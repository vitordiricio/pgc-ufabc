"""
Sistema de métricas para veículos na simulação de tráfego.
"""
from typing import Dict


class SistemaMetricas:
    """Gerencia as métricas de desempenho de um veículo."""
    
    def __init__(self, veiculo):
        """
        Inicializa o sistema de métricas para um veículo.
        
        Args:
            veiculo: Referência para o veículo
        """
        self.veiculo = veiculo
        self.tempo_viagem = 0
        self.tempo_parado = 0
        self.paradas_totais = 0
        self.distancia_percorrida = 0.0
        self.parado = True
    
    def atualizar_metricas(self, dt: float) -> None:
        """
        Atualiza as métricas do veículo.
        
        Args:
            dt: Delta time
        """
        self.tempo_viagem += dt
        
        if self.veiculo.fisica.velocidade < 0.1:
            self.tempo_parado += dt
            if not self.parado:
                self.paradas_totais += 1
            self.parado = True
        else:
            self.parado = False
    
    def adicionar_distancia_percorrida(self, distancia: float) -> None:
        """
        Adiciona distância percorrida às métricas.
        
        Args:
            distancia: Distância percorrida
        """
        self.distancia_percorrida += distancia
    
    def obter_estatisticas(self) -> Dict[str, float]:
        """
        Retorna as estatísticas do veículo.
        
        Returns:
            Dicionário com as estatísticas
        """
        return {
            'tempo_viagem': self.tempo_viagem,
            'tempo_parado': self.tempo_parado,
            'paradas_totais': self.paradas_totais,
            'distancia_percorrida': self.distancia_percorrida,
            'parado': self.parado
        }
    
    def resetar_metricas(self) -> None:
        """Reseta todas as métricas do veículo."""
        self.tempo_viagem = 0
        self.tempo_parado = 0
        self.paradas_totais = 0
        self.distancia_percorrida = 0.0
        self.parado = True
