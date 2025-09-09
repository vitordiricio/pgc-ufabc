from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from enum import Enum, auto


class Direcao(Enum):
    """Enumeração das direções possíveis - VIAS DE MÃO ÚNICA."""
    NORTE = auto()  # Movimento de cima para baixo (↓) - Norte→Sul
    SUL = auto()    # Movimento de baixo para cima (↑) - Sul→Norte (DESATIVADO)
    LESTE = auto()  # Movimento da esquerda para direita (→) - Leste→Oeste
    OESTE = auto()  # Movimento da direita para esquerda (←) - Oeste→Leste (DESATIVADO)


class EstadoSemaforo(Enum):
    """Enumeração dos estados possíveis do semáforo."""
    VERMELHO = auto()
    AMARELO = auto()
    VERDE = auto()


class TipoHeuristica(Enum):
    """Tipos de heurísticas disponíveis para controle de semáforos."""
    TEMPO_FIXO = auto()
    ADAPTATIVA_SIMPLES = auto()
    ADAPTATIVA_DENSIDADE = auto()
    WAVE_GREEN = auto()
    MANUAL = auto()


class TipoVeiculo(Enum):
    """Tipos de veículos da simulação."""
    CARRO = auto()
    ONIBUS = auto()
    CAMINHAO = auto()
    MOTO = auto()


@dataclass
class Configuracao:
    """Configuração para a simulação com vias de mão única."""
    # Tela
    LARGURA_TELA: int = 1400
    ALTURA_TELA: int = 900
    FPS: int = 60

    # Grade
    LINHAS_GRADE: int = 2
    COLUNAS_GRADE: int = 2
    ESPACAMENTO_ENTRE_CRUZAMENTOS: int = 200

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

    # Cores veículos (fallback / aleatórias para tipos não mapeados)
    CORES_VEICULO: List[tuple[int, int, int]] = field(default_factory=lambda: [
        (220, 50, 50), (50, 100, 200), (50, 180, 50), (255, 140, 0),
        (148, 0, 211), (255, 215, 0), (0, 191, 255), (255, 20, 147)
    ])

    # ----------------------------
    # Larguras / faixas da via
    # ----------------------------
    NUM_FAIXAS: int = 2                  # nº de faixas por via (mesmo valor p/ N e L)
    LARGURA_FAIXA: int = 26              # px de cada faixa (>= largura do veículo)
    LARGURA_RUA: int = 40                # será recalculado no __post_init__

    # =======================
    # Efeito "Caos" nas ruas
    # =======================
    CHAOS_ATIVO: bool = True
    CHAOS_TAMANHO_SEGMENTO: int = 160
    CHAOS_FATOR_MIN: float = 0.6
    CHAOS_FATOR_MAX: float = 1.2
    CHAOS_PROB_MUTACAO: float = 0.002
    CHAOS_MOSTRAR: bool = False

    # Direções ativas
    DIRECOES_PERMITIDAS: List[Direcao] = field(default_factory=lambda: [
        Direcao.NORTE, Direcao.LESTE
    ])

    # Spawn
    PONTOS_SPAWN: Dict[str, bool] = field(default_factory=lambda: {
        'NORTE': True, 'SUL': False, 'LESTE': True, 'OESTE': False
    })

    # ===== Parâmetros globais legado (fallback) =====
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

    # ---------
    # VIRADAS (Item 1)
    # ---------
    HABILITAR_VIRADAS: bool = True
    PROB_VIRAR_NORTE_PARA_LESTE: float = 0.25
    PROB_VIRAR_LESTE_PARA_NORTE: float = 0.25
    ESQUERDA_NORTE_PROTEGIDA: bool = True
    RAIO_CURVA: int = 28
    ZONA_DECISAO_VIRADA: int = 80
    MOSTRAR_TRAJETORIA_VIRADA: bool = False

    # ---------
    # TROCA DE FAIXA (Item 2)
    # ---------
    TROCA_FAIXA_ATIVA: bool = True
    PROB_TENTAR_TROCAR: float = 0.03
    VANTAGEM_MINIMA: float = 0.25
    GAP_FRENTE_TROCA: float = 55.0
    GAP_TRAS_TROCA: float = 35.0
    DURACAO_TROCA_FRAMES: int = 45

    # Semáforo
    TAMANHO_SEMAFORO: int = 12
    ESPACAMENTO_SEMAFORO: int = 4
    TEMPO_SEMAFORO_PADRAO: Dict[EstadoSemaforo, int] = field(default_factory=lambda: {
        EstadoSemaforo.VERDE: 180, EstadoSemaforo.AMARELO: 60, EstadoSemaforo.VERMELHO: 240
    })

    # Heurística
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

    # Visual
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

    # Posição
    MARGEM_TELA: int = 100

    # =============== TIPOS DE VEÍCULO (Item 3) ===============
    TIPOS_ATIVOS: List[TipoVeiculo] = field(default_factory=lambda: [
        TipoVeiculo.CARRO, TipoVeiculo.MOTO, TipoVeiculo.ONIBUS, TipoVeiculo.CAMINHAO
    ])

    # Distribuição de spawn (soma ≈ 1.0)
    DISTRIBUICAO_TIPOS: Dict[TipoVeiculo, float] = field(
        default_factory=lambda: {
            TipoVeiculo.CARRO: 0.60,
            TipoVeiculo.MOTO: 0.15,
            TipoVeiculo.ONIBUS: 0.10,
            TipoVeiculo.CAMINHAO: 0.15,
        }
    )

    # Parâmetros físicos/operacionais por tipo
    # Notas:
    # - 'largura' deve caber em LARGURA_FAIXA (26px)
    # - 'comprimento' é o eixo longitudinal
    PARAMS_TIPO_VEICULO: Dict[TipoVeiculo, Dict[str, float]] = field(
        default_factory=lambda: {
            TipoVeiculo.CARRO: {
                'largura': 22, 'comprimento': 35,
                'vel_min': 0.0, 'vel_base': 0.60, 'vel_max': 1.00,
                'acel': 0.18, 'desac': 0.25, 'desac_emer': 0.50,
                'dist_min': 45, 'dist_seg': 40, 'dist_reacao': 80,
            },
            TipoVeiculo.MOTO: {
                'largura': 16, 'comprimento': 24,
                'vel_min': 0.0, 'vel_base': 0.70, 'vel_max': 1.20,
                'acel': 0.22, 'desac': 0.30, 'desac_emer': 0.60,
                'dist_min': 30, 'dist_seg': 25, 'dist_reacao': 60,
            },
            TipoVeiculo.ONIBUS: {
                'largura': 24, 'comprimento': 65,
                'vel_min': 0.0, 'vel_base': 0.45, 'vel_max': 0.80,
                'acel': 0.10, 'desac': 0.20, 'desac_emer': 0.45,
                'dist_min': 60, 'dist_seg': 55, 'dist_reacao': 100,
            },
            TipoVeiculo.CAMINHAO: {
                'largura': 24, 'comprimento': 70,
                'vel_min': 0.0, 'vel_base': 0.50, 'vel_max': 0.85,
                'acel': 0.12, 'desac': 0.22, 'desac_emer': 0.48,
                'dist_min': 55, 'dist_seg': 50, 'dist_reacao': 95,
            },
        }
    )

    # Cores por tipo (opcional, para visual rápido do mix)
    CORES_TIPO: Dict[TipoVeiculo, Tuple[int, int, int]] = field(
        default_factory=lambda: {
            TipoVeiculo.CARRO: (50, 100, 200),      # azul
            TipoVeiculo.MOTO: (255, 215, 0),        # dourado
            TipoVeiculo.ONIBUS: (220, 50, 50),      # vermelho
            TipoVeiculo.CAMINHAO: (50, 180, 50),    # verde
        }
    )

    def __post_init__(self):
        # Ajusta a largura total da via para caber as faixas
        self.LARGURA_RUA = max(self.LARGURA_RUA, self.NUM_FAIXAS * self.LARGURA_FAIXA)

    @property
    def POSICAO_INICIAL_X(self) -> int:
        largura_total = (self.COLUNAS_GRADE - 1) * self.ESPACAMENTO_ENTRE_CRUZAMENTOS
        return (self.LARGURA_TELA - largura_total) // 2

    @property
    def POSICAO_INICIAL_Y(self) -> int:
        altura_total = (self.LINHAS_GRADE - 1) * self.ESPACAMENTO_ENTRE_CRUZAMENTOS
        return (self.ALTURA_TELA - altura_total) // 2 + 50


# Instância singleton
CONFIG = Configuracao()
