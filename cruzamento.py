"""
Módulo de cruzamento para a simulação de tráfego com múltiplos cruzamentos.
Sistema com vias de mão única: Horizontal (Leste→Oeste) e Vertical (Norte→Sul)
"""
import random
import math
import pygame
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
        """
        Inicializa o cruzamento.

        Args:
            posicao: Posição (x, y) do centro do cruzamento
            id_cruzamento: Identificador (linha, coluna) do cruzamento
            gerenciador_semaforos: Gerenciador global de semáforos
            malha_viaria: Referência para a malha (usada para consultar o "caos")
        """
        self.id = id_cruzamento
        self.posicao = posicao
        self.centro_x, self.centro_y = posicao
        self.gerenciador_semaforos = gerenciador_semaforos
        self.malha = malha_viaria  # <<< referência à malha

        # Veículos no cruzamento - APENAS DIREÇÕES PERMITIDAS
        self.veiculos_por_direcao: Dict[Direcao, List[Veiculo]] = {
            Direcao.NORTE: [],  # Norte→Sul
            Direcao.LESTE: []   # Leste→Oeste
        }

        # Configurações do cruzamento
        self.largura_rua = CONFIG.LARGURA_RUA
        self.limites = self._calcular_limites()
        self.ocupacao_miolo = {Direcao.NORTE: set(), Direcao.LESTE: set()}

        # Configurar semáforos apenas para as direções permitidas
        self._configurar_semaforos()

        # Estatísticas
        self.estatisticas = {
            'veiculos_processados': 0,
            'tempo_espera_acumulado': 0,
            'densidade_atual': 0
        }


    # =========================
    # Controle de MIÔLO (box)
    # =========================
    def _rect_miolo(self) -> pygame.Rect:
        """Retângulo do miolo do cruzamento (área de conflito)."""
        return pygame.Rect(
            int(self.limites['esquerda']),
            int(self.limites['topo']),
            int(self.largura_rua),
            int(self.largura_rua),
        )

    def _veiculo_no_miolo(self, v: Veiculo) -> bool:
        """True se o veículo está dentro do miolo."""
        if not v.ativo:
            return False
        return v.rect.colliderect(self._rect_miolo())

    def _atualizar_ocupacao_miolo(self, todos: List[Veiculo]) -> None:
        """Recalcula ocupação do miolo com base nas posições atuais (fase 1)."""
        self.ocupacao_miolo = {Direcao.NORTE: set(), Direcao.LESTE: set()}
        rect = self._rect_miolo()
        for v in todos:
            if v.ativo and v.direcao in self.ocupacao_miolo and v.rect.colliderect(rect):
                self.ocupacao_miolo[v.direcao].add(v.id)

    def _atualizar_ocupacao_com_veiculo(self, v: Veiculo) -> None:
        """Atualiza ocupação incrementalmente quando um veículo entra no miolo (fase 2)."""
        if v.ativo and v.direcao in self.ocupacao_miolo and self._veiculo_no_miolo(v):
            self.ocupacao_miolo[v.direcao].add(v.id)

    def _ocupado_por_oposto(self, direcao: Direcao) -> bool:
        """True se há veículo no miolo vindo da direção ortogonal."""
        oposta = Direcao.LESTE if direcao == Direcao.NORTE else Direcao.NORTE
        return len(self.ocupacao_miolo.get(oposta, set())) > 0


    # --- Helpers de faixa (centros laterais) ---
    def _centros_faixas_horizontal(self) -> List[float]:
        """Retorna os Y-centers das faixas horizontais (LESTE) deste cruzamento."""
        n = CONFIG.FAIXAS_POR_VIA
        w = CONFIG.LARGURA_FAIXA
        topo = self.centro_y - CONFIG.LARGURA_RUA / 2.0
        return [topo + w * (i + 0.5) for i in range(n)]

    def _centros_faixas_vertical(self) -> List[float]:
        """Retorna os X-centers das faixas verticais (NORTE) deste cruzamento."""
        n = CONFIG.FAIXAS_POR_VIA
        w = CONFIG.LARGURA_FAIXA
        esquerda = self.centro_x - CONFIG.LARGURA_RUA / 2.0
        return [esquerda + w * (i + 0.5) for i in range(n)]


    def _calcular_limites(self) -> Dict[str, float]:
        """Calcula os limites físicos do cruzamento."""
        margem = self.largura_rua // 2
        return {
            'esquerda': self.centro_x - margem,
            'direita': self.centro_x + margem,
            'topo': self.centro_y - margem,
            'base': self.centro_y + margem
        }

    def _configurar_semaforos(self) -> None:
        """Configura os semáforos do cruzamento - apenas para direções permitidas."""
        offset = self.largura_rua // 2 + 30

        # Cria semáforos apenas para direções de mão única
        semaforos = {}

        # Semáforo para tráfego Norte→Sul (vindo de cima)
        semaforos[Direcao.NORTE] = Semaforo(
            (self.centro_x - offset, self.centro_y - offset),
            Direcao.NORTE, self.id
        )

        # Semáforo para tráfego Leste→Oeste (vindo da esquerda)
        semaforos[Direcao.LESTE] = Semaforo(
            (self.centro_x - offset, self.centro_y + offset),
            Direcao.LESTE, self.id
        )

        # Adiciona ao gerenciador
        for semaforo in semaforos.values():
            self.gerenciador_semaforos.adicionar_semaforo(semaforo)

    def pode_gerar_veiculo(self, direcao: Direcao) -> bool:
        """Verifica se pode gerar veículo em uma direção específica - MÃO ÚNICA."""
        # Só permite direções de mão única
        if direcao not in CONFIG.DIRECOES_PERMITIDAS:
            return False

        linha, coluna = self.id

        # Define onde cada direção pode gerar veículos
        pode_gerar = {
            # Norte: apenas no topo (linha 0), veículos vão para baixo
            Direcao.NORTE: linha == 0 and CONFIG.PONTOS_SPAWN['NORTE'],
            # Leste: apenas na esquerda (coluna 0), veículos vão para direita
            Direcao.LESTE: coluna == 0 and CONFIG.PONTOS_SPAWN['LESTE'],
            # Sul e Oeste desativados - mão única
            Direcao.SUL: False,
            Direcao.OESTE: False
        }

        return pode_gerar.get(direcao, False)

    def gerar_veiculos(self) -> List[Veiculo]:
        """Gera novos veículos nas bordas apropriadas, escolhendo FAIXA e respeitando headway por faixa."""
        novos_veiculos = []

        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            if not self.pode_gerar_veiculo(direcao):
                continue
            if random.random() >= CONFIG.TAXA_GERACAO_VEICULO:
                continue

            # Escolhe faixa aleatória (poderia ser por distribuição)
            indice_faixa = random.randrange(CONFIG.FAIXAS_POR_VIA)
            posicao = self._calcular_posicao_inicial(direcao, indice_faixa)

            if self._tem_espaco_para_gerar(direcao, posicao, indice_faixa):
                veiculo = Veiculo(direcao, posicao, self.id, indice_faixa=indice_faixa)
                novos_veiculos.append(veiculo)
                self.veiculos_por_direcao[direcao].append(veiculo)

        return novos_veiculos


    def _calcular_posicao_inicial(self, direcao: Direcao, indice_faixa: int) -> Tuple[float, float]:
        """Calcula a posição inicial já centralizada na faixa escolhida."""
        if direcao == Direcao.NORTE:
            x = self._centros_faixas_vertical()[indice_faixa]
            return (x, -50.0)
        elif direcao == Direcao.LESTE:
            y = self._centros_faixas_horizontal()[indice_faixa]
            return (-50.0, y)
        return (0.0, 0.0)


    def _tem_espaco_para_gerar(self, direcao: Direcao, posicao: Tuple[float, float], indice_faixa: int) -> bool:
        """Headway mínimo na mesma faixa antes de permitir spawn."""
        candidatos = [v for v in self.veiculos_por_direcao.get(direcao, [])
                      if v.indice_faixa == indice_faixa]

        for v in candidatos:
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
        """
        Determina qual cruzamento o veículo está mais próximo.

        Args:
            veiculo: Veículo a verificar

        Returns:
            ID do cruzamento mais próximo
        """
        # Calcula em qual cruzamento o veículo está baseado em sua posição
        coluna = int((veiculo.posicao[0] - CONFIG.POSICAO_INICIAL_X + CONFIG.ESPACAMENTO_HORIZONTAL / 2) /
                    CONFIG.ESPACAMENTO_HORIZONTAL)
        linha = int((veiculo.posicao[1] - CONFIG.POSICAO_INICIAL_Y + CONFIG.ESPACAMENTO_VERTICAL / 2) /
                   CONFIG.ESPACAMENTO_VERTICAL)

        # Limita aos valores válidos
        coluna = max(0, min(coluna, CONFIG.COLUNAS_GRADE - 1))
        linha = max(0, min(linha, CONFIG.LINHAS_GRADE - 1))

        return (linha, coluna)

    def atualizar_veiculos(self, todos_veiculos: List[Veiculo]) -> None:
        """Atualiza o estado dos veículos no cruzamento com múltiplas faixas e anticolisão H×V."""
        # 1) Limpa listas do quadro anterior
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            self.veiculos_por_direcao[direcao] = []

        # 2) Recoleta veículos próximos deste cruzamento (e reseta controle ao trocar de cruzamento)
        veiculos_proximos = []
        for veiculo in todos_veiculos:
            if veiculo.direcao in CONFIG.DIRECOES_PERMITIDAS and self._veiculo_proximo_ao_cruzamento(veiculo):
                cruz_atual = self._determinar_cruzamento_veiculo(veiculo)
                if cruz_atual == self.id:
                    veiculo.resetar_controle_semaforo(self.id)
                    self.veiculos_por_direcao[veiculo.direcao].append(veiculo)
                    veiculos_proximos.append(veiculo)

        # 3) Pré-cálculo de ocupação do "miolo" do cruzamento por cada fluxo
        #    Usamos um retângulo implícito via coordenadas (sem pygame), com leve margem
        margem = 6.0
        left, right = self.limites['esquerda'] - margem, self.limites['direita'] + margem
        top, bottom = self.limites['topo'] - margem, self.limites['base'] + margem

        def dentro_miolo(v: Veiculo) -> bool:
            x, y = v.posicao
            return (left <= x <= right) and (top <= y <= bottom)

        ocupado_por_horizontal = any(v.ativo and v.direcao == Direcao.LESTE and dentro_miolo(v) for v in todos_veiculos)
        ocupado_por_vertical = any(v.ativo and v.direcao == Direcao.NORTE and dentro_miolo(v) for v in todos_veiculos)

        # 4) Processamento por direção (NORTE e LESTE)
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            veics = self.veiculos_por_direcao.get(direcao, [])
            if not veics:
                continue

            # 4.1) Particiona por faixa e ordena longitudinalmente (mais à frente primeiro)
            faixas: Dict[int, List[Veiculo]] = {}
            for v in veics:
                idx = getattr(v, "indice_faixa", 0)
                faixas.setdefault(idx, []).append(v)

            for idx_faixa, lista in faixas.items():
                if direcao == Direcao.NORTE:
                    # Norte→Sul: maior Y está mais à frente
                    lista.sort(key=lambda v: v.posicao[1], reverse=True)
                else:
                    # Leste→Oeste: maior X está mais à frente
                    lista.sort(key=lambda v: v.posicao[0], reverse=True)

            # 4.2) Acesso ao semáforo desta direção
            sems = self.gerenciador_semaforos.semaforos.get(self.id, {})
            semaforo = sems.get(direcao)

            # 4.3) Função utilitária: sou líder na minha faixa?
            def eh_lider(v: Veiculo) -> bool:
                idx = getattr(v, "indice_faixa", 0)
                lista = faixas.get(idx, [])
                if not lista:
                    return True
                return v is lista[0]  # lista já está ordenada com o mais à frente no índice 0

            # 4.4) Processa cada faixa separadamente
            for idx_faixa, lista in faixas.items():
                for veic in lista:
                    # 4.4.1) Interações globais (car-following + tentativas de troca de faixa)
                    veic.processar_todos_veiculos(todos_veiculos)

                    # 4.4.2) Semáforo: somente se ainda não passou da linha
                    if semaforo:
                        posicao_parada = semaforo.obter_posicao_parada()
                        if self._veiculo_antes_da_linha(veic, posicao_parada):
                            veic.processar_semaforo(semaforo, posicao_parada)

                    # 4.4.3) Gate do miolo (evita colisões H×V).
                    #         Aplicamos APENAS ao LÍDER da faixa e só se o cruzamento
                    #         está ocupado pela via ortogonal.
                    #         Também só atua enquanto o veículo ainda não passou da linha.
                    precisa_gate = False
                    if eh_lider(veic):
                        # Ainda está antes da linha de parada?
                        if semaforo:
                            posicao_parada = semaforo.obter_posicao_parada()
                            antes_da_linha = self._veiculo_antes_da_linha(veic, posicao_parada)
                        else:
                            # Sem semáforo configurado (raro): considera "antes" se não está dentro do miolo
                            antes_da_linha = not dentro_miolo(veic)

                        if antes_da_linha:
                            if veic.direcao == Direcao.LESTE and ocupado_por_vertical:
                                precisa_gate = True
                            elif veic.direcao == Direcao.NORTE and ocupado_por_horizontal:
                                precisa_gate = True

                    if precisa_gate:
                        # Força parada suave antes da linha
                        if semaforo:
                            dist = veic._calcular_distancia_ate_ponto(semaforo.obter_posicao_parada())
                        else:
                            # fallback: distância ao centro do cruzamento
                            dist = max(
                                0.0,
                                (self.centro_x - veic.posicao[0]) if veic.direcao == Direcao.LESTE
                                else (self.centro_y - veic.posicao[1])
                            )
                        veic._aplicar_frenagem_para_parada(dist)
                        veic.aguardando_semaforo = True

                    # 4.4.4) Atualiza física (com detecção de colisão global e fator 'caos')
                    veic.atualizar(1.0, todos_veiculos, self.malha)

                    # 4.4.5) Atualiza flag de "no cruzamento" (útil para debug/ocupação)
                    veic.no_cruzamento = dentro_miolo(veic)

                    # 4.4.6) Métricas: espera acumulada
                    if veic.parado and veic.aguardando_semaforo:
                        self.estatisticas['tempo_espera_acumulado'] += 1

        # 5) Atualiza densidade local (por cruzamento)
        self.estatisticas['densidade_atual'] = sum(
            len(self.veiculos_por_direcao.get(d, []))
            for d in CONFIG.DIRECOES_PERMITIDAS
        )

    def _veiculo_antes_da_linha(self, veiculo: Veiculo, posicao_parada: Tuple[float, float]) -> bool:
        """
        Verifica se o veículo está antes da linha de parada.

        Args:
            veiculo: Veículo a verificar
            posicao_parada: Posição da linha de parada

        Returns:
            True se o veículo está antes da linha
        """
        margem = CONFIG.DISTANCIA_DETECCAO_SEMAFORO

        if veiculo.direcao == Direcao.NORTE:
            # Norte→Sul: está antes se Y do veículo < Y da linha + margem
            return veiculo.posicao[1] < posicao_parada[1] + margem
        elif veiculo.direcao == Direcao.LESTE:
            # Leste→Oeste: está antes se X do veículo < X da linha + margem
            return veiculo.posicao[0] < posicao_parada[0] + margem

        return False

    def _veiculo_proximo_ao_cruzamento(self, veiculo: Veiculo) -> bool:
        """Verifica se um veículo está próximo o suficiente do cruzamento."""
        distancia_limite_horizontal = CONFIG.ESPACAMENTO_HORIZONTAL * 0.7
        distancia_limite_vertical = CONFIG.ESPACAMENTO_VERTICAL * 0.7

        dx = abs(veiculo.posicao[0] - self.centro_x)
        dy = abs(veiculo.posicao[1] - self.centro_y)

        return dx < distancia_limite_horizontal or dy < distancia_limite_vertical

    def _ordenar_veiculos_por_posicao(self, veiculos: List[Veiculo], direcao: Direcao) -> List[Veiculo]:
        """
        CORRIGIDO: Ordena veículos por posição absoluta na via.
        O primeiro da lista é o que está mais à frente (mais perto do destino).
        """
        if direcao == Direcao.NORTE:
            # Norte→Sul: o mais à frente tem MAIOR Y (está mais para baixo)
            return sorted(veiculos, key=lambda v: v.posicao[1], reverse=True)
        elif direcao == Direcao.LESTE:
            # Leste→Oeste: o mais à frente tem MAIOR X (está mais para direita)
            return sorted(veiculos, key=lambda v: v.posicao[0], reverse=True)

        return veiculos

    def obter_densidade_por_direcao(self) -> Dict[Direcao, int]:
        """Retorna a densidade de veículos por direção."""
        return {
            direcao: len(self.veiculos_por_direcao.get(direcao, []))
            for direcao in CONFIG.DIRECOES_PERMITIDAS
        }



class MalhaViaria:
    """Gerencia toda a malha viária com múltiplos cruzamentos e vias de mão única."""

    def __init__(self, linhas: int = CONFIG.LINHAS_GRADE, colunas: int = CONFIG.COLUNAS_GRADE):
        """
        Inicializa a malha viária.

        Args:
            linhas: Número de linhas de cruzamentos
            colunas: Número de colunas de cruzamentos
        """
        self.linhas = linhas
        self.colunas = colunas
        self.veiculos: List[Veiculo] = []
        self.cruzamentos: Dict[Tuple[int, int], Cruzamento] = {}

        # Gerenciador de semáforos
        self.gerenciador_semaforos = GerenciadorSemaforos(CONFIG.HEURISTICA_ATIVA)

        # Efeito "caos" por via/trecho
        self._inicializar_caos()  # <<< inicializa mapas de caos

        # Criar cruzamentos
        self._criar_cruzamentos()

        # Métricas
        self.metricas = {
            'tempo_simulacao': 0,
            'veiculos_total': 0,
            'veiculos_concluidos': 0,
            'tempo_viagem_total': 0,
            'tempo_parado_total': 0
        }

    # -------------------
    # EFEITO CAOS - ruas
    # -------------------
    def _inicializar_caos(self) -> None:
        """Cria os vetores de caos por via (horizontal/vertical) segmentados ao longo da tela."""
        seg = CONFIG.CHAOS_TAMANHO_SEGMENTO
        self._caos_seg_h = math.ceil(CONFIG.LARGURA_TELA / seg) + 1
        self._caos_seg_v = math.ceil(CONFIG.ALTURA_TELA / seg) + 1

        # Cada linha horizontal tem um vetor de segmentos ao longo do X
        self.caos_horizontal: Dict[int, List[float]] = {
            linha: [1.0] * self._caos_seg_h for linha in range(self.linhas)
        }
        # Cada coluna vertical tem um vetor de segmentos ao longo do Y
        self.caos_vertical: Dict[int, List[float]] = {
            coluna: [1.0] * self._caos_seg_v for coluna in range(self.colunas)
        }

    def atualizar_caos(self) -> None:
        """Aleatoriza fatores ocasionalmente por segmento."""
        if not CONFIG.CHAOS_ATIVO:
            return
        p = CONFIG.CHAOS_PROB_MUTACAO
        fmin, fmax = CONFIG.CHAOS_FATOR_MIN, CONFIG.CHAOS_FATOR_MAX

        # horizontais
        for linha in range(self.linhas):
            v = self.caos_horizontal[linha]
            for i in range(len(v)):
                if random.random() < p:
                    v[i] = random.uniform(fmin, fmax)

        # verticais
        for coluna in range(self.colunas):
            v = self.caos_vertical[coluna]
            for i in range(len(v)):
                if random.random() < p:
                    v[i] = random.uniform(fmin, fmax)

    def obter_fator_caos(self, veiculo: Veiculo) -> float:
        """Retorna o fator de caos (multiplicador de velocidade máx local) para a posição do veículo."""
        if not CONFIG.CHAOS_ATIVO:
            return 1.0

        seg = CONFIG.CHAOS_TAMANHO_SEGMENTO

        if veiculo.direcao == Direcao.LESTE:
            # via horizontal: achar linha (índice da rua horizontal) e o segmento X
            linha_mais_prox = max(0, min(
                self.linhas - 1,
                round((veiculo.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_VERTICAL)
            ))
            seg_x = max(0, min(self._caos_seg_h - 1, int(veiculo.posicao[0] // seg)))
            return self.caos_horizontal[linha_mais_prox][seg_x]

        elif veiculo.direcao == Direcao.NORTE:
            # via vertical: achar coluna (índice da rua vertical) e o segmento Y
            coluna_mais_prox = max(0, min(
                self.colunas - 1,
                round((veiculo.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_HORIZONTAL)
            ))
            seg_y = max(0, min(self._caos_seg_v - 1, int(veiculo.posicao[1] // seg)))
            return self.caos_vertical[coluna_mais_prox][seg_y]

        return 1.0

    def _criar_cruzamentos(self) -> None:
        """Cria a grade de cruzamentos."""
        for linha in range(self.linhas):
            for coluna in range(self.colunas):
                x = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_HORIZONTAL
                y = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_VERTICAL

                id_cruzamento = (linha, coluna)
                self.cruzamentos[id_cruzamento] = Cruzamento(
                    (x, y), id_cruzamento, self.gerenciador_semaforos, self  # <<< passa self (malha)
                )

    def atualizar(self) -> None:
        """Atualiza toda a malha viária - CORRIGIDO com detecção global."""
        self.metricas['tempo_simulacao'] += 1

        # Atualiza "caos" das vias
        self.atualizar_caos()

        # Gera novos veículos
        for cruzamento in self.cruzamentos.values():
            novos_veiculos = cruzamento.gerar_veiculos()
            self.veiculos.extend(novos_veiculos)
            self.metricas['veiculos_total'] += len(novos_veiculos)

        # IMPORTANTE: Ordena TODOS os veículos globalmente por direção e posição
        veiculos_por_via = self._organizar_veiculos_por_via()

        # Atualiza veículos em cada cruzamento, passando a lista completa
        for cruzamento in self.cruzamentos.values():
            cruzamento.atualizar_veiculos(self.veiculos)

        # Coleta densidade para heurísticas
        densidade_por_cruzamento = {}
        for id_cruzamento, cruzamento in self.cruzamentos.items():
            densidade_por_cruzamento[id_cruzamento] = cruzamento.obter_densidade_por_direcao()

        # Atualiza semáforos com base na heurística
        self.gerenciador_semaforos.atualizar(densidade_por_cruzamento)

        # Remove veículos inativos e coleta métricas
        veiculos_ativos = []
        for veiculo in self.veiculos:
            if veiculo.ativo:
                veiculos_ativos.append(veiculo)
            else:
                # Veículo completou trajeto
                self.metricas['veiculos_concluidos'] += 1
                self.metricas['tempo_viagem_total'] += veiculo.tempo_viagem
                self.metricas['tempo_parado_total'] += veiculo.tempo_parado

        self.veiculos = veiculos_ativos

    def _organizar_veiculos_por_via(self) -> Dict[Tuple[Direcao, int, int], List[Veiculo]]:
        """
        Organiza por (direção, linha/coluna da via, indice_faixa).
        """
        veiculos_por_via = {}
        for v in self.veiculos:
            if v.direcao == Direcao.NORTE:
                via = round((v.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_HORIZONTAL)
                chave = (Direcao.NORTE, via, v.indice_faixa)
            elif v.direcao == Direcao.LESTE:
                via = round((v.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_VERTICAL)
                chave = (Direcao.LESTE, via, v.indice_faixa)
            else:
                continue
            veiculos_por_via.setdefault(chave, []).append(v)

        for (direcao, _, _), lista in veiculos_por_via.items():
            if direcao == Direcao.NORTE:
                lista.sort(key=lambda v: v.posicao[1], reverse=True)
            else:
                lista.sort(key=lambda v: v.posicao[0], reverse=True)
        return veiculos_por_via


    def mudar_heuristica(self, nova_heuristica: TipoHeuristica) -> None:
        """Muda a heurística de controle de semáforos."""
        self.gerenciador_semaforos.mudar_heuristica(nova_heuristica)

    def obter_estatisticas(self) -> Dict[str, any]:
        """Retorna estatísticas consolidadas."""
        veiculos_ativos = len(self.veiculos)

        # Calcula médias
        tempo_viagem_medio = 0
        tempo_parado_medio = 0

        if self.metricas['veiculos_concluidos'] > 0:
            tempo_viagem_medio = self.metricas['tempo_viagem_total'] / self.metricas['veiculos_concluidos'] / CONFIG.FPS
            tempo_parado_medio = self.metricas['tempo_parado_total'] / self.metricas['veiculos_concluidos'] / CONFIG.FPS

        return {
            'veiculos_ativos': veiculos_ativos,
            'veiculos_total': self.metricas['veiculos_total'],
            'veiculos_concluidos': self.metricas['veiculos_concluidos'],
            'tempo_viagem_medio': tempo_viagem_medio,
            'tempo_parado_medio': tempo_parado_medio,
            'heuristica': self.gerenciador_semaforos.obter_info_heuristica(),
            'tempo_simulacao': self.metricas['tempo_simulacao'] / CONFIG.FPS
        }

