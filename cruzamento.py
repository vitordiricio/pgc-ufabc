# cruzamento.py
import random
import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import pygame
from configuracao import CONFIG, Direcao, TipoHeuristica, TipoVeiculo
from veiculo import Veiculo
from semaforo import Semaforo, GerenciadorSemaforos


def _offset_faixa(idx: int) -> float:
    """Offset do centro da faixa em relação ao centro da via."""
    return (idx - (CONFIG.NUM_FAIXAS - 1) / 2.0) * CONFIG.LARGURA_FAIXA


# ----------------- INCIDENTE -----------------
@dataclass
class Incidente:
    direcao: Direcao        # NORTE (vertical) ou LESTE (horizontal)
    indice: int             # linha (p/ LESTE) ou coluna (p/ NORTE)
    seg_idx: int            # índice do segmento (grade do caos)
    fator: float            # 0.0 = bloqueio total, 0< f <1 = lentidão
    restante_frames: int    # tempo restante (frames)


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

        self.veiculos_por_direcao: Dict[Direcao, List[Veiculo]] = {
            Direcao.NORTE: [],
            Direcao.LESTE: []
        }

        self.largura_rua = CONFIG.LARGURA_RUA
        self.limites = self._calcular_limites()
        self._configurar_semaforos()

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

    def _posicao_spawn_por_faixa(self, direcao: Direcao, faixa_id: int) -> Tuple[float, float]:
        """Calcula a posição de spawn alinhada ao centro da faixa escolhida."""
        if direcao == Direcao.NORTE:
            x = self.centro_x + _offset_faixa(faixa_id)
            y = -50
            return (x, y)
        elif direcao == Direcao.LESTE:
            x = -50
            y = self.centro_y + _offset_faixa(faixa_id)
            return (x, y)
        return (0, 0)

    def _sortear_tipo_veiculo(self) -> TipoVeiculo:
        """Sorteia um tipo de veículo conforme a distribuição da configuração."""
        tipos = [t for t in CONFIG.TIPOS_ATIVOS]
        pesos = [CONFIG.DISTRIBUICAO_TIPOS.get(t, 0.0) for t in tipos]
        if sum(pesos) <= 0:
            return TipoVeiculo.CARRO
        return random.choices(tipos, weights=pesos, k=1)[0]

    def gerar_veiculos(self) -> List[Veiculo]:
        novos_veiculos = []
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            if not self.pode_gerar_veiculo(direcao):
                continue
            if random.random() < CONFIG.TAXA_GERACAO_VEICULO:
                faixa_id = random.randrange(CONFIG.NUM_FAIXAS)
                posicao = self._posicao_spawn_por_faixa(direcao, faixa_id)
                tipo = self._sortear_tipo_veiculo()
                if self._tem_espaco_para_gerar(direcao, posicao, tipo):
                    veiculo = Veiculo(direcao, posicao, self.id, tipo=tipo)
                    veiculo.faixa_id = faixa_id
                    novos_veiculos.append(veiculo)
                    self.veiculos_por_direcao[direcao].append(veiculo)
        return novos_veiculos

    def _tem_espaco_para_gerar(self, direcao: Direcao, posicao: Tuple[float, float], tipo: TipoVeiculo) -> bool:
        """Verifica com margem de segurança aumentada para evitar colisões no spawn."""
        dist_min_tipo = CONFIG.PARAMS_TIPO_VEICULO.get(tipo, {}).get('dist_min', CONFIG.DISTANCIA_MIN_VEICULO)
        
        # Margem de segurança maior para spawn
        margem_seguranca = dist_min_tipo * 3
        
        for veiculo in self.veiculos_por_direcao.get(direcao, []):
            dx = abs(veiculo.posicao[0] - posicao[0])
            dy = abs(veiculo.posicao[1] - posicao[1])
            
            if direcao == Direcao.NORTE:
                # Verifica se está na mesma faixa ou adjacente
                if dx < CONFIG.LARGURA_FAIXA * 1.5:
                    if dy < margem_seguranca:
                        return False
            elif direcao == Direcao.LESTE:
                # Verifica se está na mesma faixa ou adjacente
                if dy < CONFIG.LARGURA_FAIXA * 1.5:
                    if dx < margem_seguranca:
                        return False
                        
        # Verificação adicional: não gerar se houver veículo muito próximo em qualquer faixa
        for veiculo in self.malha.veiculos:
            if not veiculo.ativo:
                continue
                
            dist = math.sqrt((veiculo.posicao[0] - posicao[0])**2 + 
                           (veiculo.posicao[1] - posicao[1])**2)
            
            if dist < dist_min_tipo * 2:
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
        # Reassocia veículos próximos a este cruzamento
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            self.veiculos_por_direcao[direcao] = []

        for veiculo in todos_veiculos:
            if veiculo.direcao in CONFIG.DIRECOES_PERMITIDAS and self._veiculo_proximo_ao_cruzamento(veiculo):
                cruzamento_atual = self._determinar_cruzamento_veiculo(veiculo)
                if cruzamento_atual == self.id:
                    veiculo.resetar_controle_semaforo(self.id)
                    self.veiculos_por_direcao[veiculo.direcao].append(veiculo)

        # Atualiza cada veículo na ordem da via
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            veiculos = self.veiculos_por_direcao.get(direcao, [])
            if not veiculos:
                continue

            veiculos_ordenados = self._ordenar_veiculos_por_posicao(veiculos, direcao)
            semaforos_cruz = self.gerenciador_semaforos.semaforos.get(self.id, {})
            semaforo = semaforos_cruz.get(direcao)

            for veiculo in veiculos_ordenados:
                veiculo.processar_todos_veiculos(todos_veiculos)

                if semaforo:
                    posicao_parada = semaforo.obter_posicao_parada()
                    if self._veiculo_antes_da_linha(veiculo, posicao_parada):
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
        return {d: len(self.veiculos_por_direcao.get(d, [])) for d in CONFIG.DIRECOES_PERMITIDAS}

    def desenhar(self, tela: pygame.Surface) -> None:
        # área do cruzamento
        area_cruzamento = pygame.Rect(
            self.limites['esquerda'],
            self.limites['topo'],
            self.largura_rua,
            self.largura_rua
        )
        pygame.draw.rect(tela, CONFIG.CINZA, area_cruzamento)
        self._desenhar_linhas_parada(tela)

        # semáforos
        semaforos = self.gerenciador_semaforos.semaforos.get(self.id, {})
        for semaforo in semaforos.values():
            semaforo.desenhar(tela)

        if CONFIG.MOSTRAR_INFO_VEICULO:
            self._desenhar_info_debug(tela)

    def _desenhar_linhas_parada(self, tela: pygame.Surface) -> None:
        cor_linha = CONFIG.BRANCO
        largura_linha = 3
        # Norte
        pygame.draw.line(tela, cor_linha,
                         (self.limites['esquerda'], self.limites['topo'] - 20),
                         (self.limites['direita'], self.limites['topo'] - 20),
                         largura_linha)
        # Leste
        pygame.draw.line(tela, cor_linha,
                         (self.limites['esquerda'] - 20, self.limites['topo']),
                         (self.limites['esquerda'] - 20, self.limites['base']),
                         largura_linha)

    def _desenhar_info_debug(self, tela: pygame.Surface) -> None:
        fonte = pygame.font.SysFont('Arial', 12)
        texto = f"C({self.id[0]},{self.id[1]}) D:{self.estatisticas['densidade_atual']}"
        superficie = fonte.render(texto, True, CONFIG.BRANCO)
        tela.blit(superficie, (self.centro_x - 30, self.centro_y - 10))


class MalhaViaria:
    """Gerencia toda a malha viária com múltiplos cruzamentos, caos e incidentes."""

    def __init__(self, linhas: int = CONFIG.LINHAS_GRADE, colunas: int = CONFIG.COLUNAS_GRADE):
        self.linhas = linhas
        self.colunas = colunas
        self.veiculos: List[Veiculo] = []
        self.cruzamentos: Dict[Tuple[int, int], Cruzamento] = {}
        self.gerenciador_semaforos = GerenciadorSemaforos(CONFIG.HEURISTICA_ATIVA)

        # Caos
        self._inicializar_caos()
        # Incidentes
        self.incidentes: List[Incidente] = []

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

    # ---- INCIDENTES ----
    def _linha_mais_proxima(self, y: float) -> int:
        idx = round((y - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
        return max(0, min(self.linhas - 1, idx))

    def _coluna_mais_proxima(self, x: float) -> int:
        idx = round((x - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
        return max(0, min(self.colunas - 1, idx))

    def _seg_idx_x(self, x: float) -> int:
        return max(0, min(self._caos_seg_h - 1, int(x // CONFIG.CHAOS_TAMANHO_SEGMENTO)))

    def _seg_idx_y(self, y: float) -> int:
        return max(0, min(self._caos_seg_v - 1, int(y // CONFIG.CHAOS_TAMANHO_SEGMENTO)))

    def _localizar_segmento_por_pos(self, pos: Tuple[int, int]) -> Optional[Tuple[Direcao, int, int]]:
        """Retorna (direcao, indice, seg_idx) do segmento mais próximo da via, ou None se fora da via."""
        x, y = pos
        # distância até eixos
        linha = self._linha_mais_proxima(y)
        y_centro = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
        dist_h = abs(y - y_centro)

        coluna = self._coluna_mais_proxima(x)
        x_centro = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
        dist_v = abs(x - x_centro)

        limite = CONFIG.LARGURA_RUA / 2 + 6  # margem
        candidato: Optional[Tuple[Direcao, int, int]] = None

        if dist_h <= limite and (dist_h <= dist_v or dist_v > limite):
            # via horizontal (LESTE)
            seg = self._seg_idx_x(x)
            candidato = (Direcao.LESTE, linha, seg)
        elif dist_v <= limite:
            # via vertical (NORTE)
            seg = self._seg_idx_y(y)
            candidato = (Direcao.NORTE, coluna, seg)

        return candidato

    def adicionar_incidente(self, direcao: Direcao, indice: int, seg_idx: int, duracao_s: int, fator: float) -> Incidente:
        # remove duplicado
        self.incidentes = [i for i in self.incidentes if not (i.direcao == direcao and i.indice == indice and i.seg_idx == seg_idx)]
        inc = Incidente(direcao, indice, seg_idx, fator, int(duracao_s * CONFIG.FPS))
        self.incidentes.append(inc)
        return inc

    def remover_incidente_chave(self, direcao: Direcao, indice: int, seg_idx: int) -> bool:
        antes = len(self.incidentes)
        self.incidentes = [i for i in self.incidentes if not (i.direcao == direcao and i.indice == indice and i.seg_idx == seg_idx)]
        return len(self.incidentes) < antes

    def toggle_incidente_por_pos(self, pos: Tuple[int, int], fator: float, duracao_s: int) -> bool:
        """Cria/Remove no segmento clicado. Retorna True se criou, False se removeu/nada."""
        loc = self._localizar_segmento_por_pos(pos)
        if not loc or not CONFIG.INCIDENTES_ATIVOS:
            return False
        d, idx, seg = loc
        # se já existe: remove
        for i in self.incidentes:
            if i.direcao == d and i.indice == idx and i.seg_idx == seg:
                self.remover_incidente_chave(d, idx, seg)
                return False
        # senão cria
        self.adicionar_incidente(d, idx, seg, duracao_s, fator)
        return True

    def remover_incidente_por_pos(self, pos: Tuple[int, int]) -> bool:
        loc = self._localizar_segmento_por_pos(pos)
        if not loc:
            return False
        d, idx, seg = loc
        return self.remover_incidente_chave(d, idx, seg)

    def atualizar_incidentes(self) -> None:
        vivos = []
        for inc in self.incidentes:
            inc.restante_frames -= 1
            if inc.restante_frames > 0:
                vivos.append(inc)
        self.incidentes = vivos

    def _fator_incidente_para_pos(self, pos: Tuple[float, float], direcao: Direcao) -> float:
        """Retorna fator multiplicativo (0..1) do incidente no segmento da via do veículo."""
        if not CONFIG.INCIDENTES_ATIVOS or not self.incidentes:
            return 1.0
        x, y = pos
        if direcao == Direcao.LESTE:
            linha = self._linha_mais_proxima(y)
            seg = self._seg_idx_x(x)
            fatores = [i.fator for i in self.incidentes if i.direcao == Direcao.LESTE and i.indice == linha and i.seg_idx == seg]
        else:
            coluna = self._coluna_mais_proxima(x)
            seg = self._seg_idx_y(y)
            fatores = [i.fator for i in self.incidentes if i.direcao == Direcao.NORTE and i.indice == coluna and i.seg_idx == seg]
        if not fatores:
            return 1.0
        f = 1.0
        for fi in fatores:
            f *= fi  # compõe fatores (ex.: duas lentidões)
        return max(0.0, min(1.0, f))

    def _rect_incidente(self, inc: Incidente) -> pygame.Rect:
        """Retângulo do segmento afetado para desenhar overlay."""
        seg = CONFIG.CHAOS_TAMANHO_SEGMENTO
        if inc.direcao == Direcao.LESTE:
            y_c = CONFIG.POSICAO_INICIAL_Y + inc.indice * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            y_top = int(y_c - CONFIG.LARGURA_RUA // 2)
            x_left = int(inc.seg_idx * seg)
            return pygame.Rect(x_left, y_top, seg, CONFIG.LARGURA_RUA)
        else:
            x_c = CONFIG.POSICAO_INICIAL_X + inc.indice * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            x_left = int(x_c - CONFIG.LARGURA_RUA // 2)
            y_top = int(inc.seg_idx * seg)
            return pygame.Rect(x_left, y_top, CONFIG.LARGURA_RUA, seg)

    def _desenhar_incidentes(self, tela: pygame.Surface) -> None:
        if not self.incidentes:
            return
        for inc in self.incidentes:
            # cor por tipo (bloqueio vs lentidão)
            cor = CONFIG.INCIDENTE_COR_BLOQUEIO if inc.fator <= 0.01 else CONFIG.INCIDENTE_COR_LENTIDAO
            rect = self._rect_incidente(inc)
            surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            surf.fill(cor)
            tela.blit(surf, rect.topleft)
            # contador simples
            fonte = pygame.font.SysFont('Arial', 12)
            segundos = max(0, int(inc.restante_frames / CONFIG.FPS))
            texto = f"{'BLQ' if inc.fator<=0.01 else 'LEN'} {segundos}s"
            img = fonte.render(texto, True, (0, 0, 0))
            tela.blit(img, (rect.x + 4, rect.y + 4))

    # ---- FATOR DINÂMICO (CAOS * INCIDENTE) ----
    def obter_fator_caos(self, veiculo: Veiculo) -> float:
        # Base: caos (ou 1.0 se desativado)
        if CONFIG.CHAOS_ATIVO:
            seg = CONFIG.CHAOS_TAMANHO_SEGMENTO
            if veiculo.direcao == Direcao.LESTE:
                linha_mais_prox = max(0, min(
                    self.linhas - 1,
                    round((veiculo.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
                ))
                seg_x = max(0, min(self._caos_seg_h - 1, int(veiculo.posicao[0] // seg)))
                fator = self.caos_horizontal[linha_mais_prox][seg_x]
            elif veiculo.direcao == Direcao.NORTE:
                coluna_mais_prox = max(0, min(
                    self.colunas - 1,
                    round((veiculo.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
                ))
                seg_y = max(0, min(self._caos_seg_v - 1, int(veiculo.posicao[1] // seg)))
                fator = self.caos_vertical[coluna_mais_prox][seg_y]
            else:
                fator = 1.0
        else:
            fator = 1.0

        # Multiplica por incidente (0..1)
        fator *= self._fator_incidente_para_pos(tuple(veiculo.posicao), veiculo.direcao)
        return fator

    # ----------------- DESENHO DE RUAS COM MÚLTIPLAS FAIXAS -----------------
    def _desenhar_ruas(self, tela: pygame.Surface) -> None:
        # Horizontais (LESTE)
        for linha in range(self.linhas):
            y_centro = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            y_top = y_centro - CONFIG.LARGURA_RUA // 2

            # Fundo
            pygame.draw.rect(tela, CONFIG.CINZA_ESCURO,
                             (0, y_top, CONFIG.LARGURA_TELA, CONFIG.LARGURA_RUA))

            # Linhas de borda
            pygame.draw.line(tela, CONFIG.BRANCO,
                             (0, y_top), (CONFIG.LARGURA_TELA, y_top), 2)
            pygame.draw.line(tela, CONFIG.BRANCO,
                             (0, y_top + CONFIG.LARGURA_RUA),
                             (CONFIG.LARGURA_TELA, y_top + CONFIG.LARGURA_RUA), 2)

            # Divisórias de faixa (tracejadas)
            for div in range(1, CONFIG.NUM_FAIXAS):
                y = y_top + div * CONFIG.LARGURA_FAIXA
                self._linha_tracejada_h(tela, y, 0, CONFIG.LARGURA_TELA, 18, 12, 2)

            # Setas de direção (opcionais)
            self._desenhar_setas_horizontais(tela, y_centro, Direcao.LESTE)

        # Verticais (NORTE)
        for coluna in range(self.colunas):
            x_centro = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            x_left = x_centro - CONFIG.LARGURA_RUA // 2

            pygame.draw.rect(tela, CONFIG.CINZA_ESCURO,
                             (x_left, 0, CONFIG.LARGURA_RUA, CONFIG.ALTURA_TELA))

            pygame.draw.line(tela, CONFIG.BRANCO,
                             (x_left, 0), (x_left, CONFIG.ALTURA_TELA), 2)
            pygame.draw.line(tela, CONFIG.BRANCO,
                             (x_left + CONFIG.LARGURA_RUA, 0),
                             (x_left + CONFIG.LARGURA_RUA, CONFIG.ALTURA_TELA), 2)

            for div in range(1, CONFIG.NUM_FAIXAS):
                x = x_left + div * CONFIG.LARGURA_FAIXA
                self._linha_tracejada_v(tela, x, 0, CONFIG.ALTURA_TELA, 18, 12, 2)

            self._desenhar_setas_verticais(tela, x_centro, Direcao.NORTE)

    # util: linhas tracejadas
    def _linha_tracejada_h(self, tela, y, x0, x1, dash=16, gap=10, esp=2):
        x = x0
        while x < x1:
            xe = min(x + dash, x1)
            pygame.draw.line(tela, CONFIG.CINZA_CLARO, (x, y), (xe, y), esp)
            x += dash + gap

    def _linha_tracejada_v(self, tela, x, y0, y1, dash=16, gap=10, esp=2):
        y = y0
        while y < y1:
            ye = min(y + dash, y1)
            pygame.draw.line(tela, CONFIG.CINZA_CLARO, (x, y), (x, ye), esp)
            y += dash + gap

    def _desenhar_setas_horizontais(self, tela: pygame.Surface, y: float, direcao: Direcao) -> None:
        if not CONFIG.MOSTRAR_DIRECAO_FLUXO:
            return
        intervalo = 100
        tamanho_seta = 15
        for x in range(50, CONFIG.LARGURA_TELA, intervalo):
            perto = False
            for coluna in range(self.colunas):
                x_cr = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                if abs(x - x_cr) < CONFIG.LARGURA_RUA:
                    perto = True
                    break
            if not perto:
                pontos = [(x - tamanho_seta, y - 5), (x - tamanho_seta, y + 5), (x, y)]
                pygame.draw.polygon(tela, CONFIG.AMARELO, pontos)

    def _desenhar_setas_verticais(self, tela: pygame.Surface, x: float, direcao: Direcao) -> None:
        if not CONFIG.MOSTRAR_DIRECAO_FLUXO:
            return
        intervalo = 100
        tamanho_seta = 15
        for y in range(50, CONFIG.ALTURA_TELA, intervalo):
            perto = False
            for linha in range(self.linhas):
                y_cr = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                if abs(y - y_cr) < CONFIG.LARGURA_RUA:
                    perto = True
                    break
            if not perto:
                pontos = [(x - 5, y - tamanho_seta), (x + 5, y - tamanho_seta), (x, y)]
                pygame.draw.polygon(tela, CONFIG.AMARELO, pontos)

    def desenhar(self, tela: pygame.Surface) -> None:
        # Ruas
        self._desenhar_ruas(tela)
        # Overlays de incidentes (entre ruas e objetos)
        self._desenhar_incidentes(tela)
        # Cruzamentos e semáforos
        for cruzamento in self.cruzamentos.values():
            cruzamento.desenhar(tela)
        # Veículos
        for veiculo in self.veiculos:
            veiculo.desenhar(tela)

    # ---- LOOP ----
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
        self.atualizar_incidentes()

        # Spawns
        for cruzamento in self.cruzamentos.values():
            novos_veiculos = cruzamento.gerar_veiculos()
            self.veiculos.extend(novos_veiculos)
            self.metricas['veiculos_total'] += len(novos_veiculos)

        # Atualiza veículos por cruzamento
        for cruzamento in self.cruzamentos.values():
            cruzamento.atualizar_veiculos(self.veiculos)

        # Densidades para heurística
        densidade_por_cruzamento = {}
        for id_cruzamento, cruzamento in self.cruzamentos.items():
            densidade_por_cruzamento[id_cruzamento] = cruzamento.obter_densidade_por_direcao()

        self.gerenciador_semaforos.atualizar(densidade_por_cruzamento)

        # Limpa veículos inativos e agrega métricas
        veiculos_ativos = []
        for veiculo in self.veiculos:
            if veiculo.ativo:
                veiculos_ativos.append(veiculo)
            else:
                self.metricas['veiculos_concluidos'] += 1
                self.metricas['tempo_viagem_total'] += veiculo.tempo_viagem
                self.metricas['tempo_parado_total'] += veiculo.tempo_parado
        self.veiculos = veiculos_ativos

    # ---- Estatísticas + Controle ----
    def obter_estatisticas(self) -> Dict[str, any]:
        """Retorna estatísticas consolidadas para o painel."""
        veiculos_ativos = len(self.veiculos)

        tempo_viagem_medio = 0.0
        tempo_parado_medio = 0.0
        concl = self.metricas['veiculos_concluidos']

        if concl > 0:
            tempo_viagem_medio = (
                self.metricas['tempo_viagem_total'] / concl / CONFIG.FPS
            )
            tempo_parado_medio = (
                self.metricas['tempo_parado_total'] / concl / CONFIG.FPS
            )

        return {
            'veiculos_ativos': veiculos_ativos,
            'veiculos_total': self.metricas['veiculos_total'],
            'veiculos_concluidos': self.metricas['veiculos_concluidos'],
            'tempo_viagem_medio': tempo_viagem_medio,
            'tempo_parado_medio': tempo_parado_medio,
            'heuristica': self.gerenciador_semaforos.obter_info_heuristica(),
            'tempo_simulacao': self.metricas['tempo_simulacao'] / CONFIG.FPS,
        }

    def mudar_heuristica(self, nova_heuristica: TipoHeuristica) -> None:
        """Muda a heurística de controle de semáforos para toda a malha."""
        self.gerenciador_semaforos.mudar_heuristica(nova_heuristica)