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

        self.largura_rua = CONFIG.LARGURA_RUA
        self.limites = self._calcular_limites()
        self._configurar_semaforos()

        # Estatísticas
        self.estatisticas = {
            'veiculos_processados': 0,
            'tempo_espera_acumulado': 0,
            'densidade_atual': 0
        }

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
            # faixa horizontal: varia em Y
            y = self.centro_y - CONFIG.LARGURA_RUA / 2 + (idx + 0.5) * CONFIG.LARGURA_FAIXA
            return (None, y)
        else:
            # faixa vertical: varia em X
            x = self.centro_x - CONFIG.LARGURA_RUA / 2 + (idx + 0.5) * CONFIG.LARGURA_FAIXA
            return (x, None)

    # ---------- geração ----------
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

    def gerar_veiculos(self) -> List[Veiculo]:
        novos_veiculos = []
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            if not self.pode_gerar_veiculo(direcao):
                continue
            if random.random() < CONFIG.TAXA_GERACAO_VEICULO:
                # escolhe faixa aleatória
                faixa = random.randint(0, CONFIG.FAIXAS_POR_VIA - 1)
                if direcao == Direcao.NORTE:
                    x, _ = self._centro_faixa(Direcao.NORTE, faixa)
                    posicao = (x, -50)
                else:
                    _, y = self._centro_faixa(Direcao.LESTE, faixa)
                    posicao = (-50, y)

                if self._tem_espaco_para_gerar(direcao, posicao, faixa):
                    veiculo = Veiculo(direcao, posicao, self.id)
                    veiculo.indice_faixa = faixa
                    novos_veiculos.append(veiculo)
                    self.veiculos_por_direcao[direcao].append(veiculo)
        return novos_veiculos

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
            # ---- NOVOS AGREGADOS / SÉRIES ----
            'paradas_totais_total': 0,
            'distancia_total': 0.0,
            'tempos_viagem': [],       # lista de tempos de viagem (s) por veículo concluído
            'tempos_parado': [],       # lista de tempos parados (s)
            'paradas_por_viagem': [],  # lista de #paradas por veículo
            'distancias': []           # lista de distâncias percorridas (px)
        }

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
        """
        Para cada (direção, via, faixa), ordena veículos por coordenada longitudinal
        e preenche caches _leader_cache/_follower_cache nos veículos.
        """
        buckets = {}  # (direcao, via_idx, faixa_idx) -> list[(long, veh)]

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

    def atualizar(self) -> None:
        self.metricas['tempo_simulacao'] += 1
        self.atualizar_caos()

        # Gera novos veículos
        for cruzamento in self.cruzamentos.values():
            novos_veiculos = cruzamento.gerar_veiculos()
            self.veiculos.extend(novos_veiculos)
            self.metricas['veiculos_total'] += len(novos_veiculos)

        # PERF: pré-calcula vizinhos por faixa (O(N))
        self._construir_vizinhos_por_faixa()

        # Atualiza cruzamentos
        for cruzamento in self.cruzamentos.values():
            cruzamento.atualizar_veiculos(self.veiculos)

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
                # ---- NOVOS ACUMULADORES/SÉRIES ----
                self.metricas['paradas_totais_total'] += veiculo.paradas_totais
                self.metricas['distancia_total'] += veiculo.distancia_percorrida
                self.metricas['tempos_viagem'].append(veiculo.tempo_viagem)
                self.metricas['tempos_parado'].append(veiculo.tempo_parado)
                self.metricas['paradas_por_viagem'].append(veiculo.paradas_totais)
                self.metricas['distancias'].append(veiculo.distancia_percorrida)

        self.veiculos = veiculos_ativos

    def mudar_heuristica(self, nova_heuristica: TipoHeuristica) -> None:
        self.gerenciador_semaforos.mudar_heuristica(nova_heuristica)

    # --------- helpers internos para estatística instantânea ----------
    def _cruzamento_id_para_posicao(self, pos: Tuple[float, float]) -> Tuple[int, int]:
        x, y = pos
        coluna = int((x - CONFIG.POSICAO_INICIAL_X + CONFIG.ESPACAMENTO_HORIZONTAL / 2) / CONFIG.ESPACAMENTO_HORIZONTAL)
        linha = int((y - CONFIG.POSICAO_INICIAL_Y + CONFIG.ESPACAMENTO_VERTICAL / 2) / CONFIG.ESPACAMENTO_VERTICAL)
        coluna = max(0, min(coluna, CONFIG.COLUNAS_GRADE - 1))
        linha = max(0, min(linha, CONFIG.LINHAS_GRADE - 1))
        return (linha, coluna)

    def _maior_fila_atual(self) -> int:
        """
        Retorna a maior fila atual entre todos os cruzamentos (conta veículos em
        espera de semáforo, fora da caixa de interseção).
        """
        # Aproximação: conta veículos aguardando_semaforo e associa ao cruzamento
        filas: Dict[Tuple[int, int], int] = {}
        for v in self.veiculos:
            if not v.aguardando_semaforo or v.no_cruzamento:
                continue
            cid = self._cruzamento_id_para_posicao(tuple(v.posicao))
            filas[cid] = filas.get(cid, 0) + 1
        return max(filas.values()) if filas else 0

    def obter_estatisticas(self) -> Dict[str, any]:
        veiculos_ativos = len(self.veiculos)
        tempo_viagem_medio = 0
        tempo_parado_medio = 0
        if self.metricas['veiculos_concluidos'] > 0:
            tempo_viagem_medio = self.metricas['tempo_viagem_total'] / self.metricas['veiculos_concluidos'] / CONFIG.FPS
            tempo_parado_medio = self.metricas['tempo_parado_total'] / self.metricas['veiculos_concluidos'] / CONFIG.FPS

        # ---- NOVAS MÉTRICAS DERIVADAS (com base em acumuladores) ----
        tempo_sim_s = self.metricas['tempo_simulacao'] / CONFIG.FPS
        velocidade_media_global = 0.0
        if self.metricas['tempo_viagem_total'] > 0:
            # distância (px) / tempo (frames) -> px/frame. Convertemos para px/s multiplicando FPS.
            v_px_por_frame = self.metricas['distancia_total'] / max(1e-9, self.metricas['tempo_viagem_total'])
            velocidade_media_global = v_px_por_frame * CONFIG.FPS

        paradas_media_por_veiculo = (
            sum(self.metricas['paradas_por_viagem']) / len(self.metricas['paradas_por_viagem'])
            if self.metricas['paradas_por_viagem'] else 0.0
        )

        def _percentil(vals: List[float], p: float) -> float:
            if not vals:
                return 0.0
            arr = sorted(vals)
            k = (len(arr) - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return arr[int(k)]
            return arr[f] + (arr[c] - arr[f]) * (k - f)

        tempo_viagem_p50 = _percentil(self.metricas['tempos_viagem'], 0.50)
        tempo_viagem_p95 = _percentil(self.metricas['tempos_viagem'], 0.95)
        # já em segundos? self.metricas['tempos_viagem'] está em frames acumulados convertidos?
        # Observação: guardamos em 'atualizar' diretamente 'veiculo.tempo_viagem' que está em "passos dt (=frames)"
        # Lá foi somado com dt=1 por atualização (vide Veiculo.atualizar). Para manter consistência, convertemos aqui:
        tempo_viagem_p50 /= CONFIG.FPS
        tempo_viagem_p95 /= CONFIG.FPS

        throughput_por_minuto = (self.metricas['veiculos_concluidos'] / (tempo_sim_s / 60)) if tempo_sim_s > 0 else 0.0

        veiculos_aguardando = sum(1 for v in self.veiculos if v.aguardando_semaforo and not v.no_cruzamento)
        velocidade_media_ativa = (
            sum(v.velocidade for v in self.veiculos) / veiculos_ativos if veiculos_ativos > 0 else 0.0
        )

        maior_fila_cruzamento_atual = self._maior_fila_atual()

        return {
            'veiculos_ativos': veiculos_ativos,
            'veiculos_total': self.metricas['veiculos_total'],
            'veiculos_concluidos': self.metricas['veiculos_concluidos'],
            'tempo_viagem_medio': tempo_viagem_medio,
            'tempo_parado_medio': tempo_parado_medio,
            'heuristica': self.gerenciador_semaforos.obter_info_heuristica(),
            'tempo_simulacao': tempo_sim_s,
            # ---- NOVAS CHAVES ----
            'velocidade_media_global': velocidade_media_global,          # px/s
            'paradas_media_por_veiculo': paradas_media_por_veiculo,
            'tempo_viagem_p50': tempo_viagem_p50,                       # s
            'tempo_viagem_p95': tempo_viagem_p95,                       # s
            'throughput_por_minuto': throughput_por_minuto,
            'veiculos_aguardando': veiculos_aguardando,
            'velocidade_media_ativa': velocidade_media_ativa,           # px/frame (interno), mas útil relativa
            'maior_fila_cruzamento_atual': maior_fila_cruzamento_atual
        }
