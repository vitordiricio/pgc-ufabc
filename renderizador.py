"""
Módulo de renderização para a simulação de malha viária urbana.
"""
import pygame
from configuracao import CONFIG
from cruzamento import MalhaViaria


class Renderizador:
    """Lida com a renderização da simulação."""
    
    def __init__(self):
        """Inicializa o renderizador com uma superfície de exibição."""
        self.tela = pygame.display.set_mode(
            (CONFIG.LARGURA_TELA, CONFIG.ALTURA_TELA)
        )
        pygame.display.set_caption("Simulação de Malha Viária Urbana")
        self.relogio = pygame.time.Clock()
        self.fontes = {
            'pequena': pygame.font.SysFont('Arial', 12),
            'media': pygame.font.SysFont('Arial', 16),
            'grande': pygame.font.SysFont('Arial', 24)
        }
    
    def renderizar(self, malha: MalhaViaria, info_adicional: dict = None) -> None:
        """
        Renderiza um quadro da simulação.
        
        Args:
            malha: A malha viária a ser renderizada
            info_adicional: Informações adicionais para exibir
        """
        # Preenche a tela com a cor de fundo
        self.tela.fill(CONFIG.PRETO)
        
        # Desenha a malha viária
        malha.desenhar(self.tela)
        
        # Desenha a interface do usuário
        self._desenhar_ui(malha, info_adicional)
        
        # Atualiza a exibição
        pygame.display.flip()
        
        # Limita a taxa de quadros
        self.relogio.tick(CONFIG.FPS)
    
    def _desenhar_ui(self, malha: MalhaViaria, info_adicional: dict = None) -> None:
        """
        Desenha elementos da interface do usuário.
        
        Args:
            malha: A malha viária sendo renderizada
            info_adicional: Informações adicionais para exibir
        """
        # Título
        superficie_titulo = self.fontes['grande'].render(
            "Simulação de Malha Viária Urbana", 
            True, 
            CONFIG.BRANCO
        )
        
        rect_titulo = superficie_titulo.get_rect(
            center=(CONFIG.LARGURA_TELA // 2, 20)
        )
        
        self.tela.blit(superficie_titulo, rect_titulo)
        
        # Informações adicionais
        if info_adicional:
            self._desenhar_info_adicional(info_adicional)
        
        # Desenha informações de controle sempre
        self._desenhar_controles()
    
    def _desenhar_info_adicional(self, info: dict) -> None:
        """
        Desenha informações adicionais na tela.
        
        Args:
            info: Dicionário com informações adicionais
        """
        y_pos = 50
        for chave, valor in info.items():
            texto = f"{chave}: {valor}"
            superficie = self.fontes['media'].render(texto, True, CONFIG.BRANCO)
            self.tela.blit(superficie, (CONFIG.LARGURA_TELA - 250, y_pos))
            y_pos += 25
    
    def _desenhar_controles(self) -> None:
        """Desenha as instruções de controle na tela."""
        controles = [
            "Controles:",
            "ESC - Sair",
            "ESPAÇO - Pausar/Continuar",
            "R - Reiniciar simulação",
            "+/- - Alterar velocidade da simulação"
        ]
        
        for i, texto in enumerate(controles):
            superficie = self.fontes['pequena'].render(texto, True, CONFIG.BRANCO)
            self.tela.blit(superficie, (10, CONFIG.ALTURA_TELA - 100 + i * 20))