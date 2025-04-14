"""
Configurações para a simulação de malha viária urbana com múltiplos cruzamentos.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from enum import Enum, auto


class Direcao(Enum):
    """Enumeração das direções possíveis."""
    NORTE = auto()  # De cima para baixo (↓)
    LESTE = auto()  # Da esquerda para direita (→)


class EstadoSemaforo(Enum):
    """Enumeração dos estados possíveis do semáforo."""
    VERMELHO = auto()
    AMARELO = auto()
    VERDE = auto()


@dataclass
class Configuracao:
    """Configuração para a simulação."""
    # Configurações de tela
    LARGURA_TELA: int = 1200
    ALTURA_TELA: int = 800
    FPS: int = 60
    
    # Configurações da grade de cruzamentos
    LINHAS_GRADE: int = 2
    COLUNAS_GRADE: int = 2
    ESPACAMENTO_ENTRE_CRUZAMENTOS: int = 300
    
    # Cores
    PRETO: tuple[int, int, int] = (0, 0, 0)
    BRANCO: tuple[int, int, int] = (255, 255, 255)
    VERMELHO: tuple[int, int, int] = (255, 0, 0)
    AMARELO: tuple[int, int, int] = (255, 255, 0)
    VERDE: tuple[int, int, int] = (0, 255, 0)
    AZUL: tuple[int, int, int] = (0, 0, 255)
    CINZA: tuple[int, int, int] = (200, 200, 200)
    
    # Cores de veículos
    CORES_VEICULO: List[tuple[int, int, int]] = field(default_factory=lambda: [
        (255, 0, 0),    # Vermelho
        (0, 0, 255),    # Azul
        (0, 255, 0),    # Verde
        (255, 165, 0),  # Laranja
        (128, 0, 128)   # Roxo
    ])
    
    # Configurações da rua
    LARGURA_RUA: int = 50
    
    # Pontos de spawn de veículos (margens superior e esquerda)
    PONTOS_SPAWN: Dict[str, bool] = field(default_factory=lambda: {
        'TOPO': True,      # Spawnar veículos no topo (direção NORTE)
        'ESQUERDA': True,  # Spawnar veículos à esquerda (direção LESTE)
    })
    
    # Configurações de veículos
    LARGURA_VEICULO: int = 30
    ALTURA_VEICULO: int = 20
    TAXA_GERACAO_VEICULO: float = 0.02  # Probabilidade por frame
    VELOCIDADE_VEICULO: int = 2
    ACELERACAO_VEICULO: float = 0.1
    DESACELERACAO_VEICULO: float = 0.4
    VELOCIDADE_MAX_VEICULO: int = 3
    DISTANCIA_MIN_VEICULO: int = 40
    
    # Configurações de semáforo
    TAMANHO_SEMAFORO: int = 15
    ESPACAMENTO_SEMAFORO: int = 5
    DESLOCAMENTO_SEMAFORO: int = 20
    
    # Tempos de semáforo (em frames)
    TEMPO_SEMAFORO: Dict[EstadoSemaforo, int] = field(default_factory=lambda: {
        EstadoSemaforo.VERDE: 180,   # 3 segundos a 60 FPS
        EstadoSemaforo.AMARELO: 60,  # 1 segundo a 60 FPS
        EstadoSemaforo.VERMELHO: 180 # 3 segundos a 60 FPS
    })
    
    # Distância de detecção do semáforo
    DISTANCIA_DETECCAO_SEMAFORO: int = 150
    
    # Mapa de cores para estados de semáforo
    CORES_SEMAFORO: Dict[EstadoSemaforo, tuple[int, int, int]] = field(default_factory=lambda: {
        EstadoSemaforo.VERMELHO: (255, 0, 0),
        EstadoSemaforo.AMARELO: (255, 255, 0),
        EstadoSemaforo.VERDE: (0, 255, 0)
    })
    
    # Configurações de debug
    MODO_DEBUG: bool = False  # Alterado para False como padrão
    
    # Posição inicial da malha (centralizada)
    POSICAO_INICIAL_X: int = 300
    POSICAO_INICIAL_Y: int = 200


# Instância singleton
CONFIG = Configuracao()