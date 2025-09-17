"""
Módulo de renderização aprimorado para a simulação de malha viária urbana.
Centraliza todas as responsabilidades visuais do sistema.
"""
import pygame
import math
from typing import Dict, List, Tuple
from configuracao import CONFIG, Direcao, EstadoSemaforo
from cruzamento import MalhaViaria, Cruzamento
from veiculo import Veiculo
from semaforo import Semaforo


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

    @staticmethod
    def _linha_tracejada(surface, cor, start_pos, end_pos, dash_length=14, gap_length=10, width=2):
        import math
        x1, y1 = start_pos
        x2, y2 = end_pos
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist == 0:
            return
        vx = dx / dist
        vy = dy / dist
        n_dashes = int(dist // (dash_length + gap_length)) + 1
        for i in range(n_dashes):
            sx = x1 + (dash_length + gap_length) * i * vx
            sy = y1 + (dash_length + gap_length) * i * vy
            ex = sx + dash_length * vx
            ey = sy + dash_length * vy
            pygame.draw.line(surface, cor, (sx, sy), (ex, ey), width)

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
        
        # Desenha a malha viária usando métodos centralizados
        self.desenhar_malha_viaria(self.tela, malha)
        
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
            ("1-4", "Mudar heurística automática"),
            ("5",   "Modo Manual"),
            ("N",   "Avançar fase manual (todos)"),
            ("Clique", "Alternar semáforo sob o mouse (Manual)"),  # <-- adicionado
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
    
    # ========================================
    # MÉTODOS DE RENDERIZAÇÃO DE CRUZAMENTOS
    # ========================================
    
    def desenhar_cruzamento(self, tela: pygame.Surface, cruzamento: Cruzamento) -> None:
        """Desenha um cruzamento e seus elementos."""
        # Desenha área do cruzamento
        area_cruzamento = pygame.Rect(
            cruzamento.limites['esquerda'],
            cruzamento.limites['topo'],
            cruzamento.largura_rua,
            cruzamento.largura_rua
        )
        pygame.draw.rect(tela, CONFIG.CINZA, area_cruzamento)

        # Desenha linhas de parada apenas para direções permitidas
        self._desenhar_linhas_parada(tela, cruzamento)

        # Desenha semáforos
        semaforos = cruzamento.gerenciador_semaforos.semaforos.get(cruzamento.id, {})
        for semaforo in semaforos.values():
            self.desenhar_semaforo(tela, semaforo)

        # Desenha informações debug
        if CONFIG.MOSTRAR_INFO_VEICULO:
            self._desenhar_info_debug_cruzamento(tela, cruzamento)

    def _desenhar_linhas_parada(self, tela: pygame.Surface, cruzamento: Cruzamento) -> None:
        """Desenha as linhas de parada apenas para direções de mão única."""
        cor_linha = CONFIG.BRANCO
        largura_linha = 3

        # Linha Norte (horizontal, antes do cruzamento vindo de cima)
        pygame.draw.line(tela,
                        cor_linha,
                        (cruzamento.limites['esquerda'], cruzamento.limites['topo'] - 20),
                        (cruzamento.limites['direita'], cruzamento.limites['topo'] - 20),
                        largura_linha)

        # Linha Leste (vertical, antes do cruzamento vindo da esquerda)
        pygame.draw.line(tela,
                        cor_linha,
                        (cruzamento.limites['esquerda'] - 20, cruzamento.limites['topo']),
                        (cruzamento.limites['esquerda'] - 20, cruzamento.limites['base']),
                        largura_linha)

    def _desenhar_info_debug_cruzamento(self, tela: pygame.Surface, cruzamento: Cruzamento) -> None:
        """Desenha informações de debug do cruzamento."""
        fonte = pygame.font.SysFont('Arial', 12)
        texto = f"C({cruzamento.id[0]},{cruzamento.id[1]}) D:{cruzamento.estatisticas['densidade_atual']}"
        superficie = fonte.render(texto, True, CONFIG.BRANCO)
        tela.blit(superficie, (cruzamento.centro_x - 30, cruzamento.centro_y - 10))

    # ========================================
    # MÉTODOS DE RENDERIZAÇÃO DE MALHA VIÁRIA
    # ========================================
    
    def desenhar_malha_viaria(self, tela: pygame.Surface, malha: MalhaViaria) -> None:
        """Desenha toda a malha viária."""
        # Desenha as ruas
        self._desenhar_ruas(tela, malha)

        # Desenha os cruzamentos
        for cruzamento in malha.cruzamentos.values():
            self.desenhar_cruzamento(tela, cruzamento)

        # Desenha os veículos
        for veiculo in malha.veiculos:
            self.desenhar_veiculo(tela, veiculo)

    def _desenhar_ruas(self, tela: pygame.Surface, malha: MalhaViaria) -> None:
        """Desenha as ruas da malha com múltiplas faixas, setas e (opcional) overlay do CAOS."""
        # ---- Ruas horizontais (fluxo Leste → Oeste) ----
        for linha in range(malha.linhas):
            yc = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_VERTICAL
            y_top = int(yc - CONFIG.LARGURA_RUA // 2)
            y_bot = int(yc + CONFIG.LARGURA_RUA // 2)

            # Fundo da rua
            pygame.draw.rect(
                tela,
                CONFIG.CINZA_ESCURO,
                (0, y_top, CONFIG.LARGURA_TELA, int(CONFIG.LARGURA_RUA))
            )

            # Indicadores de direção (setas)
            self._desenhar_setas_horizontais(tela, yc, Direcao.LESTE, malha)

            # Bordas da rua (superior e inferior)
            pygame.draw.line(tela, CONFIG.BRANCO, (0, y_top), (CONFIG.LARGURA_TELA, y_top), 2)
            pygame.draw.line(tela, CONFIG.BRANCO, (0, y_bot), (CONFIG.LARGURA_TELA, y_bot), 2)

            # Divisórias de faixa (tracejadas) — internas
            for i in range(1, CONFIG.FAIXAS_POR_VIA):
                y_linha = yc - CONFIG.LARGURA_RUA / 2.0 + i * CONFIG.LARGURA_FAIXA
                self._linha_tracejada(
                    tela,
                    CONFIG.BRANCO,
                    (0, int(y_linha)),
                    (CONFIG.LARGURA_TELA, int(y_linha)),
                    dash_length=18,
                    gap_length=12,
                    width=2
                )

            # Overlay do "caos" (opcional)
            if CONFIG.CHAOS_MOSTRAR:
                self._desenhar_overlay_caos_horizontal(tela, yc, malha, linha)

        # ---- Ruas verticais (fluxo Norte → Sul) ----
        for coluna in range(malha.colunas):
            xc = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_HORIZONTAL
            x_left = int(xc - CONFIG.LARGURA_RUA // 2)
            x_right = int(xc + CONFIG.LARGURA_RUA // 2)

            # Fundo da rua
            pygame.draw.rect(
                tela,
                CONFIG.CINZA_ESCURO,
                (x_left, 0, int(CONFIG.LARGURA_RUA), CONFIG.ALTURA_TELA)
            )

            # Indicadores de direção (setas)
            self._desenhar_setas_verticais(tela, xc, Direcao.NORTE, malha)

            # Bordas da rua (esquerda e direita)
            pygame.draw.line(tela, CONFIG.BRANCO, (x_left, 0), (x_left, CONFIG.ALTURA_TELA), 2)
            pygame.draw.line(tela, CONFIG.BRANCO, (x_right, 0), (x_right, CONFIG.ALTURA_TELA), 2)

            # Divisórias de faixa (tracejadas) — internas
            for i in range(1, CONFIG.FAIXAS_POR_VIA):
                x_linha = xc - CONFIG.LARGURA_RUA / 2.0 + i * CONFIG.LARGURA_FAIXA
                self._linha_tracejada(
                    tela,
                    CONFIG.BRANCO,
                    (int(x_linha), 0),
                    (int(x_linha), CONFIG.ALTURA_TELA),
                    dash_length=18,
                    gap_length=12,
                    width=2
                )

            # Overlay do "caos" (opcional)
            if CONFIG.CHAOS_MOSTRAR:
                self._desenhar_overlay_caos_vertical(tela, xc, malha, coluna)

    def _desenhar_setas_horizontais(self, tela: pygame.Surface, y: float, direcao: Direcao, malha: MalhaViaria) -> None:
        """Desenha setas indicando a direção do fluxo horizontal."""
        if not CONFIG.MOSTRAR_DIRECAO_FLUXO:
            return

        # Desenha setas a cada intervalo
        intervalo = 100
        tamanho_seta = 15

        for x in range(50, CONFIG.LARGURA_TELA, intervalo):
            # Evita desenhar setas nos cruzamentos
            perto_de_cruzamento = False
            for coluna in range(malha.colunas):
                x_cruzamento = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_HORIZONTAL
                if abs(x - x_cruzamento) < CONFIG.LARGURA_RUA:
                    perto_de_cruzamento = True
                    break

            if not perto_de_cruzamento:
                # Desenha seta para direita (Leste→Oeste)
                pontos = [
                    (x - tamanho_seta, y - 5),
                    (x - tamanho_seta, y + 5),
                    (x, y)
                ]
                pygame.draw.polygon(tela, CONFIG.AMARELO, pontos)

    def _desenhar_setas_verticais(self, tela: pygame.Surface, x: float, direcao: Direcao, malha: MalhaViaria) -> None:
        """Desenha setas indicando a direção do fluxo vertical."""
        if not CONFIG.MOSTRAR_DIRECAO_FLUXO:
            return

        # Desenha setas a cada intervalo
        intervalo = 100
        tamanho_seta = 15

        for y in range(50, CONFIG.ALTURA_TELA, intervalo):
            # Evita desenhar setas nos cruzamentos
            perto_de_cruzamento = False
            for linha in range(malha.linhas):
                y_cruzamento = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_VERTICAL
                if abs(y - y_cruzamento) < CONFIG.LARGURA_RUA:
                    perto_de_cruzamento = True
                    break

            if not perto_de_cruzamento:
                # Desenha seta para baixo (Norte→Sul)
                pontos = [
                    (x - 5, y - tamanho_seta),
                    (x + 5, y - tamanho_seta),
                    (x, y)
                ]
                pygame.draw.polygon(tela, CONFIG.AMARELO, pontos)

    def _desenhar_overlay_caos_horizontal(self, tela: pygame.Surface, y: float, malha: MalhaViaria, linha: int) -> None:
        """Desenha overlay do caos para ruas horizontais."""
        seg = CONFIG.CHAOS_TAMANHO_SEGMENTO
        y_top = y - CONFIG.LARGURA_RUA // 2
        vetor = malha.caos_horizontal[linha]
        for i, fator in enumerate(vetor):
            x0 = i * seg
            w = seg if x0 + seg <= CONFIG.LARGURA_TELA else CONFIG.LARGURA_TELA - x0
            if w <= 0:
                continue
            surf = pygame.Surface((w, CONFIG.LARGURA_RUA), pygame.SRCALPHA)
            # vermelho suave se <1; verde suave se >1
            if fator < 1.0:
                cor = (255, 80, 80, int((1.0 - fator) * 80))
            else:
                cor = (80, 255, 80, int((fator - 1.0) * 80))
            surf.fill(cor)
            tela.blit(surf, (x0, y_top))

    def _desenhar_overlay_caos_vertical(self, tela: pygame.Surface, x: float, malha: MalhaViaria, coluna: int) -> None:
        """Desenha overlay do caos para ruas verticais."""
        seg = CONFIG.CHAOS_TAMANHO_SEGMENTO
        x_left = x - CONFIG.LARGURA_RUA // 2
        vetor = malha.caos_vertical[coluna]
        for j, fator in enumerate(vetor):
            y0 = j * seg
            h = seg if y0 + seg <= CONFIG.ALTURA_TELA else CONFIG.ALTURA_TELA - y0
            if h <= 0:
                continue
            surf = pygame.Surface((CONFIG.LARGURA_RUA, h), pygame.SRCALPHA)
            if fator < 1.0:
                cor = (255, 80, 80, int((1.0 - fator) * 80))
            else:
                cor = (80, 255, 80, int((fator - 1.0) * 80))
            surf.fill(cor)
            tela.blit(surf, (x_left, y0))

    # ========================================
    # MÉTODOS DE RENDERIZAÇÃO DE VEÍCULOS
    # ========================================
    
    def desenhar_veiculo(self, tela: pygame.Surface, veiculo: Veiculo) -> None:
        """Desenha o veículo na tela com visual aprimorado - MÃO ÚNICA."""
        # Cria superfície para o veículo
        if veiculo.direcao == Direcao.NORTE:
            superficie = pygame.Surface((veiculo.largura, veiculo.altura), pygame.SRCALPHA)
        else:  # Direcao.LESTE
            superficie = pygame.Surface((veiculo.altura, veiculo.largura), pygame.SRCALPHA)
        
        # Desenha o corpo do veículo
        pygame.draw.rect(superficie, veiculo.cor, superficie.get_rect(), border_radius=4)
        
        # Adiciona detalhes (janelas)
        cor_janela = (200, 220, 255, 180)
        if veiculo.direcao == Direcao.NORTE:
            # Janela frontal (parte de baixo - direção do movimento)
            pygame.draw.rect(superficie, cor_janela, 
                           (3, veiculo.altura * 0.7, veiculo.largura - 6, veiculo.altura * 0.25), 
                           border_radius=2)
            # Janela traseira (parte de cima)
            pygame.draw.rect(superficie, cor_janela, 
                           (3, 3, veiculo.largura - 6, veiculo.altura * 0.3), 
                           border_radius=2)
        else:  # Direcao.LESTE
            # Janela frontal (parte direita - direção do movimento)
            pygame.draw.rect(superficie, cor_janela, 
                           (veiculo.altura * 0.7, 3, veiculo.altura * 0.25, veiculo.largura - 6), 
                           border_radius=2)
            # Janela traseira (parte esquerda)
            pygame.draw.rect(superficie, cor_janela, 
                           (3, 3, veiculo.altura * 0.3, veiculo.largura - 6), 
                           border_radius=2)
        
        # Adiciona luzes de freio se estiver freando
        if veiculo.aceleracao_atual < -0.1:
            cor_freio = (255, 100, 100)
            if veiculo.direcao == Direcao.NORTE:
                # Luzes na parte de cima (traseira)
                pygame.draw.rect(superficie, cor_freio, (2, 1, 6, 3))
                pygame.draw.rect(superficie, cor_freio, (veiculo.largura - 8, 1, 6, 3))
            elif veiculo.direcao == Direcao.LESTE:
                # Luzes na parte esquerda (traseira)
                pygame.draw.rect(superficie, cor_freio, (1, 2, 3, 6))
                pygame.draw.rect(superficie, cor_freio, (1, veiculo.largura - 8, 3, 6))
        
        # Adiciona faróis
        cor_farol = (255, 255, 200, 150)
        if veiculo.direcao == Direcao.NORTE:
            # Faróis na frente (parte de baixo)
            pygame.draw.circle(superficie, cor_farol, (8, veiculo.altura - 5), 3)
            pygame.draw.circle(superficie, cor_farol, (veiculo.largura - 8, veiculo.altura - 5), 3)
        elif veiculo.direcao == Direcao.LESTE:
            # Faróis na frente (parte direita)
            pygame.draw.circle(superficie, cor_farol, (veiculo.altura - 5, 8), 3)
            pygame.draw.circle(superficie, cor_farol, (veiculo.altura - 5, veiculo.largura - 8), 3)
        
        # Desenha na tela
        rect = superficie.get_rect(center=(int(veiculo.posicao[0]), int(veiculo.posicao[1])))
        tela.blit(superficie, rect)
        
        # Debug info
        if CONFIG.MOSTRAR_INFO_VEICULO:
            self._desenhar_info_debug_veiculo(tela, veiculo)

    def _desenhar_info_debug_veiculo(self, tela: pygame.Surface, veiculo: Veiculo) -> None:
        """Desenha informações de debug do veículo."""
        fonte = pygame.font.SysFont('Arial', 10)
        # Adiciona indicador se está aguardando semáforo ou veículo
        aguardando = ""
        if veiculo.aguardando_semaforo:
            aguardando = "🔴"
        elif veiculo.veiculo_frente and veiculo.distancia_veiculo_frente < CONFIG.DISTANCIA_REACAO:
            aguardando = "🚗"
        
        texto = f"V:{veiculo.velocidade:.1f} ID:{veiculo.id} {aguardando}"
        superficie_texto = fonte.render(texto, True, CONFIG.BRANCO)
        tela.blit(superficie_texto, (veiculo.posicao[0] - 20, veiculo.posicao[1] - 25))

    # ========================================
    # MÉTODOS DE RENDERIZAÇÃO DE SEMÁFOROS
    # ========================================
    
    def desenhar_semaforo(self, tela: pygame.Surface, semaforo: Semaforo) -> None:
        """Desenha o semáforo na tela com visual aprimorado - MÃO ÚNICA."""
        # Dimensões da caixa do semáforo
        largura = CONFIG.TAMANHO_SEMAFORO * 3 + CONFIG.ESPACAMENTO_SEMAFORO * 2
        altura = CONFIG.TAMANHO_SEMAFORO + 8

        # Posição da caixa - ajustada para mão única
        if semaforo.direcao == Direcao.NORTE:
            # Semáforo horizontal para tráfego vertical
            rect_caixa = pygame.Rect(
                semaforo.posicao[0] - largura // 2,
                semaforo.posicao[1] - altura // 2,
                largura, altura
            )
        else:  # Direcao.LESTE
            # Semáforo vertical para tráfego horizontal
            rect_caixa = pygame.Rect(
                semaforo.posicao[0] - altura // 2,
                semaforo.posicao[1] - largura // 2,
                altura, largura
            )
        
        # Desenha a caixa do semáforo
        pygame.draw.rect(tela, CONFIG.PRETO, rect_caixa, border_radius=4)
        pygame.draw.rect(tela, CONFIG.CINZA_ESCURO, rect_caixa, 2, border_radius=4)
        
        # Cores das luzes
        cores = {
            EstadoSemaforo.VERMELHO: CONFIG.VERMELHO if semaforo.estado == EstadoSemaforo.VERMELHO else (60, 20, 20),
            EstadoSemaforo.AMARELO: CONFIG.AMARELO if semaforo.estado == EstadoSemaforo.AMARELO else (60, 60, 20),
            EstadoSemaforo.VERDE: CONFIG.VERDE if semaforo.estado == EstadoSemaforo.VERDE else (20, 60, 20)
        }
        
        # Desenha as luzes
        raio = CONFIG.TAMANHO_SEMAFORO // 2 - 1
        
        if semaforo.direcao == Direcao.NORTE:
            # Semáforo horizontal
            x_base = rect_caixa.x + CONFIG.TAMANHO_SEMAFORO // 2 + 4
            y_centro = rect_caixa.centery
            
            for i, (estado, cor) in enumerate(cores.items()):
                x = x_base + i * (CONFIG.TAMANHO_SEMAFORO + CONFIG.ESPACAMENTO_SEMAFORO)
                pygame.draw.circle(tela, cor, (x, y_centro), raio)
                
                # Adiciona brilho se a luz estiver ativa
                if semaforo.estado == estado:
                    pygame.draw.circle(tela, cor, (x, y_centro), raio - 2, 2)
        else:  # Direcao.LESTE
            # Semáforo vertical
            x_centro = rect_caixa.centerx
            y_base = rect_caixa.y + CONFIG.TAMANHO_SEMAFORO // 2 + 4
            
            for i, (estado, cor) in enumerate(cores.items()):
                y = y_base + i * (CONFIG.TAMANHO_SEMAFORO + CONFIG.ESPACAMENTO_SEMAFORO)
                pygame.draw.circle(tela, cor, (x_centro, y), raio)
                
                # Adiciona brilho se a luz estiver ativa
                if semaforo.estado == estado:
                    pygame.draw.circle(tela, cor, (x_centro, y), raio - 2, 2)
        
        # Define área clicável para modo manual
        semaforo._click_rect = rect_caixa.inflate(8, 8)