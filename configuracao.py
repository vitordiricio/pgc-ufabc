"""
Configurações para a simulação de malha viária urbana com múltiplos cruzamentos.
Sistema com vias de mão única: Horizontal (Leste→Oeste) e Vertical (Norte→Sul)
"""
from dataclasses import dataclass, field
from typing import Dict, List
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


@dataclass
class Configuracao:
    """Configuração para a simulação com vias de mão única."""
    # Configurações de tela
    LARGURA_TELA: int = 1400
    ALTURA_TELA: int = 900
    FPS: int = 60
    
    # Configurações da grade de cruzamentos
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
    
    # Cores de veículos
    CORES_VEICULO: List[tuple[int, int, int]] = field(default_factory=lambda: [
        (220, 50, 50),    # Vermelho
        (50, 100, 200),   # Azul
        (50, 180, 50),    # Verde
        (255, 140, 0),    # Laranja
        (148, 0, 211),    # Roxo
        (255, 215, 0),    # Dourado
        (0, 191, 255),    # Azul Claro
        (255, 20, 147)    # Rosa
    ])
    
    # Configurações da rua - AGORA MÃO ÚNICA
    LARGURA_RUA: int = 40  # Reduzida pois só tem uma direção
    LARGURA_FAIXA: int = 40  # Uma única faixa por direção

    # =======================
    # Efeito "Caos" nas ruas
    # =======================
    CHAOS_ATIVO: bool = True
    CHAOS_TAMANHO_SEGMENTO: int = 160    # px por trecho
    CHAOS_FATOR_MIN: float = 0.6         # reduz limite local
    CHAOS_FATOR_MAX: float = 1.2         # pode dar leve "boost"
    CHAOS_PROB_MUTACAO: float = 0.002    # prob. (por segmento/frame) de mudar o fator
    CHAOS_MOSTRAR: bool = False          # overlay visual dos trechos (debug)

    
    # Sistema de mão única: define quais direções são permitidas
    DIRECOES_PERMITIDAS: List[Direcao] = field(default_factory=lambda: [
        Direcao.NORTE,  # Vertical: Norte→Sul (de cima para baixo)
        Direcao.LESTE   # Horizontal: Leste→Oeste (da esquerda para direita)
    ])
    
    # Pontos de spawn de veículos - APENAS NAS BORDAS CORRETAS
    # Para mão única: Norte spawn no topo, Leste spawn na esquerda
    PONTOS_SPAWN: Dict[str, bool] = field(default_factory=lambda: {
        'NORTE': True,   # Spawn no topo (vai para baixo)
        'SUL': False,    # Desativado - mão única
        'LESTE': True,   # Spawn na esquerda (vai para direita)
        'OESTE': False   # Desativado - mão única
    })
    
    # Configurações de veículos
    LARGURA_VEICULO: int = 25
    ALTURA_VEICULO: int = 35
    TAXA_GERACAO_VEICULO: float = 0.01  # Aumentada um pouco já que temos menos pontos de spawn
    VELOCIDADE_VEICULO: float = 0.5
    VELOCIDADE_MAX_VEICULO: float = 1.0
    VELOCIDADE_MIN_VEICULO: float = 0.0
    ACELERACAO_VEICULO: float = 0.15
    DESACELERACAO_VEICULO: float = 0.25
    DESACELERACAO_EMERGENCIA: float = 0.5
    DISTANCIA_MIN_VEICULO: int = 50
    DISTANCIA_SEGURANCA: int = 40
    DISTANCIA_REACAO: int = 80
    
    # Configurações de semáforo
    TAMANHO_SEMAFORO: int = 12
    ESPACAMENTO_SEMAFORO: int = 4
    
    # Tempos de semáforo padrão (em frames)
    TEMPO_SEMAFORO_PADRAO: Dict[EstadoSemaforo, int] = field(default_factory=lambda: {
        EstadoSemaforo.VERDE: 180,    # 3 segundos
        EstadoSemaforo.AMARELO: 60,   # 1 segundo
        EstadoSemaforo.VERMELHO: 240  # 4 segundos
    })
    
    # Configurações de heurísticas
    HEURISTICA_ATIVA: TipoHeuristica = TipoHeuristica.ADAPTATIVA_DENSIDADE
    LIMIAR_DENSIDADE_BAIXA: int = 3
    LIMIAR_DENSIDADE_MEDIA: int = 6
    LIMIAR_DENSIDADE_ALTA: int = 10
    
    # Tempos adaptativos baseados em densidade
    TEMPO_VERDE_DENSIDADE_BAIXA: int = 120   # 2 segundos
    TEMPO_VERDE_DENSIDADE_MEDIA: int = 180   # 3 segundos
    TEMPO_VERDE_DENSIDADE_ALTA: int = 300    # 5 segundos
    
    # Configurações de detecção
    DISTANCIA_DETECCAO_SEMAFORO: int = 120
    DISTANCIA_PARADA_SEMAFORO: int = 15
    
    # Configurações visuais
    MOSTRAR_GRID: bool = True
    MOSTRAR_ESTATISTICAS: bool = True
    MOSTRAR_INFO_VEICULO: bool = False
    MOSTRAR_DIRECAO_FLUXO: bool = True  
    TAMANHO_FONTE_PEQUENA: int = 14
    TAMANHO_FONTE_MEDIA: int = 18
    TAMANHO_FONTE_GRANDE: int = 24
    
    # Métricas de desempenho
    COLETAR_METRICAS: bool = True
    INTERVALO_METRICAS: int = 300  # 5 segundos
    
    # Posição inicial da malha
    MARGEM_TELA: int = 100
    
    @property
    def POSICAO_INICIAL_X(self) -> int:
        """Calcula a posição X inicial dinamicamente."""
        largura_total = (self.COLUNAS_GRADE - 1) * self.ESPACAMENTO_ENTRE_CRUZAMENTOS
        return (self.LARGURA_TELA - largura_total) // 2
    
    @property
    def POSICAO_INICIAL_Y(self) -> int:
        """Calcula a posição Y inicial dinamicamente."""
        altura_total = (self.LINHAS_GRADE - 1) * self.ESPACAMENTO_ENTRE_CRUZAMENTOS
        return (self.ALTURA_TELA - altura_total) // 2 + 50


# Instância singleton
CONFIG = Configuracao()