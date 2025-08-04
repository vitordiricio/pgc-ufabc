"""
Módulo de renderização aprimorado para a simulação de malha viária urbana.
"""
import pygame
from typing import Dict, List, Tuple
from configuracao import CONFIG, TipoHeuristica
from cruzamento import MalhaViaria


class Renderizador:
    """Sistema de renderização com interface aprimorada."""
    
    def __init__(self):
        """Inicializa o renderizador."""
        self.tela = pygame.display.set_mode(
            (CONFIG.LARGURA_TELA, CONFIG.ALTURA_TELA)
        )
        pygame.display.set_caption("Simulação de Tráfego Urbano - PGC UFABC")
        pygame.display.set_icon(self._criar_icone())
        
        self.relogio = pygame.time.Clock()
        
        # Fontes
        self.fontes = {
            'pequena': pygame.font.SysFont('Arial', CONFIG.TAMANHO_FONTE_PEQUENA),
            'media': pygame.font.SysFont('Arial', CONFIG.TAMANHO_FONTE_MEDIA),
            'grande': pygame.font.SysFont('Arial', CONFIG.TAMANHO_FONTE_GRANDE),
            'titulo': pygame.font.SysFont('Arial', 28, bold=True)
        }
        
        # Superfícies para otimização
        self.superficie_fundo = self._criar_fundo()
        self.painel_info = None
        self.ultima_atualizacao_painel = 0
    
    def _criar_icone(self) -> pygame.Surface:
        """Cria um ícone para a janela."""
        icone = pygame.Surface((32, 32))
        icone.fill(CONFIG.PRETO)
        
        # Desenha um semáforo simplificado
        pygame.draw.rect(icone, CONFIG.CINZA, (12, 4, 8, 24))
        pygame.draw.circle(icone, CONFIG.VERMELHO, (16, 8), 3)
        pygame.draw.circle(icone, CONFIG.AMARELO, (16, 16), 3)
        pygame.draw.circle(icone, CONFIG.VERDE, (16, 24), 3)
        
        return icone
    
    def _criar_fundo(self) -> pygame.Surface:
        """Cria uma superfície de fundo com gradiente."""
        fundo = pygame.Surface((CONFIG.LARGURA_TELA, CONFIG.ALTURA_TELA))
        
        # Gradiente vertical
        for y in range(CONFIG.ALTURA_TELA):
            intensidade = int(20 + (40 * y / CONFIG.ALTURA_TELA))
            cor = (intensidade, intensidade, intensidade + 10)
            pygame.draw.line(fundo, cor, (0, y), (CONFIG.LARGURA_TELA, y))
        
        return fundo
    
    def renderizar(self, malha: MalhaViaria, info_simulacao: Dict = None) -> None:
        """
        Renderiza um quadro completo da simulação.
        
        Args:
            malha: A malha viária a ser renderizada
            info_simulacao: Informações adicionais da simulação
        """
        # Desenha o fundo
        self.tela.blit(self.superficie_fundo, (0, 0))
        
        # Desenha a malha viária
        malha.desenhar(self.tela)
        
        # Desenha painéis de informação
        self._desenhar_painel_superior(malha)
        self._desenhar_painel_lateral(malha, info_simulacao)
        self._desenhar_controles()
        
        # Atualiza a tela
        pygame.display.flip()
        self.relogio.tick(CONFIG.FPS)
    
    def _desenhar_painel_superior(self, malha: MalhaViaria) -> None:
        """Desenha o painel superior com título e informações básicas."""
        # Fundo do painel
        altura_painel = 60
        pygame.draw.rect(self.tela, (30, 30, 40), (0, 0, CONFIG.LARGURA_TELA, altura_painel))
        pygame.draw.line(self.tela, CONFIG.CINZA, (0, altura_painel), (CONFIG.LARGURA_TELA, altura_painel), 2)
        
        # Título
        titulo = "SIMULAÇÃO DE TRÁFEGO URBANO"
        superficie_titulo = self.fontes['titulo'].render(titulo, True, CONFIG.BRANCO)
        rect_titulo = superficie_titulo.get_rect(center=(CONFIG.LARGURA_TELA // 2, 20))
        self.tela.blit(superficie_titulo, rect_titulo)
        
        # Subtítulo
        subtitulo = "Projeto de Graduação em Computação - UFABC"
        superficie_subtitulo = self.fontes['pequena'].render(subtitulo, True, CONFIG.CINZA_CLARO)
        rect_subtitulo = superficie_subtitulo.get_rect(center=(CONFIG.LARGURA_TELA // 2, 40))
        self.tela.blit(superficie_subtitulo, rect_subtitulo)
    
    def _desenhar_painel_lateral(self, malha: MalhaViaria, info_simulacao: Dict) -> None:
        """Desenha o painel lateral com estatísticas detalhadas."""
        # Dimensões do painel
        largura_painel = 300
        altura_painel = 400
        x_painel = CONFIG.LARGURA_TELA - largura_painel - 20
        y_painel = 80

        # Fundo do painel
        superficie_painel = pygame.Surface((largura_painel, altura_painel))
        superficie_painel.set_alpha(220)
        superficie_painel.fill((40, 40, 50))

        # Borda
        pygame.draw.rect(superficie_painel, CONFIG.CINZA, superficie_painel.get_rect(), 2)

        # Título do painel
        y_texto = 15
        titulo = "ESTATÍSTICAS DA SIMULAÇÃO"
        superficie_titulo = self.fontes['media'].render(titulo, True, CONFIG.BRANCO)
        rect_titulo = superficie_titulo.get_rect(centerx=largura_painel//2, y=y_texto)
        superficie_painel.blit(superficie_titulo, rect_titulo)

        # Linha separadora
        y_texto += 35
        pygame.draw.line(superficie_painel, CONFIG.CINZA,
                         (10, y_texto), (largura_painel - 10, y_texto), 1)
        y_texto += 15

        estatisticas = malha.obter_estatisticas()

        # Seção TEMPO
        self._desenhar_secao(superficie_painel, "TEMPO", y_texto, [
            f"Tempo de Simulação: {estatisticas['tempo_simulacao']:.1f}s",
            f"Velocidade: {info_simulacao.get('velocidade', 1.0)}x"
        ])
        y_texto += 70

        # Seção VEÍCULOS
        self._desenhar_secao(superficie_painel, "VEÍCULOS", y_texto, [
            f"Ativos: {estatisticas['veiculos_ativos']}",
            f"Total Gerado: {estatisticas['veiculos_total']}",
            f"Concluídos: {estatisticas['veiculos_concluidos']}"
        ])
        y_texto += 90

        # Seção DESEMPENHO
        self._desenhar_secao(superficie_painel, "DESEMPENHO", y_texto, [
            f"Tempo Médio de Viagem: {estatisticas['tempo_viagem_medio']:.1f}s",
            f"Tempo Médio Parado: {estatisticas['tempo_parado_medio']:.1f}s",
            f"Eficiência: {self._calcular_eficiencia(estatisticas):.1f}%"
        ])
        y_texto += 90

        # Seção SCORE
        score = info_simulacao.get('score', 0.0)
        self._desenhar_secao(superficie_painel, "SCORE", y_texto, [
            f"Score: {score:.1f}/100"
        ])
        y_texto += 40

        # Seção CONTROLE (Heurística atual)
        self._desenhar_secao(superficie_painel, "CONTROLE", y_texto, [
            f"Heurística: {estatisticas['heuristica']}",
            f"Estado: {info_simulacao.get('estado', 'Executando')}"
        ])

        # Blit final do painel
        self.tela.blit(superficie_painel, (x_painel, y_painel))
    
    def _desenhar_secao(self, superficie: pygame.Surface, titulo: str, y_inicial: int, 
                       itens: List[str]) -> None:
        """Desenha uma seção de informações no painel."""
        # Título da seção
        superficie_titulo = self.fontes['media'].render(titulo, True, CONFIG.AMARELO)
        superficie.blit(superficie_titulo, (20, y_inicial))
        
        # Itens
        y = y_inicial + 25
        for item in itens:
            superficie_item = self.fontes['pequena'].render(item, True, CONFIG.BRANCO)
            superficie.blit(superficie_item, (30, y))
            y += 20
    
    def _calcular_eficiencia(self, estatisticas: Dict) -> float:
        """Calcula a eficiência do sistema de tráfego."""
        if estatisticas['tempo_viagem_medio'] == 0:
            return 0
        
        # Eficiência baseada na razão entre tempo em movimento e tempo total
        tempo_movimento = estatisticas['tempo_viagem_medio'] - estatisticas['tempo_parado_medio']
        eficiencia = (tempo_movimento / estatisticas['tempo_viagem_medio']) * 100
        
        return max(0, min(100, eficiencia))
    
    def _desenhar_controles(self) -> None:
        """Desenha o painel de controles."""
        # Dimensões do painel
        largura_painel = 350
        altura_painel = 150
        x_painel = 20
        y_painel = CONFIG.ALTURA_TELA - altura_painel - 20
        
        # Fundo do painel
        superficie_painel = pygame.Surface((largura_painel, altura_painel))
        superficie_painel.set_alpha(200)
        superficie_painel.fill((40, 40, 50))
        pygame.draw.rect(superficie_painel, CONFIG.CINZA, superficie_painel.get_rect(), 2)
        
        # Título
        y_texto = 10
        titulo = "CONTROLES"
        superficie_titulo = self.fontes['media'].render(titulo, True, CONFIG.BRANCO)
        rect_titulo = superficie_titulo.get_rect(centerx=largura_painel//2, y=y_texto)
        superficie_painel.blit(superficie_titulo, rect_titulo)
        
        # Controles
        y_texto = 35
        controles = [
            ("ESC", "Sair da simulação"),
            ("ESPAÇO", "Pausar/Continuar"),
            ("R", "Reiniciar simulação"),
            ("+/-", "Ajustar velocidade"),
            ("1-4", "Mudar heurística"),
            ("TAB", "Alternar estatísticas")
        ]
        
        for tecla, descricao in controles:
            # Tecla
            superficie_tecla = self.fontes['pequena'].render(tecla, True, CONFIG.AMARELO)
            superficie_painel.blit(superficie_tecla, (20, y_texto))
            
            # Descrição
            superficie_desc = self.fontes['pequena'].render(descricao, True, CONFIG.BRANCO)
            superficie_painel.blit(superficie_desc, (80, y_texto))
            
            y_texto += 18
        
        # Desenha o painel na tela
        self.tela.blit(superficie_painel, (x_painel, y_painel))
    
    def desenhar_mensagem(self, mensagem: str, cor: Tuple[int, int, int] = None) -> None:
        """
        Desenha uma mensagem temporária no centro da tela.
        
        Args:
            mensagem: Texto da mensagem
            cor: Cor da mensagem
        """
        if cor is None:
            cor = CONFIG.BRANCO
        
        # Cria superfície para a mensagem
        superficie_msg = self.fontes['grande'].render(mensagem, True, cor)
        rect_msg = superficie_msg.get_rect(center=(CONFIG.LARGURA_TELA // 2, CONFIG.ALTURA_TELA // 2))
        
        # Fundo semi-transparente
        superficie_fundo = pygame.Surface((rect_msg.width + 40, rect_msg.height + 20))
        superficie_fundo.set_alpha(180)
        superficie_fundo.fill(CONFIG.PRETO)
        
        rect_fundo = superficie_fundo.get_rect(center=(CONFIG.LARGURA_TELA // 2, CONFIG.ALTURA_TELA // 2))
        
        # Desenha
        self.tela.blit(superficie_fundo, rect_fundo)
        self.tela.blit(superficie_msg, rect_msg)
    
    def obter_fps(self) -> float:
        """Retorna o FPS atual."""
        return self.relogio.get_fps()