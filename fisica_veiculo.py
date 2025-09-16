"""
Módulo de física de veículos para a simulação de tráfego.
Contém a lógica de movimento, aceleração e física dos veículos.
Otimizado com numpy para melhor performance.
"""
import math
import numpy as np
from typing import Tuple, List, Optional
from configuracao import CONFIG, Direcao
from utils import calcular_desaceleracao_necessaria, obter_direcao_movimento, calcular_posicao_futura


class FisicaVeiculo:
    """Gerencia a física e movimento de um veículo."""
    
    def __init__(self, veiculo):
        """
        Inicializa a física do veículo.
        
        Args:
            veiculo: Referência para o veículo
        """
        self.veiculo = veiculo
        self.velocidade = 0.0
        self.velocidade_desejada = veiculo.velocidade_maxima_individual
        self.aceleracao_atual = 0.0
        self.em_desaceleracao = False
    
    def aplicar_aceleracao(self, dt: float) -> None:
        """
        Aplica aceleração ao veículo.
        
        Args:
            dt: Delta time para cálculos de física
        """
        self.velocidade += self.aceleracao_atual * dt
    
    def aplicar_limite_velocidade(self, fator_caos: float = 1.0) -> None:
        """
        Aplica limites de velocidade considerando fator de caos local e velocidade individual.
        
        Args:
            fator_caos: Fator de caos local (multiplicador de velocidade máxima)
        """
        # Limite global da via (considerando caos)
        vmax_global = CONFIG.VELOCIDADE_MAX_GLOBAL * fator_caos
        
        # Limite individual do veículo
        vmax_individual = self.veiculo.velocidade_maxima_individual * fator_caos
        
        # Usa o menor entre os dois limites
        vmax_efetiva = min(vmax_global, vmax_individual)
        
        self.velocidade = max(CONFIG.VELOCIDADE_MIN_VEICULO, min(vmax_efetiva, self.velocidade))
    
    def mover_veiculo(self, dt: float) -> Tuple[float, float]:
        """
        Move o veículo baseado na velocidade atual.
        Otimizado com numpy para melhor performance.
        
        Args:
            dt: Delta time
            
        Returns:
            Tupla (dx, dy) representando o movimento aplicado
        """
        # Usa numpy para cálculos vetoriais mais eficientes
        direcao_vec = np.array(obter_direcao_movimento(self.veiculo.direcao))
        movimento = direcao_vec * self.velocidade
        
        # Atualiza posição usando numpy
        pos_atual = np.array(self.veiculo.posicao)
        nova_pos = pos_atual + movimento
        
        # Atualiza posição do veículo
        self.veiculo.posicao[0] = nova_pos[0]
        self.veiculo.posicao[1] = nova_pos[1]
        
        # Calcula distância percorrida usando norma euclidiana
        distancia = np.linalg.norm(movimento)
        self.veiculo.metricas.adicionar_distancia_percorrida(distancia)
        
        return tuple(movimento)
    
    def aplicar_frenagem_para_parada(self, distancia: float) -> None:
        """
        Aplica frenagem suave para parar em uma distância específica.
        
        Args:
            distancia: Distância disponível para parar
        """
        if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO:
            # Muito próximo, frenagem de emergência
            self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
            self.velocidade_desejada = 0
            # Força parada completa se muito próximo
            if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO / 2:
                self.velocidade = 0.0
        else:
            # Cálculo de desaceleração necessária
            if self.velocidade > 0.1:
                self.aceleracao_atual = calcular_desaceleracao_necessaria(self.velocidade, distancia)
            else:
                self.aceleracao_atual = 0
    
    def parar_veiculo(self) -> None:
        """Para o veículo imediatamente."""
        self.velocidade = 0.0
        self.aceleracao_atual = 0.0
    
    def acelerar_normalmente(self) -> None:
        """Aplica aceleração normal do veículo até sua velocidade máxima individual."""
        # Só acelera se ainda não atingiu sua velocidade máxima individual
        if self.velocidade < self.veiculo.velocidade_maxima_individual:
            self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
        else:
            self.aceleracao_atual = 0
    
    def desacelerar_suavemente(self) -> None:
        """Aplica desaceleração suave."""
        self.aceleracao_atual = -CONFIG.DESACELERACAO_VEICULO
    
    def desacelerar_emergencia(self) -> None:
        """Aplica desaceleração de emergência."""
        self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
    
    def ajustar_velocidade_segura(self, distancia: float, velocidade_lider: float) -> None:
        """
        Ajusta a velocidade para manter distância segura.
        
        Args:
            distancia: Distância até o veículo à frente
            velocidade_lider: Velocidade do veículo à frente
        """
        from utils import calcular_velocidade_segura
        
        if distancia < CONFIG.DISTANCIA_MIN_VEICULO:
            self.parar_veiculo()
            return
        
        velocidade_segura = calcular_velocidade_segura(distancia, velocidade_lider)
        
        if self.velocidade > velocidade_segura:
            # Precisa frear
            if distancia < CONFIG.DISTANCIA_MIN_VEICULO * 1.5:
                self.desacelerar_emergencia()
            else:
                self.desacelerar_suavemente()
        elif self.velocidade < velocidade_segura * 0.9:
            # Pode acelerar um pouco
            self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO * 0.3
        else:
            # Manter velocidade
            self.aceleracao_atual = 0
    
    def verificar_saida_tela(self) -> bool:
        """
        Verifica se o veículo saiu da tela.
        
        Returns:
            True se saiu da tela
        """
        margem = 100
        return (self.veiculo.posicao[0] < -margem or
                self.veiculo.posicao[0] > CONFIG.LARGURA_TELA + margem or
                self.veiculo.posicao[1] < -margem or
                self.veiculo.posicao[1] > CONFIG.ALTURA_TELA + margem)
    
    def obter_velocidade_atual(self) -> float:
        """Retorna a velocidade atual do veículo."""
        return self.velocidade
    
    def obter_aceleracao_atual(self) -> float:
        """Retorna a aceleração atual do veículo."""
        return self.aceleracao_atual
    
    def definir_velocidade(self, velocidade: float) -> None:
        """Define a velocidade do veículo."""
        self.velocidade = velocidade
    
    def definir_aceleracao(self, aceleracao: float) -> None:
        """Define a aceleração do veículo."""
        self.aceleracao_atual = aceleracao
