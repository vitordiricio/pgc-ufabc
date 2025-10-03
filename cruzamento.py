"""
Módulo de cruzamento para a simulação de tráfego com múltiplos cruzamentos.
Sistema com vias de mão única: Horizontal (Leste→Oeste) e Vertical (Norte→Sul)
"""
import random
import math
from typing import List, Dict, Tuple
from configuracao import CONFIG, Direcao, TipoHeuristica
from veiculo import Veiculo
from semaforo import Semaforo, GerenciadorSemaforos


class Cruzamento:
    """Representa um cruzamento de tráfego com controle inteligente e vias de mão única."""

    def __init__(
        self,
        posicao: Tuple[float, float],
        id_cruzamento: Tuple[int, int],
        gerenciador_semaforos: GerenciadorSemaforos,
        malha_viaria: 'MalhaViaria'
    ):
        self.id = id_cruzamento
        self.posicao = posicao
        self.centro_x, self.centro_y = posicao
        self.gerenciador_semaforos = gerenciador_semaforos
        self.malha = malha_viaria

        # Veículos no cruzamento - APENAS DIREÇÕES PERMITIDAS
        self.veiculos_por_direcao: Dict[Direcao, List[Veiculo]] = {
            Direcao.NORTE: [],  # Norte→Sul
            Direcao.LESTE: []   # Leste→Oeste
        }

        # -------- BACKLOG por entrada --------
        self.backlog_por_direcao: Dict[Direcao, int] = {
            Direcao.NORTE: 0,
            Direcao.LESTE: 0
        }
        self.backlog_gerado_total = 0
        self.backlog_despachado_total = 0

        self.largura_rua = CONFIG.LARGURA_RUA
        self.limites = self._calcular_limites()
        self._configurar_semaforos()

        # Estatísticas
        self.estatisticas = {
            'veiculos_processados': 0,
            'tempo_espera_acumulado': 0,
            'densidade_atual': 0
        }

    def backlog_total(self) -> int:
        return sum(self.backlog_por_direcao.values())

    def _calcular_limites(self) -> Dict[str, float]:
        margem = self.largura_rua // 2
        return {
            'esquerda': self.centro_x - margem,
            'direita': self.centro_x + margem,
            'topo': self.centro_y - margem,
            'base': self.centro_y + margem
        }

    def _configurar_semaforos(self) -> None:
        offset = self.largura_rua // 2 + 30
        semaforos = {}
        semaforos[Direcao.NORTE] = Semaforo(
            (self.centro_x - offset, self.centro_y - offset),
            Direcao.NORTE, self.id
        )
        semaforos[Direcao.LESTE] = Semaforo(
            (self.centro_x - offset, self.centro_y + offset),
            Direcao.LESTE, self.id
        )
        for semaforo in semaforos.values():
            self.gerenciador_semaforos.adicionar_semaforo(semaforo)

    # ---------- helpers de faixa ----------
    def _centro_faixa(self, direcao: Direcao, idx: int) -> Tuple[float, float]:
        idx = max(0, min(idx, CONFIG.FAIXAS_POR_VIA - 1))
        if direcao == Direcao.LESTE:
            y = self.centro_y - CONFIG.LARGURA_RUA / 2 + (idx + 0.5) * CONFIG.LARGURA_FAIXA
            return (None, y)
        else:
            x = self.centro_x - CONFIG.LARGURA_RUA / 2 + (idx + 0.5) * CONFIG.LARGURA_FAIXA
            return (x, None)

    # ---------- geração + BACKLOG ----------
    def pode_gerar_veiculo(self, direcao: Direcao) -> bool:
        if direcao not in CONFIG.DIRECOES_PERMITIDAS:
            return False
        linha, coluna = self.id
        pode_gerar = {
            Direcao.NORTE: linha == 0 and CONFIG.PONTOS_SPAWN['NORTE'],
            Direcao.LESTE: coluna == 0 and CONFIG.PONTOS_SPAWN['LESTE'],
            Direcao.SUL: False,
            Direcao.OESTE: False
        }
        return pode_gerar.get(direcao, False)

    def _registrar_chegada(self, direcao: Direcao, qtd: int = 1) -> int:
        """Registra chegada de requisições de geração na fila (backlog). Retorna o que foi aceito."""
        if not CONFIG.BACKLOG_ATIVO or qtd <= 0:
            return 0
        antes = self.backlog_total()
        if antes >= CONFIG.BACKLOG_TAMANHO_MAX:
            return 0
        aceita = min(qtd, CONFIG.BACKLOG_TAMANHO_MAX - antes)
        self.backlog_por_direcao[direcao] += aceita
        self.backlog_gerado_total += aceita
        return aceita

    def _tentar_spawn(self, direcao: Direcao, faixa: int) -> Veiculo | None:
        """Tenta criar 1 veículo na faixa informada se houver espaço."""
        if direcao == Direcao.NORTE:
            x, _ = self._centro_faixa(Direcao.NORTE, faixa)
            posicao = (x, -50)
        else:
            _, y = self._centro_faixa(Direcao.LESTE, faixa)
            posicao = (-50, y)
        if self._tem_espaco_para_gerar(direcao, posicao, faixa):
            v = Veiculo(direcao, posicao, self.id)
            v.indice_faixa = faixa
            self.veiculos_por_direcao[direcao].append(v)
            return v
        return None

    def gerar_veiculos(self) -> Tuple[List[Veiculo], int, int]:
        """
        Gera veículos com suporte a backlog por entrada.
        Retorna: (novos_veiculos, chegadas_registradas, backlog_despachado)
        """
        novos_veiculos: List[Veiculo] = []
        chegadas_total = 0
        despachados_total = 0

        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            if not self.pode_gerar_veiculo(direcao):
                continue

            # 1) chegada estocástica → vira backlog
            if random.random() < CONFIG.TAXA_GERACAO_VEICULO:
                chegadas_total += self._registrar_chegada(direcao, 1)

            # 2) tenta escoar uma parte do backlog (limite por frame)
            flush_restantes = CONFIG.BACKLOG_FLUSH_MAX_POR_FRAME
            while CONFIG.BACKLOG_ATIVO and self.backlog_por_direcao[direcao] > 0 and flush_restantes > 0:
                # tenta em faixas diferentes para achar espaço
                faixas = list(range(CONFIG.FAIXAS_POR_VIA))
                random.shuffle(faixas)
                spawned = False
                for faixa in faixas:
                    v = self._tentar_spawn(direcao, faixa)
                    if v is not None:
                        novos_veiculos.append(v)
                        self.backlog_por_direcao[direcao] -= 1
                        self.backlog_despachado_total += 1
                        despachados_total += 1
                        flush_restantes -= 1
                        spawned = True
                        break
                if not spawned:
                    # sem espaço em nenhuma faixa nesse frame
                    break

        return novos_veiculos, chegadas_total, despachados_total

    def _tem_espaco_para_gerar(self, direcao, posicao, faixa) -> bool:
        for v in self.veiculos_por_direcao.get(direcao, []):
            if getattr(v, "indice_faixa", 0) != faixa:
                continue
            dx = abs(v.posicao[0] - posicao[0])
            dy = abs(v.posicao[1] - posicao[1])
            if direcao == Direcao.NORTE:
                if dy < CONFIG.DISTANCIA_MIN_VEICULO * 2:
                    return False
            elif direcao == Direcao.LESTE:
                if dx < CONFIG.DISTANCIA_MIN_VEICULO * 2:
                    return False
        return True

    def _determinar_cruzamento_veiculo(self, veiculo: Veiculo) -> Tuple[int, int]:
        coluna = int((veiculo.posicao[0] - CONFIG.POSICAO_INICIAL_X + CONFIG.ESPACAMENTO_HORIZONTAL / 2) /
                     CONFIG.ESPACAMENTO_HORIZONTAL)
        linha = int((veiculo.posicao[1] - CONFIG.POSICAO_INICIAL_Y + CONFIG.ESPACAMENTO_VERTICAL / 2) /
                    CONFIG.ESPACAMENTO_VERTICAL)
        coluna = max(0, min(coluna, CONFIG.COLUNAS_GRADE - 1))
        linha = max(0, min(linha, CONFIG.LINHAS_GRADE - 1))
        return (linha, coluna)

    def _veiculo_proximo_ao_cruzamento(self, veiculo: Veiculo) -> bool:
        distancia_limite_horizontal = CONFIG.ESPACAMENTO_HORIZONTAL * 0.7
        distancia_limite_vertical = CONFIG.ESPACAMENTO_VERTICAL * 0.7
        dx = abs(veiculo.posicao[0] - self.centro_x)
        dy = abs(veiculo.posicao[1] - self.centro_y)
        return dx < distancia_limite_horizontal or dy < distancia_limite_vertical

    def _veiculo_antes_da_linha(self, veiculo: Veiculo, posicao_parada: Tuple[float, float]) -> bool:
        margem = CONFIG.DISTANCIA_DETECCAO_SEMAFORO
        if veiculo.direcao == Direcao.NORTE:
            return veiculo.posicao[1] < posicao_parada[1] + margem
        elif veiculo.direcao == Direcao.LESTE:
            return veiculo.posicao[0] < posicao_parada[0] + margem
        return False

    def _ordenar_veiculos_por_posicao(self, veiculos: List[Veiculo], direcao: Direcao) -> List[Veiculo]:
        if direcao == Direcao.NORTE:
            return sorted(veiculos, key=lambda v: v.posicao[1], reverse=True)
        elif direcao == Direcao.LESTE:
            return sorted(veiculos, key=lambda v: v.posicao[0], reverse=True)
        return veiculos

    def obter_densidade_por_direcao(self) -> Dict[Direcao, int]:
        return {
            direcao: len(self.veiculos_por_direcao.get(direcao, []))
            for direcao in CONFIG.DIRECOES_PERMITIDAS
        }

    # =========================
    # ATUALIZAÇÃO (com anticolisão H×V + faixas)
    # =========================
    def atualizar_veiculos(self, todos_veiculos: List[Veiculo]) -> None:
        """Atualiza o estado dos veículos no cruzamento, com lock de interseção por direção."""
        # 1) Limpa listas antigas deste cruzamento
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            self.veiculos_por_direcao[direcao] = []

        # 2) Reclassifica veículos deste cruzamento
        veiculos_proximos: List[Veiculo] = []
        for v in todos_veiculos:
            if v.direcao in CONFIG.DIRECOES_PERMITIDAS and self._veiculo_proximo_ao_cruzamento(v):
                c_id = self._determinar_cruzamento_veiculo(v)
                if c_id == self.id:
                    v.resetar_controle_semaforo(self.id)
                    self.veiculos_por_direcao[v.direcao].append(v)
                    veiculos_proximos.append(v)

        # 3) Ocupação atual da interseção (quem já está dentro)
        left = self.limites['esquerda']
        right = self.limites['direita']
        top = self.limites['topo']
        base = self.limites['base']

        def dentro_intersec(veh: Veiculo) -> bool:
            x, y = veh.posicao
            return (left <= x <= right) and (top <= y <= base)

        ocup = {Direcao.NORTE: 0, Direcao.LESTE: 0}
        for v in veiculos_proximos:
            inside = dentro_intersec(v)
            v.no_cruzamento = inside
            if inside:
                ocup[v.direcao] += 1

        # 4) Processa veículos por direção
        semaforos = self.gerenciador_semaforos.semaforos.get(self.id, {})

        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            veics = self.veiculos_por_direcao.get(direcao, [])
            if not veics:
                continue

            veics_ordenados = self._ordenar_veiculos_por_posicao(veics, direcao)
            semaforo = semaforos.get(direcao, None)
            oposta = Direcao.LESTE if direcao == Direcao.NORTE else Direcao.NORTE

            for v in veics_ordenados:
                # Car-following global
                v.processar_todos_veiculos(todos_veiculos)

                # Posição da linha de parada (se houver semáforo)
                pos_parada = semaforo.obter_posicao_parada() if semaforo else None

                # Estado antes de atualizar (para detectar entrada/saída da caixa)
                estava_dentro = dentro_intersec(v)
                antes_da_linha = False
                if semaforo and pos_parada is not None:
                    # Só "antes da linha" se ainda não entrou no box
                    antes_da_linha = (not estava_dentro) and self._veiculo_antes_da_linha(v, pos_parada)

                # 4a) BLOQUEIO da direção oposta: se a outra direção está dentro, não deixamos entrar
                if antes_da_linha and ocup.get(oposta, 0) > 0:
                    # Trate como vermelho: pare antes da linha
                    dist = v._calcular_distancia_ate_ponto(pos_parada)
                    v._aplicar_frenagem_para_parada(dist)
                    v.aguardando_semaforo = True
                else:
                    # 4b) Semáforo normal
                    if semaforo and pos_parada is not None:
                        # Só processa semáforo se ainda não estiver no box
                        if not estava_dentro:
                            v.processar_semaforo(semaforo, pos_parada)

                # 4c) Atualiza física (com colisão e caos)
                v.atualizar(1.0, todos_veiculos, self.malha)

                # 4d) Detecta transições (entrou / saiu do box) e atualiza lock
                agora_dentro = dentro_intersec(v)

                if (not estava_dentro) and agora_dentro:
                    v.no_cruzamento = True
                    ocup[direcao] = ocup.get(direcao, 0) + 1
                    # Ao entrar, não deixar o carro frear por semáforo
                    v.aguardando_semaforo = False
                    v.pode_passar_amarelo = False

                elif estava_dentro and (not agora_dentro):
                    v.no_cruzamento = False
                    if ocup.get(direcao, 0) > 0:
                        ocup[direcao] -= 1

                # 4e) Métricas de espera
                if v.parado and v.aguardando_semaforo:
                    self.estatisticas['tempo_espera_acumulado'] += 1

        # 5) Atualiza densidade (veículos visíveis/associados a este cruzamento)
        self.estatisticas['densidade_atual'] = sum(
            len(self.veiculos_por_direcao.get(d, [])) for d in CONFIG.DIRECOES_PERMITIDAS
        )


class MalhaViaria:
    """Gerencia toda a malha viária com múltiplos cruzamentos e vias de mão única."""

    def __init__(self, linhas: int = CONFIG.LINHAS_GRADE, colunas: int = CONFIG.COLUNAS_GRADE):
        self.linhas = linhas
        self.colunas = colunas
        self.veiculos: List[Veiculo] = []
        self.cruzamentos: Dict[Tuple[int, int], Cruzamento] = {}
        self.gerenciador_semaforos = GerenciadorSemaforos(CONFIG.HEURISTICA_ATIVA)
        self._inicializar_caos()
        self._criar_cruzamentos()
        self.metricas = {
            'tempo_simulacao': 0,
            'veiculos_total': 0,
            'veiculos_concluidos': 0,
            'tempo_viagem_total': 0,
            'tempo_parado_total': 0,
            # backlog
            'backlog_atual_total': 0,
            'backlog_max_total': 0,
            'backlog_gerado_total': 0,
            'backlog_despachado_total': 0,
            'backlog_amostras_acum': 0  # para média
        }
        # ---- NOVO: séries/contadores para métricas que estavam zeradas ----
        self._tempos_viagem_concluidos_s = []     # em segundos (já dividido por FPS)
        self._paradas_total_concluidos = 0        # soma de paradas dos que saíram
        self._paradas_veiculos_concluidos = 0     # quantidade de veículos considerados em paradas

    # -------------------
    # EFEITO CAOS - ruas
    # -------------------
    def _inicializar_caos(self) -> None:
        seg = CONFIG.CHAOS_TAMANHO_SEGMENTO
        self._caos_seg_h = math.ceil(CONFIG.LARGURA_TELA / seg) + 1
        self._caos_seg_v = math.ceil(CONFIG.ALTURA_TELA / seg) + 1
        self.caos_horizontal: Dict[int, List[float]] = {
            linha: [1.0] * self._caos_seg_h for linha in range(self.linhas)
        }
        self.caos_vertical: Dict[int, List[float]] = {
            coluna: [1.0] * self._caos_seg_v for coluna in range(self.colunas)
        }

    def atualizar_caos(self) -> None:
        if not CONFIG.CHAOS_ATIVO:
            return
        p = CONFIG.CHAOS_PROB_MUTACAO
        fmin, fmax = CONFIG.CHAOS_FATOR_MIN, CONFIG.CHAOS_FATOR_MAX
        for linha in range(self.linhas):
            v = self.caos_horizontal[linha]
            for i in range(len(v)):
                if random.random() < p:
                    v[i] = random.uniform(fmin, fmax)
        for coluna in range(self.colunas):
            v = self.caos_vertical[coluna]
            for i in range(len(v)):
                if random.random() < p:
                    v[i] = random.uniform(fmin, fmax)

    def obter_fator_caos(self, veiculo: Veiculo) -> float:
        if not CONFIG.CHAOS_ATIVO:
            return 1.0
        seg = CONFIG.CHAOS_TAMANHO_SEGMENTO
        if veiculo.direcao == Direcao.LESTE:
            linha_mais_prox = max(0, min(
                self.linhas - 1,
                round((veiculo.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_VERTICAL)
            ))
            seg_x = max(0, min(self._caos_seg_h - 1, int(veiculo.posicao[0] // seg)))
            return self.caos_horizontal[linha_mais_prox][seg_x]
        elif veiculo.direcao == Direcao.NORTE:
            coluna_mais_prox = max(0, min(
                self.colunas - 1,
                round((veiculo.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_HORIZONTAL)
            ))
            seg_y = max(0, min(self._caos_seg_v - 1, int(veiculo.posicao[1] // seg)))
            return self.caos_vertical[coluna_mais_prox][seg_y]
        return 1.0

    def _criar_cruzamentos(self) -> None:
        for linha in range(self.linhas):
            for coluna in range(self.colunas):
                x = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_HORIZONTAL
                y = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_VERTICAL
                id_cruzamento = (linha, coluna)
                self.cruzamentos[id_cruzamento] = Cruzamento(
                    (x, y), id_cruzamento, self.gerenciador_semaforos, self
                )

    # --------- PERF: vizinhos por (via, faixa) em O(N) ----------
    def _construir_vizinhos_por_faixa(self) -> None:
        buckets = {}

        def via_idx_de(v: Veiculo) -> int:
            if v.direcao == Direcao.LESTE:
                idx = round((v.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_VERTICAL)
                return max(0, min(idx, self.linhas - 1))
            else:
                idx = round((v.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_HORIZONTAL)
                return max(0, min(idx, self.colunas - 1))

        for v in self.veiculos:
            if not v.ativo:
                continue
            faixa = getattr(v, "indice_faixa", 0)
            key = (v.direcao, via_idx_de(v), faixa)
            longpos = v.posicao[0] if v.direcao == Direcao.LESTE else v.posicao[1]
            buckets.setdefault(key, []).append((longpos, v))

        # zera caches
        for v in self.veiculos:
            v._leader_cache = None
            v._follower_cache = None

        for key, arr in buckets.items():
            arr.sort(key=lambda t: t[0])  # crescente
            n = len(arr)
            for i, (_, v) in enumerate(arr):
                v._leader_cache = arr[i + 1][1] if i + 1 < n else None
                v._follower_cache = arr[i - 1][1] if i - 1 >= 0 else None

    # ---- helpers para métricas instantâneas ----
    @staticmethod
    def _speed_of(v: Veiculo) -> float:
        # tenta várias convenções comuns
        if hasattr(v, 'velocidade'):
            return float(v.velocidade)
        if hasattr(v, 'velocidade_atual'):
            return float(v.velocidade_atual)
        if hasattr(v, 'vx') and hasattr(v, 'vy'):
            try:
                return math.hypot(float(v.vx), float(v.vy))
            except Exception:
                return 0.0
        # fallback: moveu no frame? (se o Veiculo tiver delta armazenado)
        return float(getattr(v, 'speed', 0.0))

    @staticmethod
    def _percentil(valores: List[float], p: float) -> float:
        if not valores:
            return 0.0
        arr = sorted(valores)
        if len(arr) == 1:
            return arr[0]
        k = (len(arr) - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return arr[int(k)]
        d0 = arr[f] * (c - k)
        d1 = arr[c] * (k - f)
        return d0 + d1

    def atualizar(self) -> None:
        self.metricas['tempo_simulacao'] += 1
        self.atualizar_caos()

        # Gera novos veículos + backlog
        frame_chegadas = 0
        frame_despachados = 0
        for cruzamento in self.cruzamentos.values():
            novos_veiculos, chegadas, despachados = cruzamento.gerar_veiculos()
            self.veiculos.extend(novos_veiculos)
            self.metricas['veiculos_total'] += len(novos_veiculos)
            frame_chegadas += chegadas
            frame_despachados += despachados

        self.metricas['backlog_gerado_total'] += frame_chegadas
        self.metricas['backlog_despachado_total'] += frame_despachados

        # PERF: pré-calcula vizinhos por faixa (O(N))
        self._construir_vizinhos_por_faixa()

        # Atualiza cruzamentos
        for cruzamento in self.cruzamentos.values():
            cruzamento.atualizar_veiculos(self.veiculos)

        # ---- NOVO: detectar início de parada (para contar "paradas") ----
        # Regra: conta quando transita de "em movimento" -> "parado".
        # Critério de parado: speed <= 1e-3 OU atributo v.parado True
        for v in self.veiculos:
            if not v.ativo:
                continue
            speed = self._speed_of(v)
            moving = speed > 1e-3 and not getattr(v, 'parado', False)
            was_moving = getattr(v, '_was_moving', True)
            if was_moving and not moving:
                v._stop_count = getattr(v, '_stop_count', 0) + 1
            v._was_moving = moving

        # Coleta densidade para heurísticas
        densidade_por_cruzamento = {}
        for id_cruzamento, cruzamento in self.cruzamentos.items():
            densidade_por_cruzamento[id_cruzamento] = cruzamento.obter_densidade_por_direcao()

        self.gerenciador_semaforos.atualizar(densidade_por_cruzamento)

        # Remove veículos inativos e coleta métricas
        veiculos_ativos = []
        for veiculo in self.veiculos:
            if veiculo.ativo:
                veiculos_ativos.append(veiculo)
            else:
                self.metricas['veiculos_concluidos'] += 1
                self.metricas['tempo_viagem_total'] += veiculo.tempo_viagem
                self.metricas['tempo_parado_total'] += veiculo.tempo_parado
                # ---- NOVO: guardar dados para percentis e paradas ----
                self._tempos_viagem_concluidos_s.append(veiculo.tempo_viagem / CONFIG.FPS)
                self._paradas_total_concluidos += int(getattr(veiculo, '_stop_count',
                                                              getattr(veiculo, 'numero_paradas', 0)))
                self._paradas_veiculos_concluidos += 1

        self.veiculos = veiculos_ativos

        # Atualiza backlog atual / máximo
        backlog_atual = sum(c.backlog_total() for c in self.cruzamentos.values())
        self.metricas['backlog_atual_total'] = backlog_atual
        if backlog_atual > self.metricas['backlog_max_total']:
            self.metricas['backlog_max_total'] = backlog_atual
        self.metricas['backlog_amostras_acum'] += backlog_atual

    def mudar_heuristica(self, nova_heuristica: TipoHeuristica) -> None:
        self.gerenciador_semaforos.mudar_heuristica(nova_heuristica)

    def obter_estatisticas(self) -> Dict[str, any]:
        veiculos_ativos = len(self.veiculos)

        # tempos médios concluídos
        tempo_viagem_medio = 0.0
        tempo_parado_medio = 0.0
        if self.metricas['veiculos_concluidos'] > 0:
            tempo_viagem_medio = (self.metricas['tempo_viagem_total'] /
                                  self.metricas['veiculos_concluidos'] / CONFIG.FPS)
            tempo_parado_medio = (self.metricas['tempo_parado_total'] /
                                  self.metricas['veiculos_concluidos'] / CONFIG.FPS)

        # Throughput por minuto (média no período)
        sim_t = max(1.0, self.metricas['tempo_simulacao'] / CONFIG.FPS)
        throughput_por_minuto = (self.metricas['veiculos_concluidos'] / sim_t) * 60.0

        # ---- NOVO: velocidades médias instantâneas ----
        speeds = [self._speed_of(v) for v in self.veiculos]
        velocidade_media_global = sum(speeds) / len(speeds) if speeds else 0.0
        speeds_ativas = [s for s in speeds if s > 1e-3 and not getattr(self.veiculos[speeds.index(s)], 'parado', False)]
        # Para não depender do index acima (caso duplicatas), refazemos:
        speeds_ativas = []
        for v in self.veiculos:
            s = self._speed_of(v)
            if s > 1e-3 and not getattr(v, 'parado', False):
                speeds_ativas.append(s)
        velocidade_media_ativa = sum(speeds_ativas) / len(speeds_ativas) if speeds_ativas else 0.0

        # ---- NOVO: veículos aguardando (parados/aguardando semáforo) ----
        veiculos_aguardando = 0
        for v in self.veiculos:
            if getattr(v, 'parado', False) or getattr(v, 'aguardando_semaforo', False):
                veiculos_aguardando += 1

        # ---- NOVO: maior fila por cruzamento (aproximação: carros associados ao cruzamento) ----
        maior_fila = 0
        for cruz in self.cruzamentos.values():
            fila_cruz = sum(len(cruz.veiculos_por_direcao.get(d, [])) for d in CONFIG.DIRECOES_PERMITIDAS)
            if fila_cruz > maior_fila:
                maior_fila = fila_cruz

        # ---- NOVO: percentis de tempo de viagem ----
        p50 = self._percentil(self._tempos_viagem_concluidos_s, 0.50)
        p95 = self._percentil(self._tempos_viagem_concluidos_s, 0.95)

        # ---- NOVO: paradas médias por veículo concluído ----
        if self._paradas_veiculos_concluidos > 0:
            paradas_media = self._paradas_total_concluidos / self._paradas_veiculos_concluidos
        else:
            paradas_media = 0.0

        # Estatísticas do backlog
        backlog_atual = self.metricas['backlog_atual_total']
        backlog_max = self.metricas['backlog_max_total']
        backlog_gerado = self.metricas['backlog_gerado_total']
        backlog_desp = self.metricas['backlog_despachado_total']
        backlog_media = self.metricas['backlog_amostras_acum'] / max(1, self.metricas['tempo_simulacao'])

        return {
            'veiculos_ativos': veiculos_ativos,
            'veiculos_total': self.metricas['veiculos_total'],
            'veiculos_concluidos': self.metricas['veiculos_concluidos'],
            'tempo_viagem_medio': tempo_viagem_medio,
            'tempo_parado_medio': tempo_parado_medio,
            'heuristica': self.gerenciador_semaforos.obter_info_heuristica(),
            'tempo_simulacao': self.metricas['tempo_simulacao'] / CONFIG.FPS,
            'throughput_por_minuto': throughput_por_minuto,
            # ---- NOVAS/ARRUMADAS ----
            'velocidade_media_global': velocidade_media_global,
            'velocidade_media_ativa': velocidade_media_ativa,
            'veiculos_aguardando': veiculos_aguardando,
            'maior_fila_cruzamento_atual': maior_fila,
            'tempo_viagem_p50': p50,
            'tempo_viagem_p95': p95,
            'paradas_media_por_veiculo': paradas_media,
            # backlog
            'backlog_total': backlog_atual,
            'backlog_max': backlog_max,
            'backlog_gerado_total': backlog_gerado,
            'backlog_despachado_total': backlog_desp,
            'backlog_medio': backlog_media
        }
