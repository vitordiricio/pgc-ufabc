"""
Módulo de utilitários comuns para a simulação de tráfego.
Contém funções auxiliares para cálculos e operações comuns.
Otimizado com numpy para melhor performance.
"""
import math
import numpy as np
from typing import Tuple, List
from configuracao import CONFIG, Direcao


def calcular_distancia_ate_ponto(posicao: Tuple[float, float], ponto: Tuple[float, float], direcao: Direcao) -> float:
    """
    Calcula a distância até um ponto específico considerando a direção do movimento.
    Otimizado com numpy para melhor performance.
    
    Args:
        posicao: Posição atual (x, y)
        ponto: Ponto de destino (x, y)
        direcao: Direção do movimento
        
    Returns:
        Distância até o ponto
    """
    pos = np.array(posicao)
    dest = np.array(ponto)
    
    if direcao == Direcao.NORTE:
        # Norte→Sul: distância é diferença em Y (positiva)
        return max(0.0, dest[1] - pos[1])
    elif direcao == Direcao.LESTE:
        # Leste→Oeste: distância é diferença em X (positiva)
        return max(0.0, dest[0] - pos[0])
    return float('inf')


def passou_da_linha(posicao: Tuple[float, float], ponto: Tuple[float, float], direcao: Direcao) -> bool:
    """
    Verifica se já passou de um ponto considerando a direção do movimento.
    Otimizado com numpy para melhor performance.
    
    Args:
        posicao: Posição atual (x, y)
        ponto: Ponto de referência (x, y)
        direcao: Direção do movimento
        
    Returns:
        True se passou do ponto
    """
    margem = 10.0
    pos = np.array(posicao)
    ref = np.array(ponto)
    
    if direcao == Direcao.NORTE:
        # Norte→Sul: passou se Y atual > Y do ponto
        return pos[1] > ref[1] + margem
    elif direcao == Direcao.LESTE:
        # Leste→Oeste: passou se X atual > X do ponto
        return pos[0] > ref[0] + margem
    return False


def calcular_distancia_entre_veiculos(pos1: Tuple[float, float], pos2: Tuple[float, float], 
                                    direcao: Direcao, dimensoes1: Tuple[float, float], 
                                    dimensoes2: Tuple[float, float]) -> float:
    """
    Calcula a distância entre dois veículos considerando suas dimensões.
    Otimizado com numpy para melhor performance.
    
    Args:
        pos1: Posição do primeiro veículo
        pos2: Posição do segundo veículo
        direcao: Direção do movimento
        dimensoes1: (largura, altura) do primeiro veículo
        dimensoes2: (largura, altura) do segundo veículo
        
    Returns:
        Distância entre os veículos
    """
    if direcao not in (Direcao.NORTE, Direcao.LESTE):
        return float('inf')
    
    # Usa numpy para cálculos vetoriais mais eficientes
    pos1_arr = np.array(pos1)
    pos2_arr = np.array(pos2)
    diff = pos2_arr - pos1_arr
    
    # Ajusta pela direção e dimensões dos veículos
    if direcao == Direcao.NORTE:
        if diff[1] > 0:  # Outro está à frente
            return max(0.0, diff[1] - (dimensoes1[1] + dimensoes2[1]) / 2)
    elif direcao == Direcao.LESTE:
        if diff[0] > 0:  # Outro está à frente
            return max(0.0, diff[0] - (dimensoes1[0] + dimensoes2[0]) / 2)
    
    return float('inf')


def mesma_via(pos1: Tuple[float, float], pos2: Tuple[float, float], direcao: Direcao) -> bool:
    """
    Verifica se dois veículos estão na mesma via (considerando faixas).
    Otimizado com numpy para melhor performance.
    
    Args:
        pos1: Posição do primeiro veículo
        pos2: Posição do segundo veículo
        direcao: Direção do movimento
        
    Returns:
        True se estão na mesma via
    """
    # Tolerância baseada na largura da faixa, não da rua inteira
    tolerancia = CONFIG.LARGURA_FAIXA * 0.8
    
    pos1_arr = np.array(pos1)
    pos2_arr = np.array(pos2)
    diff = np.abs(pos2_arr - pos1_arr)
    
    if direcao == Direcao.NORTE:
        # Mesma via vertical - verifica se estão na mesma faixa
        return diff[0] < tolerancia
    elif direcao == Direcao.LESTE:
        # Mesma via horizontal - verifica se estão na mesma faixa
        return diff[1] < tolerancia
    
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
    Otimizado com numpy para melhor performance.
    
    Args:
        direcao: Direção do movimento
        
    Returns:
        Tupla (dx, dy) representando o vetor de movimento
    """
    if direcao == Direcao.NORTE:
        return (0.0, 1.0)  # Movimento vertical (para baixo)
    elif direcao == Direcao.LESTE:
        return (1.0, 0.0)  # Movimento horizontal (para direita)
    else:
        return (0.0, 0.0)


def calcular_posicao_futura(posicao: Tuple[float, float], velocidade: float, direcao: Direcao) -> Tuple[float, float]:
    """
    Calcula a posição futura baseada na velocidade e direção.
    Otimizado com numpy para melhor performance.
    
    Args:
        posicao: Posição atual (x, y)
        velocidade: Velocidade atual
        direcao: Direção do movimento
        
    Returns:
        Posição futura (x, y)
    """
    pos = np.array(posicao)
    direcao_vec = np.array(obter_direcao_movimento(direcao))
    return tuple(pos + direcao_vec * velocidade)


# ==========================================
# FUNÇÕES OTIMIZADAS PARA PROCESSAMENTO EM LOTE
# ==========================================

def calcular_distancias_entre_veiculos_batch(posicoes: np.ndarray, direcoes: np.ndarray, 
                                            dimensoes: np.ndarray, tolerancia: float) -> np.ndarray:
    """
    Calcula distâncias entre veículos em lote usando numpy.
    Muito mais eficiente que loops aninhados.
    
    Args:
        posicoes: Array (N, 2) com posições dos veículos
        direcoes: Array (N,) com direções dos veículos
        dimensoes: Array (N, 2) com dimensões dos veículos
        tolerancia: Tolerância para considerar mesma via
        
    Returns:
        Array (N, N) com distâncias entre veículos
    """
    n = len(posicoes)
    if n == 0:
        return np.array([])
    
    # Cria matriz de distâncias
    distancias = np.full((n, n), np.inf)
    
    # Para cada direção, calcula distâncias apenas entre veículos da mesma direção
    for direcao in [Direcao.NORTE, Direcao.LESTE]:
        mask = direcoes == direcao
        indices = np.where(mask)[0]
        
        if len(indices) < 2:
            continue
            
        # Pega posições e dimensões dos veículos desta direção
        pos_dir = posicoes[indices]
        dim_dir = dimensoes[indices]
        
        # Calcula diferenças entre posições
        if direcao == Direcao.NORTE:
            # Distância vertical (Y)
            diff_y = pos_dir[:, 1:2] - pos_dir[:, 1:2].T
            # Só considera veículos à frente (diff_y > 0)
            mask_frente = diff_y > 0
            dist_y = diff_y - (dim_dir[:, 1:2] + dim_dir[:, 1:2].T) / 2
            dist_y = np.where(mask_frente, np.maximum(0, dist_y), np.inf)
            distancias[np.ix_(indices, indices)] = dist_y
            
        elif direcao == Direcao.LESTE:
            # Distância horizontal (X)
            diff_x = pos_dir[:, 0:1] - pos_dir[:, 0:1].T
            # Só considera veículos à frente (diff_x > 0)
            mask_frente = diff_x > 0
            dist_x = diff_x - (dim_dir[:, 0:1] + dim_dir[:, 0:1].T) / 2
            dist_x = np.where(mask_frente, np.maximum(0, dist_x), np.inf)
            distancias[np.ix_(indices, indices)] = dist_x
    
    return distancias


def encontrar_veiculos_frente_batch(posicoes: np.ndarray, direcoes: np.ndarray, 
                                   tolerancia: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Encontra veículos à frente para cada veículo usando processamento em lote.
    
    Args:
        posicoes: Array (N, 2) com posições dos veículos
        direcoes: Array (N,) com direções dos veículos
        tolerancia: Tolerância para considerar mesma via
        
    Returns:
        Tuple com (indices_veiculos_frente, distancias)
    """
    n = len(posicoes)
    if n == 0:
        return np.array([]), np.array([])
    
    indices_frente = np.full(n, -1, dtype=int)
    distancias_frente = np.full(n, np.inf)
    
    for direcao in [Direcao.NORTE, Direcao.LESTE]:
        mask = direcoes == direcao
        indices = np.where(mask)[0]
        
        if len(indices) < 2:
            continue
            
        pos_dir = posicoes[indices]
        
        if direcao == Direcao.NORTE:
            # Para cada veículo, encontra o mais próximo à frente (Y maior)
            for i, idx_i in enumerate(indices):
                pos_i = pos_dir[i]
                # Veículos à frente têm Y maior
                mask_frente = pos_dir[:, 1] > pos_i[1]
                if not np.any(mask_frente):
                    continue
                    
                # Calcula distâncias apenas para veículos à frente
                distancias = pos_dir[mask_frente, 1] - pos_i[1]
                # Encontra o mais próximo
                idx_mais_proximo = np.argmin(distancias)
                indices_reais = indices[mask_frente]
                indices_frente[idx_i] = indices_reais[idx_mais_proximo]
                distancias_frente[idx_i] = distancias[idx_mais_proximo]
                
        elif direcao == Direcao.LESTE:
            # Para cada veículo, encontra o mais próximo à frente (X maior)
            for i, idx_i in enumerate(indices):
                pos_i = pos_dir[i]
                # Veículos à frente têm X maior
                mask_frente = pos_dir[:, 0] > pos_i[0]
                if not np.any(mask_frente):
                    continue
                    
                # Calcula distâncias apenas para veículos à frente
                distancias = pos_dir[mask_frente, 0] - pos_i[0]
                # Encontra o mais próximo
                idx_mais_proximo = np.argmin(distancias)
                indices_reais = indices[mask_frente]
                indices_frente[idx_i] = indices_reais[idx_mais_proximo]
                distancias_frente[idx_i] = distancias[idx_mais_proximo]
    
    return indices_frente, distancias_frente


def verificar_mesma_via_batch(posicoes: np.ndarray, direcoes: np.ndarray, 
                             tolerancia: float) -> np.ndarray:
    """
    Verifica quais veículos estão na mesma via usando processamento em lote.
    
    Args:
        posicoes: Array (N, 2) com posições dos veículos
        direcoes: Array (N,) com direções dos veículos
        tolerancia: Tolerância para considerar mesma via
        
    Returns:
        Array (N, N) booleano indicando se veículos estão na mesma via
    """
    n = len(posicoes)
    if n == 0:
        return np.array([])
    
    mesma_via = np.zeros((n, n), dtype=bool)
    
    for direcao in [Direcao.NORTE, Direcao.LESTE]:
        mask = direcoes == direcao
        indices = np.where(mask)[0]
        
        if len(indices) < 2:
            continue
            
        pos_dir = posicoes[indices]
        
        if direcao == Direcao.NORTE:
            # Mesma via se diferença em X for menor que tolerância
            diff_x = np.abs(pos_dir[:, 0:1] - pos_dir[:, 0:1].T)
            mesma_via[np.ix_(indices, indices)] = diff_x < tolerancia
            
        elif direcao == Direcao.LESTE:
            # Mesma via se diferença em Y for menor que tolerância
            diff_y = np.abs(pos_dir[:, 1:2] - pos_dir[:, 1:2].T)
            mesma_via[np.ix_(indices, indices)] = diff_y < tolerancia
    
    return mesma_via
