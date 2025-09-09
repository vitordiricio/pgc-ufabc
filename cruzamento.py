import random
import math
from typing import List, Dict, Tuple
import pygame
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

        # Configurações do cruzamento
        self.largura_rua = CONFIG.LARGURA_RUA
        self.limites = self._calcular_limites()

        # Configurar semáforos
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
                posicao = self._calcular_posicao_inicial(direcao)
                if self._tem_espaco_para_gerar(direcao, posicao):
                    veiculo = Veiculo(direcao, posicao, self.id)
                    novos_veiculos.append(veiculo)
                    self.veiculos_por_direcao[direcao].append(veiculo)
        return novos_veiculos

    def _calcular_posicao_inicial(self, direcao: Direcao) -> Tuple[float, float]:
        if direcao == Direcao.NORTE:
            return (self.centro_x, -50)
        elif direcao == Direcao.LESTE:
            return (-50, self.centro_y)
        else:
            return (0, 0)

    def _tem_espaco_para_gerar(self, direcao: Direcao, posicao: Tuple[float, float]) -> bool:
        for veiculo in self.veiculos_por_direcao.get(direcao, []):
            dx = abs(veiculo.posicao[0] - posicao[0])
            dy = abs(veiculo.posicao[1] - posicao[1])

            if direcao == Direcao.NORTE:
                if dy < CONFIG.DISTANCIA_MIN_VEICULO * 2:
                    return False
            elif direcao == Direcao.LESTE:
                if dx < CONFIG.DISTANCIA_MIN_VEICULO * 2:
                    return False
        return True

    def _determinar_cruzamento_veiculo(self, veiculo: Veiculo) -> Tuple[int, int]:
        coluna = int((veiculo.posicao[0] - CONFIG.POSICAO_INICIAL_X + CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS / 2) /
                     CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
        linha = int((veiculo.posicao[1] - CONFIG.POSICAO_INICIAL_Y + CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS / 2) /
                    CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
        coluna = max(0, min(coluna, CONFIG.COLUNAS_GRADE - 1))
        linha = max(0, min(linha, CONFIG.LINHAS_GRADE - 1))
        return (linha, coluna)

    def atualizar_veiculos(self, todos_veiculos: List[Veiculo]) -> None:
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            self.veiculos_por_direcao[direcao] = []

        veiculos_proximos = []
        for veiculo in todos_veiculos:
            if veiculo.direcao in CONFIG.DIRECOES_PERMITIDAS and self._veiculo_proximo_ao_cruzamento(veiculo):
                cruzamento_atual = self._determinar_cruzamento_veiculo(veiculo)
                if cruzamento_atual == self.id:
                    veiculo.resetar_controle_semaforo(self.id)
                    self.veiculos_por_direcao[veiculo.direcao].append(veiculo)
                    veiculos_proximos.append(veiculo)

        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            veiculos = self.veiculos_por_direcao.get(direcao, [])
            if not veiculos:
                continue

            veiculos_ordenados = self._ordenar_veiculos_por_posicao(veiculos, direcao)

            semaforos_cruz = self.gerenciador_semaforos.semaforos.get(self.id, {})
            semaforo = semaforos_cruz.get(direcao)

            for i, veiculo in enumerate(veiculos_ordenados):
                veiculo.processar_todos_veiculos(todos_veiculos)

                if semaforo:
                    posicao_parada = semaforo.obter_posicao_parada()
                    if self._veiculo_antes_da_linha(veiculo, posicao_parada):
                        # >>> PASSA também todos os semáforos do cruzamento e o centro do cruzamento (para curvas)
                        veiculo.processar_semaforo(
                            semaforo,
                            posicao_parada,
                            semaforos_cruz,
                            (self.centro_x, self.centro_y)
                        )

                veiculo.atualizar(1.0, todos_veiculos, self.malha)

                if veiculo.parado and veiculo.aguardando_semaforo:
                    self.estatisticas['tempo_espera_acumulado'] += 1

        self.estatisticas['densidade_atual'] = sum(
            len(veiculos) for direcao, veiculos in self.veiculos_por_direcao.items()
            if direcao in CONFIG.DIRECOES_PERMITIDAS
        )

    def _veiculo_antes_da_linha(self, veiculo: Veiculo, posicao_parada: Tuple[float, float]) -> bool:
        margem = CONFIG.DISTANCIA_DETECCAO_SEMAFORO
        if veiculo.direcao == Direcao.NORTE:
            return veiculo.posicao[1] < posicao_parada[1] + margem
        elif veiculo.direcao == Direcao.LESTE:
            return veiculo.posicao[0] < posicao_parada[0] + margem
        return False

    def _veiculo_proximo_ao_cruzamento(self, veiculo: Veiculo) -> bool:
        distancia_limite = CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS * 0.7
        dx = abs(veiculo.posicao[0] - self.centro_x)
        dy = abs(veiculo.posicao[1] - self.centro_y)
        return dx < distancia_limite or dy < distancia_limite

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

    def desenhar(self, tela: pygame.Surface) -> None:
        area_cruzamento = pygame.Rect(
            self.limites['esquerda'],
            self.limites['topo'],
            self.largura_rua,
            self.largura_rua
        )
        pygame.draw.rect(tela, CONFIG.CINZA, area_cruzamento)
        self._desenhar_linhas_parada(tela)

        semaforos = self.gerenciador_semaforos.semaforos.get(self.id, {})
        for semaforo in semaforos.values():
            semaforo.desenhar(tela)

        if CONFIG.MOSTRAR_INFO_VEICULO:
            self._desenhar_info_debug(tela)

    def _desenhar_linhas_parada(self, tela: pygame.Surface) -> None:
        cor_linha = CONFIG.BRANCO
        largura_linha = 3

        # Linha Norte
        pygame.draw.line(tela,
                         cor_linha,
                         (self.limites['esquerda'], self.limites['topo'] - 20),
                         (self.limites['direita'], self.limites['topo'] - 20),
                         largura_linha)
        # Linha Leste
        pygame.draw.line(tela,
                         cor_linha,
                         (self.limites['esquerda'] - 20, self.limites['topo']),
                         (self.limites['esquerda'] - 20, self.limites['base']),
                         largura_linha)

    def _desenhar_info_debug(self, tela: pygame.Surface) -> None:
        fonte = pygame.font.SysFont('Arial', 12)
        texto = f"C({self.id[0]},{self.id[1]}) D:{self.estatisticas['densidade_atual']}"
        superficie = fonte.render(texto, True, CONFIG.BRANCO)
        tela.blit(superficie, (self.centro_x - 30, self.centro_y - 10))


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
            'tempo_parado_total': 0
        }

    # ---- EFEITO CAOS ----
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
                round((veiculo.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
            ))
            seg_x = max(0, min(self._caos_seg_h - 1, int(veiculo.posicao[0] // seg)))
            return self.caos_horizontal[linha_mais_prox][seg_x]
        elif veiculo.direcao == Direcao.NORTE:
            coluna_mais_prox = max(0, min(
                self.colunas - 1,
                round((veiculo.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
            ))
            seg_y = max(0, min(self._caos_seg_v - 1, int(veiculo.posicao[1] // seg)))
            return self.caos_vertical[coluna_mais_prox][seg_y]
        return 1.0

    def _criar_cruzamentos(self) -> None:
        for linha in range(self.linhas):
            for coluna in range(self.colunas):
                x = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                y = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                id_cruzamento = (linha, coluna)
                self.cruzamentos[id_cruzamento] = Cruzamento(
                    (x, y), id_cruzamento, self.gerenciador_semaforos, self
                )

    def atualizar(self) -> None:
        self.metricas['tempo_simulacao'] += 1
        self.atualizar_caos()

        for cruzamento in self.cruzamentos.values():
            novos_veiculos = cruzamento.gerar_veiculos()
            self.veiculos.extend(novos_veiculos)
            self.metricas['veiculos_total'] += len(novos_veiculos)

        _ = self._organizar_veiculos_por_via()

        for cruzamento in self.cruzamentos.values():
            cruzamento.atualizar_veiculos(self.veiculos)

        densidade_por_cruzamento = {}
        for id_cruzamento, cruzamento in self.cruzamentos.items():
            densidade_por_cruzamento[id_cruzamento] = cruzamento.obter_densidade_por_direcao()

        self.gerenciador_semaforos.atualizar(densidade_por_cruzamento)

        veiculos_ativos = []
        for veiculo in self.veiculos:
            if veiculo.ativo:
                veiculos_ativos.append(veiculo)
            else:
                self.metricas['veiculos_concluidos'] += 1
                self.metricas['tempo_viagem_total'] += veiculo.tempo_viagem
                self.metricas['tempo_parado_total'] += veiculo.tempo_parado
        self.veiculos = veiculos_ativos

    def _organizar_veiculos_por_via(self) -> Dict[Tuple[Direcao, int], List[Veiculo]]:
        veiculos_por_via = {}
        for veiculo in self.veiculos:
            if veiculo.direcao == Direcao.NORTE:
                via_x = round(veiculo.posicao[0] / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
                chave = (Direcao.NORTE, via_x)
            elif veiculo.direcao == Direcao.LESTE:
                via_y = round(veiculo.posicao[1] / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
                chave = (Direcao.LESTE, via_y)
            else:
                continue
            if chave not in veiculos_por_via:
                veiculos_por_via[chave] = []
            veiculos_por_via[chave].append(veiculo)

        for chave, veiculos in veiculos_por_via.items():
            direcao = chave[0]
            if direcao == Direcao.NORTE:
                veiculos.sort(key=lambda v: v.posicao[1], reverse=True)
            elif direcao == Direcao.LESTE:
                veiculos.sort(key=lambda v: v.posicao[0], reverse=True)
        return veiculos_por_via

    def mudar_heuristica(self, nova_heuristica: TipoHeuristica) -> None:
        self.gerenciador_semaforos.mudar_heuristica(nova_heuristica)

    def obter_estatisticas(self) -> Dict[str, any]:
        veiculos_ativos = len(self.veiculos)
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

    def desenhar(self, tela: pygame.Surface) -> None:
        # Ruas horizontais
        for linha in range(self.linhas):
            y = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            pygame.draw.rect(tela, CONFIG.CINZA_ESCURO,
                             (0, y - CONFIG.LARGURA_RUA // 2,
                              CONFIG.LARGURA_TELA, CONFIG.LARGURA_RUA))
            self._desenhar_setas_horizontais(tela, y, Direcao.LESTE)
            pygame.draw.line(tela, CONFIG.BRANCO,
                             (0, y - CONFIG.LARGURA_RUA // 2),
                             (CONFIG.LARGURA_TELA, y - CONFIG.LARGURA_RUA // 2), 2)
            pygame.draw.line(tela, CONFIG.BRANCO,
                             (0, y + CONFIG.LARGURA_RUA // 2),
                             (CONFIG.LARGURA_TELA, y + CONFIG.LARGURA_RUA // 2), 2)

        # Ruas verticais
        for coluna in range(self.colunas):
            x = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            pygame.draw.rect(tela, CONFIG.CINZA_ESCURO,
                             (x - CONFIG.LARGURA_RUA // 2, 0,
                              CONFIG.LARGURA_RUA, CONFIG.ALTURA_TELA))
            self._desenhar_setas_verticais(tela, x, Direcao.NORTE)
            pygame.draw.line(tela, CONFIG.BRANCO,
                             (x - CONFIG.LARGURA_RUA // 2, 0),
                             (x - CONFIG.LARGURA_RUA // 2, CONFIG.ALTURA_TELA), 2)
            pygame.draw.line(tela, CONFIG.BRANCO,
                             (x + CONFIG.LARGURA_RUA // 2, 0),
                             (x + CONFIG.LARGURA_RUA // 2, CONFIG.ALTURA_TELA), 2)

        # Cruzamentos
        for cruzamento in self.cruzamentos.values():
            cruzamento.desenhar(tela)

        # Veículos
        for veiculo in self.veiculos:
            veiculo.desenhar(tela)

    def _desenhar_setas_horizontais(self, tela: pygame.Surface, y: float, direcao: Direcao) -> None:
        if not CONFIG.MOSTRAR_DIRECAO_FLUXO:
            return
        intervalo = 100
        tamanho_seta = 15
        for x in range(50, CONFIG.LARGURA_TELA, intervalo):
            perto_de_cruzamento = False
            for coluna in range(self.colunas):
                x_cruzamento = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                if abs(x - x_cruzamento) < CONFIG.LARGURA_RUA:
                    perto_de_cruzamento = True
                    break
            if not perto_de_cruzamento:
                pontos = [
                    (x - tamanho_seta, y - 5),
                    (x - tamanho_seta, y + 5),
                    (x, y)
                ]
                pygame.draw.polygon(tela, CONFIG.AMARELO, pontos)

    def _desenhar_setas_verticais(self, tela: pygame.Surface, x: float, direcao: Direcao) -> None:
        if not CONFIG.MOSTRAR_DIRECAO_FLUXO:
            return
        intervalo = 100
        tamanho_seta = 15
        for y in range(50, CONFIG.ALTURA_TELA, intervalo):
            perto_de_cruzamento = False
            for linha in range(self.linhas):
                y_cruzamento = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                if abs(y - y_cruzamento) < CONFIG.LARGURA_RUA:
                    perto_de_cruzamento = True
                    break
            if not perto_de_cruzamento:
                pontos = [
                    (x - 5, y - tamanho_seta),
                    (x + 5, y - tamanho_seta),
                    (x, y)
                ]
                pygame.draw.polygon(tela, CONFIG.AMARELO, pontos)
