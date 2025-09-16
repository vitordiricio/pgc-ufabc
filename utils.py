"""
Módulo de utilitários comuns para a simulação de tráfego.
Contém funções auxiliares para cálculos e operações comuns.
"""
import math
from typing import Tuple, List
from configuracao import CONFIG, Direcao


def calcular_distancia_ate_ponto(posicao: Tuple[float, float], ponto: Tuple[float, float], direcao: Direcao) -> float:
    """
    Calcula a distância até um ponto específico considerando a direção do movimento.
    
    Args:
        posicao: Posição atual (x, y)
        ponto: Ponto de destino (x, y)
        direcao: Direção do movimento
        
    Returns:
        Distância até o ponto
    """
    if direcao == Direcao.NORTE:
        # Norte→Sul: distância é diferença em Y (positiva)
        return max(0, ponto[1] - posicao[1])
    elif direcao == Direcao.LESTE:
        # Leste→Oeste: distância é diferença em X (positiva)
        return max(0, ponto[0] - posicao[0])
    return float('inf')


def passou_da_linha(posicao: Tuple[float, float], ponto: Tuple[float, float], direcao: Direcao) -> bool:
    """
    Verifica se já passou de um ponto considerando a direção do movimento.
    
    Args:
        posicao: Posição atual (x, y)
        ponto: Ponto de referência (x, y)
        direcao: Direção do movimento
        
    Returns:
        True se passou do ponto
    """
    margem = 10
    if direcao == Direcao.NORTE:
        # Norte→Sul: passou se Y atual > Y do ponto
        return posicao[1] > ponto[1] + margem
    elif direcao == Direcao.LESTE:
        # Leste→Oeste: passou se X atual > X do ponto
        return posicao[0] > ponto[0] + margem
    return False


def calcular_distancia_entre_veiculos(pos1: Tuple[float, float], pos2: Tuple[float, float], 
                                    direcao: Direcao, dimensoes1: Tuple[float, float], 
                                    dimensoes2: Tuple[float, float]) -> float:
    """
    Calcula a distância entre dois veículos considerando suas dimensões.
    
    Args:
        pos1: Posição do primeiro veículo
        pos2: Posição do segundo veículo
        direcao: Direção do movimento
        dimensoes1: (largura, altura) do primeiro veículo
        dimensoes2: (largura, altura) do segundo veículo
        
    Returns:
        Distância entre os veículos
    """
    if direcao != Direcao.NORTE and direcao != Direcao.LESTE:
        return float('inf')
    
    # Calcula distância centro a centro
    dx = pos2[0] - pos1[0]
    dy = pos2[1] - pos1[1]
    
    # Ajusta pela direção e dimensões dos veículos
    if direcao == Direcao.NORTE:
        if dy > 0:  # Outro está à frente
            return max(0, dy - (dimensoes1[1] + dimensoes2[1]) / 2)
    elif direcao == Direcao.LESTE:
        if dx > 0:  # Outro está à frente
            return max(0, dx - (dimensoes1[0] + dimensoes2[0]) / 2)
    
    return float('inf')


def mesma_via(pos1: Tuple[float, float], pos2: Tuple[float, float], direcao: Direcao) -> bool:
    """
    Verifica se dois veículos estão na mesma via (considerando faixas).
    
    Args:
        pos1: Posição do primeiro veículo
        pos2: Posição do segundo veículo
        direcao: Direção do movimento
        
    Returns:
        True se estão na mesma via
    """
    # Tolerância baseada na largura da faixa, não da rua inteira
    tolerancia = CONFIG.LARGURA_FAIXA * 0.8
    
    if direcao == Direcao.NORTE:
        # Mesma via vertical - verifica se estão na mesma faixa
        return abs(pos1[0] - pos2[0]) < tolerancia
    elif direcao == Direcao.LESTE:
        # Mesma via horizontal - verifica se estão na mesma faixa
        return abs(pos1[1] - pos2[1]) < tolerancia
    
    return False


def calcular_velocidade_segura(distancia: float, velocidade_lider: float) -> float:
    """
    Calcula a velocidade segura baseada na distância e velocidade do veículo à frente.
    
    Args:
        distancia: Distância até o veículo à frente
        velocidade_lider: Velocidade do veículo à frente
        
    Returns:
        Velocidade segura recomendada
    """
    if distancia < CONFIG.DISTANCIA_MIN_VEICULO:
        return 0
    
    # Modelo de car-following simplificado
    tempo_reacao = 1.0  # 1 segundo
    distancia_segura = CONFIG.DISTANCIA_SEGURANCA + velocidade_lider * tempo_reacao
    
    if distancia < distancia_segura:
        fator = distancia / distancia_segura
        return velocidade_lider * fator
    
    # Retorna velocidade base como referência (será limitada pela velocidade individual)
    return CONFIG.VELOCIDADE_BASE


def calcular_desaceleracao_necessaria(velocidade_atual: float, distancia: float) -> float:
    """
    Calcula a desaceleração necessária para parar em uma distância específica.
    
    Args:
        velocidade_atual: Velocidade atual do veículo
        distancia: Distância disponível para parar
        
    Returns:
        Desaceleração necessária (valor negativo)
    """
    if velocidade_atual <= 0.1 or distancia <= 0:
        return 0
    
    # Cálculo de desaceleração necessária: v² = v₀² + 2*a*d
    desaceleracao_necessaria = (velocidade_atual ** 2) / (2 * distancia)
    return -min(desaceleracao_necessaria, CONFIG.DESACELERACAO_VEICULO)


def obter_direcao_movimento(direcao: Direcao) -> Tuple[float, float]:
    """
    Retorna o vetor de movimento baseado na direção.
    
    Args:
        direcao: Direção do movimento
        
    Returns:
        Tupla (dx, dy) representando o vetor de movimento
    """
    if direcao == Direcao.NORTE:
        return (0, 1)  # Movimento vertical (para baixo)
    elif direcao == Direcao.LESTE:
        return (1, 0)  # Movimento horizontal (para direita)
    else:
        return (0, 0)


def calcular_posicao_futura(posicao: Tuple[float, float], velocidade: float, direcao: Direcao) -> Tuple[float, float]:
    """
    Calcula a posição futura baseada na velocidade e direção.
    
    Args:
        posicao: Posição atual (x, y)
        velocidade: Velocidade atual
        direcao: Direção do movimento
        
    Returns:
        Posição futura (x, y)
    """
    dx, dy = obter_direcao_movimento(direcao)
    return (posicao[0] + dx * velocidade, posicao[1] + dy * velocidade)
