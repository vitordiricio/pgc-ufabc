"""
Sistema de renderização para veículos na simulação de tráfego.
"""
import pygame
from typing import Tuple
from configuracao import CONFIG, Direcao


class RenderizadorVeiculo:
    """Gerencia a renderização visual de um veículo."""
    
    def __init__(self, veiculo):
        """
        Inicializa o renderizador para um veículo.
        
        Args:
            veiculo: Referência para o veículo
        """
        self.veiculo = veiculo
    
    def desenhar(self, tela: pygame.Surface) -> None:
        """Desenha o veículo na tela com visual aprimorado."""
        # Cria superfície para o veículo
        if self.veiculo.direcao == Direcao.NORTE:
            superficie = pygame.Surface((self.veiculo.largura, self.veiculo.altura), pygame.SRCALPHA)
        else:  # Direcao.LESTE
            superficie = pygame.Surface((self.veiculo.altura, self.veiculo.largura), pygame.SRCALPHA)
        
        # Desenha o corpo do veículo
        pygame.draw.rect(superficie, self.veiculo.cor, superficie.get_rect(), border_radius=4)
        
        # Adiciona detalhes (janelas)
        self._desenhar_janelas(superficie)
        
        # Adiciona luzes de freio se estiver freando
        if self.veiculo.fisica.aceleracao_atual < -0.1:
            self._desenhar_luzes_freio(superficie)
        
        # Adiciona faróis
        self._desenhar_farois(superficie)
        
        # Desenha na tela
        rect = superficie.get_rect(center=(int(self.veiculo.posicao[0]), int(self.veiculo.posicao[1])))
        tela.blit(superficie, rect)
        
        # Debug info
        if CONFIG.MOSTRAR_INFO_VEICULO:
            self._desenhar_info_debug(tela)
    
    def _desenhar_janelas(self, superficie: pygame.Surface) -> None:
        """Desenha as janelas do veículo."""
        cor_janela = (200, 220, 255, 180)
        
        if self.veiculo.direcao == Direcao.NORTE:
            # Janela frontal (parte de baixo - direção do movimento)
            pygame.draw.rect(superficie, cor_janela, 
                           (3, self.veiculo.altura * 0.7, self.veiculo.largura - 6, self.veiculo.altura * 0.25), 
                           border_radius=2)
            # Janela traseira (parte de cima)
            pygame.draw.rect(superficie, cor_janela, 
                           (3, 3, self.veiculo.largura - 6, self.veiculo.altura * 0.3), 
                           border_radius=2)
        else:  # Direcao.LESTE
            # Janela frontal (parte direita - direção do movimento)
            pygame.draw.rect(superficie, cor_janela, 
                           (self.veiculo.altura * 0.7, 3, self.veiculo.altura * 0.25, self.veiculo.largura - 6), 
                           border_radius=2)
            # Janela traseira (parte esquerda)
            pygame.draw.rect(superficie, cor_janela, 
                           (3, 3, self.veiculo.altura * 0.3, self.veiculo.largura - 6), 
                           border_radius=2)
    
    def _desenhar_luzes_freio(self, superficie: pygame.Surface) -> None:
        """Desenha as luzes de freio do veículo."""
        cor_freio = (255, 100, 100)
        
        if self.veiculo.direcao == Direcao.NORTE:
            # Luzes na parte de cima (traseira)
            pygame.draw.rect(superficie, cor_freio, (2, 1, 6, 3))
            pygame.draw.rect(superficie, cor_freio, (self.veiculo.largura - 8, 1, 6, 3))
        elif self.veiculo.direcao == Direcao.LESTE:
            # Luzes na parte esquerda (traseira)
            pygame.draw.rect(superficie, cor_freio, (1, 2, 3, 6))
            pygame.draw.rect(superficie, cor_freio, (1, self.veiculo.largura - 8, 3, 6))
    
    def _desenhar_farois(self, superficie: pygame.Surface) -> None:
        """Desenha os faróis do veículo."""
        cor_farol = (255, 255, 200, 150)
        
        if self.veiculo.direcao == Direcao.NORTE:
            # Faróis na frente (parte de baixo)
            pygame.draw.circle(superficie, cor_farol, (8, self.veiculo.altura - 5), 3)
            pygame.draw.circle(superficie, cor_farol, (self.veiculo.largura - 8, self.veiculo.altura - 5), 3)
        elif self.veiculo.direcao == Direcao.LESTE:
            # Faróis na frente (parte direita)
            pygame.draw.circle(superficie, cor_farol, (self.veiculo.altura - 5, 8), 3)
            pygame.draw.circle(superficie, cor_farol, (self.veiculo.altura - 5, self.veiculo.largura - 8), 3)
    
    def _desenhar_info_debug(self, tela: pygame.Surface) -> None:
        """Desenha informações de debug do veículo."""
        fonte = pygame.font.SysFont('Arial', 10)
        
        # Adiciona indicador se está aguardando semáforo ou veículo
        aguardando = ""
        if self.veiculo.aguardando_semaforo:
            aguardando = "🔴"
        elif self.veiculo.colisao.veiculo_frente and self.veiculo.colisao.distancia_veiculo_frente < CONFIG.DISTANCIA_REACAO:
            aguardando = "🚗"
        
        texto = f"V:{self.veiculo.fisica.velocidade:.1f} ID:{self.veiculo.id} {aguardando}"
        superficie_texto = fonte.render(texto, True, CONFIG.BRANCO)
        tela.blit(superficie_texto, (self.veiculo.posicao[0] - 20, self.veiculo.posicao[1] - 25))
