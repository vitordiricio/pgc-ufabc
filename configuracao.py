"""
Configurações para a simulação de malha viária urbana com múltiplos cruzamentos.
Sistema com vias de mão única: Horizontal (Leste→Oeste) e Vertical (Norte→Sul)
"""

from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum, auto

class Direcao(Enum):
    NORTE = auto()
    SUL = auto()
    LESTE = auto()
    OESTE = auto()

class EstadoSemaforo(Enum):
    VERMELHO = auto()
    AMARELO = auto()
    VERDE = auto()

class TipoHeuristica(Enum):
    TEMPO_FIXO = auto()
    ADAPTATIVA_SIMPLES = auto()
    ADAPTATIVA_DENSIDADE = auto()
    WAVE_GREEN = auto()
    MANUAL = auto()

@dataclass
class Configuracao:
    # Tela
    LARGURA_TELA: int = 1920
    ALTURA_TELA: int = 1080
    FPS: int = 60

    GRACE_FRAMES_LANE_CHANGE = 3  # frames imunes a falso-positivo pós troca
    COOLDOWN_MUDANCA_FAIXA = 60  # já usado
    GANHO_MIN_MUDANCA_FAIXA = 0.2  # já usado
    DIST_MIN_TROCA_PERTO_CRUZAMENTO = 120  # já usado

    # Grade
    LINHAS_GRADE: int = 3
    COLUNAS_GRADE: int = 3

    @property
    def ESPACAMENTO_HORIZONTAL(self) -> int:
        return self.LARGURA_TELA // self.COLUNAS_GRADE

    @property
    def ESPACAMENTO_VERTICAL(self) -> int:
        return self.ALTURA_TELA // self.LINHAS_GRADE

    # Cores
    PRETO: tuple[int, int, int] = (20, 20, 20)
    BRANCO: tuple[int, int, int] = (255, 255, 255)
    VERMELHO: tuple[int, int, int] = (220, 50, 50)
    AMARELO: tuple[int, int, int] = (255, 200, 0)
    VERDE: tuple[int, int, int] = (50, 220, 50)
    AZUL: tuple[int, int, int] = (50, 100, 200)
    CINZA: tuple[int, int, int] = (128, 128, 128)
    CINZA_ESCURO: tuple[int, int, int] = (70, 70, 70)
    CINZA_CLARO: tuple[int, int, int] = (200, 200, 200)
    VERDE_ESCURO: tuple[int, int, int] = (0, 100, 0)

    # Cores veículos
    CORES_VEICULO: List[tuple[int, int, int]] = field(default_factory=lambda: [
        (220, 50, 50),(50, 100, 200),(50, 180, 50),(255, 140, 0),
        (148, 0, 211),(255, 215, 0),(0, 191, 255),(255, 20, 147)
    ])

    # >>> NOVO: número de faixas por via (n ≥ 2)
    FAIXAS_POR_VIA: int = 2

    # Largura da rua (total, cobrindo todas as faixas)
    # Aumentei para comportar veículos confortavelmente em 2+ faixas
    LARGURA_RUA: int = 80  # ex.: 2 faixas de ~40px

    # >>> LARGURA_FAIXA agora é propriedade derivada
    @property
    def LARGURA_FAIXA(self) -> int:
        # largura inteira da faixa; garante >= 28 px para caber o veículo (25px) + margem
        return max(28, self.LARGURA_RUA // max(1, self.FAIXAS_POR_VIA))

    # Sistema de mão única (mantém seu comportamento)
    DIRECOES_PERMITIDAS: List[Direcao] = field(default_factory=lambda: [Direcao.NORTE, Direcao.LESTE])

    PONTOS_SPAWN: Dict[str, bool] = field(default_factory=lambda: {
        'NORTE': True,'SUL': False,'LESTE': True,'OESTE': False
    })

    # Veículos
    LARGURA_VEICULO: int = 25
    ALTURA_VEICULO: int = 35
    TAXA_GERACAO_VEICULO: float = 0.01
    VELOCIDADE_VEICULO: float = 0.5
    VELOCIDADE_MAX_VEICULO: float = 1.0
    VELOCIDADE_MIN_VEICULO: float = 0.0
    ACELERACAO_VEICULO: float = 0.15
    DESACELERACAO_VEICULO: float = 0.25
    DESACELERACAO_EMERGENCIA: float = 0.5
    DISTANCIA_MIN_VEICULO: int = 50
    DISTANCIA_SEGURANCA: int = 40
    DISTANCIA_REACAO: int = 80

    # Semáforo
    TAMANHO_SEMAFORO: int = 12
    ESPACAMENTO_SEMAFORO: int = 4
    TEMPO_SEMAFORO_PADRAO: Dict[EstadoSemaforo, int] = field(default_factory=lambda: {
        EstadoSemaforo.VERDE: 180, EstadoSemaforo.AMARELO: 60, EstadoSemaforo.VERMELHO: 240
    })

    # Heurística
    HEURISTICA_ATIVA: 'TipoHeuristica' = 'TipoHeuristica'.ADAPTATIVA_DENSIDADE if False else None
    HEURISTICA_ATIVA: TipoHeuristica = TipoHeuristica.ADAPTATIVA_DENSIDADE
    LIMIAR_DENSIDADE_BAIXA: int = 3
    LIMIAR_DENSIDADE_MEDIA: int = 6
    LIMIAR_DENSIDADE_ALTA: int = 10
    TEMPO_VERDE_DENSIDADE_BAIXA: int = 120
    TEMPO_VERDE_DENSIDADE_MEDIA: int = 180
    TEMPO_VERDE_DENSIDADE_ALTA: int = 300

    # Detecção
    DISTANCIA_DETECCAO_SEMAFORO: int = 120
    DISTANCIA_PARADA_SEMAFORO: int = 15

    # Visuais
    MOSTRAR_GRID: bool = True
    MOSTRAR_ESTATISTICAS: bool = True
    MOSTRAR_INFO_VEICULO: bool = False
    MOSTRAR_DIRECAO_FLUXO: bool = True
    TAMANHO_FONTE_PEQUENA: int = 14
    TAMANHO_FONTE_MEDIA: int = 18
    TAMANHO_FONTE_GRANDE: int = 24

    # Métricas
    COLETAR_METRICAS: bool = True
    INTERVALO_METRICAS: int = 300

    # Posição base
    MARGEM_TELA: int = 100

    @property
    def POSICAO_INICIAL_X(self) -> int:
        largura_total = (self.COLUNAS_GRADE - 1) * self.ESPACAMENTO_HORIZONTAL
        return (self.LARGURA_TELA - largura_total) // 2

    @property
    def POSICAO_INICIAL_Y(self) -> int:
        altura_total = (self.LINHAS_GRADE - 1) * self.ESPACAMENTO_VERTICAL
        return (self.ALTURA_TELA - altura_total) // 2 + 50

    # ====== CAOS (inalterado) ======
    CHAOS_ATIVO: bool = True
    CHAOS_TAMANHO_SEGMENTO: int = 160
    CHAOS_FATOR_MIN: float = 0.6
    CHAOS_FATOR_MAX: float = 1.2
    CHAOS_PROB_MUTACAO: float = 0.002
    CHAOS_MOSTRAR: bool = False

    def __post_init__(self):
        # Garante que cada faixa comporte o veículo com folga
        min_lane = max(self.LARGURA_VEICULO + 6, 28)
        min_road = min_lane * max(1, self.FAIXAS_POR_VIA)
        if self.LARGURA_RUA < min_road:
            self.LARGURA_RUA = min_road

# Instância singleton
CONFIG = Configuracao()