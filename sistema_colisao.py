"""
Sistema de detecção e prevenção de colisões para veículos.
"""
import pygame
from typing import List, Tuple, Optional
from configuracao import CONFIG, Direcao
from utils import calcular_distancia_entre_veiculos, mesma_via, calcular_velocidade_segura


class SistemaColisao:
    """Gerencia a detecção e prevenção de colisões entre veículos."""
    
    def __init__(self, veiculo):
        """
        Inicializa o sistema de colisão para um veículo.
        
        Args:
            veiculo: Referência para o veículo
        """
        self.veiculo = veiculo
        self.veiculo_frente = None
        self.distancia_veiculo_frente = float('inf')
    
    def verificar_colisao_futura(self, todos_veiculos: List) -> bool:
        """
        Verifica se haverá colisão se o veículo continuar se movendo.
        
        Args:
            todos_veiculos: Lista de todos os veículos na simulação
            
        Returns:
            True se uma colisão é iminente
        """
        # Calcula posição futura
        from utils import calcular_posicao_futura
        posicao_futura = calcular_posicao_futura(
            self.veiculo.posicao, 
            self.veiculo.fisica.velocidade + CONFIG.DISTANCIA_MIN_VEICULO / 2,
            self.veiculo.direcao
        )
        
        # Cria retângulo futuro
        rect_futuro = self._criar_rect_futuro(posicao_futura)
        
        # Verifica colisão com outros veículos
        for outro in todos_veiculos:
            if outro.id == self.veiculo.id or not outro.ativo:
                continue
            
            # Só verifica veículos na mesma via
            if not mesma_via(self.veiculo.posicao, outro.posicao, self.veiculo.direcao):
                continue
            
            # Expande o retângulo do outro veículo para margem de segurança
            rect_outro_expandido = outro.rect.inflate(10, 10)
            
            if rect_futuro.colliderect(rect_outro_expandido):
                return True
        
        return False
    
    def _criar_rect_futuro(self, posicao_futura: Tuple[float, float]) -> pygame.Rect:
        """Cria retângulo de colisão para posição futura."""
        if self.veiculo.direcao == Direcao.NORTE:
            return pygame.Rect(
                posicao_futura[0] - self.veiculo.largura // 2,
                posicao_futura[1] - self.veiculo.altura // 2,
                self.veiculo.largura,
                self.veiculo.altura
            )
        else:  # Direcao.LESTE
            return pygame.Rect(
                posicao_futura[0] - self.veiculo.altura // 2,
                posicao_futura[1] - self.veiculo.largura // 2,
                self.veiculo.altura,
                self.veiculo.largura
            )
    
    def processar_todos_veiculos(self, todos_veiculos: List) -> None:
        """
        Processa interação com todos os veículos, não apenas os do cruzamento atual.
        
        Args:
            todos_veiculos: Lista de todos os veículos na simulação
        """
        veiculo_mais_proximo = None
        distancia_minima = float('inf')
        
        for outro in todos_veiculos:
            if outro.id == self.veiculo.id or not outro.ativo:
                continue
            
            # Verifica se estão na mesma via e direção
            if self.veiculo.direcao != outro.direcao or not mesma_via(self.veiculo.posicao, outro.posicao, self.veiculo.direcao):
                continue
            
            # Verifica se o outro está à frente
            if self.veiculo.direcao == Direcao.NORTE:
                if outro.posicao[1] > self.veiculo.posicao[1]:  # Outro está à frente (mais para baixo)
                    distancia = outro.posicao[1] - self.veiculo.posicao[1]
                    if distancia < distancia_minima:
                        distancia_minima = distancia
                        veiculo_mais_proximo = outro
            elif self.veiculo.direcao == Direcao.LESTE:
                if outro.posicao[0] > self.veiculo.posicao[0]:  # Outro está à frente (mais para direita)
                    distancia = outro.posicao[0] - self.veiculo.posicao[0]
                    if distancia < distancia_minima:
                        distancia_minima = distancia
                        veiculo_mais_proximo = outro
        
        # Processa o veículo mais próximo à frente
        if veiculo_mais_proximo:
            self.veiculo_frente = veiculo_mais_proximo
            self.distancia_veiculo_frente = distancia_minima
            self.processar_veiculo_frente(veiculo_mais_proximo)
        else:
            self.veiculo_frente = None
            self.distancia_veiculo_frente = float('inf')
            # Se não há veículo à frente e não está aguardando semáforo, acelera
            if not self.veiculo.aguardando_semaforo:
                self.veiculo.fisica.acelerar_normalmente()
    
    def processar_veiculo_frente(self, veiculo_frente) -> None:
        """
        Processa a reação a um veículo à frente.
        
        Args:
            veiculo_frente: Veículo detectado à frente
        """
        if not veiculo_frente:
            return
        
        distancia = self._calcular_distancia_para_veiculo(veiculo_frente)
        
        # Força parada se muito próximo
        if distancia < CONFIG.DISTANCIA_MIN_VEICULO:
            self.veiculo.fisica.parar_veiculo()
            return
        
        if distancia < CONFIG.DISTANCIA_REACAO:
            # Calcula velocidade segura baseada na distância
            velocidade_segura = calcular_velocidade_segura(distancia, veiculo_frente.fisica.velocidade)
            
            # Limita a velocidade segura pela velocidade máxima individual do veículo
            velocidade_segura = min(velocidade_segura, self.veiculo.velocidade_maxima_individual)
            
            if self.veiculo.fisica.velocidade > velocidade_segura:
                # Precisa frear
                if distancia < CONFIG.DISTANCIA_MIN_VEICULO * 1.5:
                    self.veiculo.fisica.desacelerar_emergencia()
                else:
                    self.veiculo.fisica.desacelerar_suavemente()
            elif self.veiculo.fisica.velocidade < velocidade_segura * 0.9:
                # Pode acelerar um pouco (respeitando velocidade individual)
                self.veiculo.fisica.definir_aceleracao(CONFIG.ACELERACAO_VEICULO * 0.3)
            else:
                # Manter velocidade
                self.veiculo.fisica.definir_aceleracao(0)
        else:
            # Distância segura, pode acelerar se não estiver aguardando semáforo
            if not self.veiculo.aguardando_semaforo:
                self.veiculo.fisica.acelerar_normalmente()
    
    def _calcular_distancia_para_veiculo(self, outro) -> float:
        """Calcula a distância até outro veículo."""
        return calcular_distancia_entre_veiculos(
            self.veiculo.posicao, 
            outro.posicao, 
            self.veiculo.direcao,
            (self.veiculo.largura, self.veiculo.altura),
            (outro.largura, outro.altura)
        )
    
    def obter_veiculo_frente(self):
        """Retorna o veículo à frente."""
        return self.veiculo_frente
    
    def obter_distancia_veiculo_frente(self) -> float:
        """Retorna a distância até o veículo à frente."""
        return self.distancia_veiculo_frente
