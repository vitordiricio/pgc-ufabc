"""
Módulo de simulação para a malha viária urbana.
"""
import pygame
from configuracao import CONFIG
from cruzamento import MalhaViaria
from renderizador import Renderizador


class Simulacao:
    """Classe principal de simulação que coordena a malha viária e o renderizador."""
    
    def __init__(self, linhas: int = CONFIG.LINHAS_GRADE, colunas: int = CONFIG.COLUNAS_GRADE):
        """
        Inicializa os componentes da simulação.
        
        Args:
            linhas: Número de linhas na grade de cruzamentos
            colunas: Número de colunas na grade de cruzamentos
        """
        self.malha = MalhaViaria(linhas, colunas)
        self.renderizador = Renderizador()
        self.rodando = True
        self.pausado = False
        self.multiplicador_velocidade = 1.0
        self.contador_quadros = 0
        self.tempo_simulacao = 0
        # Modo debug removido completamente
    
    def processar_eventos(self) -> None:
        """Lida com eventos do pygame."""
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            elif evento.type == pygame.KEYDOWN:
                self._processar_tecla_pressionada(evento)
    
    def _processar_tecla_pressionada(self, evento: pygame.event.Event) -> None:
        """
        Processa eventos de tecla pressionada.
        
        Args:
            evento: Evento de tecla pressionada
        """
        if evento.key == pygame.K_ESCAPE:
            self.rodando = False
        elif evento.key == pygame.K_SPACE:
            # Pausa/continua a simulação
            self.pausado = not self.pausado
        elif evento.key == pygame.K_PLUS or evento.key == pygame.K_EQUALS:
            # Aumenta a velocidade da simulação
            self.multiplicador_velocidade = min(4.0, self.multiplicador_velocidade + 0.5)
        elif evento.key == pygame.K_MINUS:
            # Diminui a velocidade da simulação
            self.multiplicador_velocidade = max(0.5, self.multiplicador_velocidade - 0.5)
        elif evento.key == pygame.K_r:
            # Reinicia a simulação
            self.reiniciar()
        # Removida a opção da tecla D para modo de depuração
    
    def atualizar(self) -> None:
        """Atualiza o estado da simulação."""
        if not self.pausado:
            # Aplica o multiplicador de velocidade realizando múltiplas atualizações
            passos = max(1, int(self.multiplicador_velocidade))
            for _ in range(passos):
                self.malha.atualizar()
                self.contador_quadros += 1
            
            # Atualiza o tempo de simulação (em segundos)
            if self.contador_quadros % CONFIG.FPS == 0:
                self.tempo_simulacao += 1
    
    def renderizar(self) -> None:
        """Renderiza o estado atual da simulação."""
        # Prepara informações adicionais para exibição
        info_adicional = {
            "Tempo simulação": f"{self.tempo_simulacao}s",
            "Velocidade": f"{self.multiplicador_velocidade}x",
            "Veículos ativos": self.malha.estatisticas["veiculos_ativos"],
            "Total gerado": self.malha.estatisticas["veiculos_totais"],
            "Estado": "Pausado" if self.pausado else "Executando"
        }
        
        # Renderiza a malha viária
        self.renderizador.renderizar(self.malha, info_adicional)
    
    def reiniciar(self) -> None:
        """Reinicia a simulação para o estado inicial."""
        self.malha = MalhaViaria(CONFIG.LINHAS_GRADE, CONFIG.COLUNAS_GRADE)
        self.pausado = False
        self.multiplicador_velocidade = 1.0
        self.contador_quadros = 0
        self.tempo_simulacao = 0
    
    def executar(self) -> None:
        """Executa o loop principal da simulação."""
        while self.rodando:
            self.processar_eventos()
            self.atualizar()
            self.renderizar()