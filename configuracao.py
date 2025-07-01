"""
Configurações para a simulação de malha viária urbana com múltiplos cruzamentos.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from enum import Enum, auto


class Direcao(Enum):
    """Enumeração das direções possíveis."""
    NORTE = auto()  # De cima para baixo (↓)
    SUL = auto()    # De baixo para cima (↑)
    LESTE = auto()  # Da esquerda para direita (→)
    OESTE = auto()  # Da direita para esquerda (←)


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
    """Configuração para a simulação."""
    # Configurações de tela
    LARGURA_TELA: int = 1400
    ALTURA_TELA: int = 900
    FPS: int = 60
    
    # Configurações da grade de cruzamentos
    LINHAS_GRADE: int = 2
    COLUNAS_GRADE: int = 2
    ESPACAMENTO_ENTRE_CRUZAMENTOS: int = 500
    
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
    
    # Configurações da rua
    LARGURA_RUA: int = 60
    LARGURA_FAIXA: int = 30
    
    # Pontos de spawn de veículos
    PONTOS_SPAWN: Dict[str, bool] = field(default_factory=lambda: {
        'NORTE': True,
        'SUL': True,
        'LESTE': True,
        'OESTE': True
    })
    
    # Configurações de veículos
    LARGURA_VEICULO: int = 25
    ALTURA_VEICULO: int = 35
    TAXA_GERACAO_VEICULO: float = 0.015
    VELOCIDADE_VEICULO: float = 1.0
    VELOCIDADE_MAX_VEICULO: float = 2.0
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