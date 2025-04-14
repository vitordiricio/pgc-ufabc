"""
Módulo de semáforo para a simulação de cruzamento de tráfego com múltiplos cruzamentos.
"""
from typing import Tuple, Dict, Optional
import pygame
from configuracao import CONFIG, EstadoSemaforo, Direcao


class Semaforo:
    """Representa um semáforo na simulação."""
    
    def __init__(self, posicao: Tuple[int, int], direcao: Direcao):
        """
        Inicializa um semáforo.
        
        Args:
            posicao: Posição (x, y) do semáforo
            direcao: Direção do tráfego que o semáforo controla
        """
        self.posicao = posicao
        self.direcao = direcao
        
        # Semáforo Norte começa verde e Leste começa vermelho para garantir alternância
        # Norte: carros de cima para baixo
        # Leste: carros da esquerda para direita
        self.estado = EstadoSemaforo.VERMELHO if direcao == Direcao.LESTE else EstadoSemaforo.VERDE
        self.temporizador = 0
        self.duracao_estado = CONFIG.TEMPO_SEMAFORO[self.estado]
        
    def atualizar(self) -> EstadoSemaforo:
        """
        Atualiza o estado do semáforo com base no temporizador.
        
        Returns:
            EstadoSemaforo: Retorna o estado anterior para detectar mudanças
        """
        estado_anterior = self.estado
        self.temporizador += 1
        
        # Verifica se é hora de mudar o estado
        if self.temporizador >= self.duracao_estado:
            self._mudar_estado()
            self.temporizador = 0
            
        return estado_anterior
    
    def _mudar_estado(self) -> None:
        """Altera o estado do semáforo para o próximo na sequência."""
        # Garante a sequência correta: VERDE -> AMARELO -> VERMELHO -> VERDE
        if self.estado == EstadoSemaforo.VERDE:
            # Após VERDE sempre vai para AMARELO
            self.estado = EstadoSemaforo.AMARELO
        elif self.estado == EstadoSemaforo.AMARELO:
            # Após AMARELO sempre vai para VERMELHO
            self.estado = EstadoSemaforo.VERMELHO
        elif self.estado == EstadoSemaforo.VERMELHO:
            # Após VERMELHO sempre vai para VERDE
            self.estado = EstadoSemaforo.VERDE
        
        # Atualiza a duração do estado
        self.duracao_estado = CONFIG.TEMPO_SEMAFORO[self.estado]
    
    def esta_verde(self) -> bool:
        """Retorna True se o semáforo estiver verde."""
        return self.estado == EstadoSemaforo.VERDE
    
    def esta_vermelho(self) -> bool:
        """Retorna True se o semáforo estiver vermelho."""
        return self.estado == EstadoSemaforo.VERMELHO
    
    def esta_amarelo(self) -> bool:
        """Retorna True se o semáforo estiver amarelo."""
        return self.estado == EstadoSemaforo.AMARELO
    
    def definir_estado(self, estado: EstadoSemaforo, resetar_temporizador: bool = True) -> None:
        """
        Define o estado do semáforo diretamente.
        
        Args:
            estado: O novo estado do semáforo
            resetar_temporizador: Se True, reseta o temporizador
        """
        self.estado = estado
        if resetar_temporizador:
            self.temporizador = 0
        self.duracao_estado = CONFIG.TEMPO_SEMAFORO[self.estado]
    
    def desenhar(self, tela: pygame.Surface) -> None:
        """
        Desenha o semáforo na tela.
        
        Args:
            tela: Superfície Pygame para desenhar
        """
        # Desenha a caixa do semáforo
        largura_caixa = CONFIG.TAMANHO_SEMAFORO
        altura_caixa = (CONFIG.TAMANHO_SEMAFORO * 3) + (CONFIG.ESPACAMENTO_SEMAFORO * 2)
        
        # Ajusta a posição com base na direção
        x_caixa, y_caixa = self._obter_posicao_ajustada(largura_caixa, altura_caixa)
        
        # Desenha a caixa de fundo
        pygame.draw.rect(
            tela,
            CONFIG.PRETO,
            pygame.Rect(x_caixa, y_caixa, largura_caixa, altura_caixa),
            0,
            3
        )
        
        # Desenha as luzes do semáforo (vermelho, amarelo, verde de cima para baixo)
        estados_luz = [
            (EstadoSemaforo.VERMELHO, CONFIG.VERMELHO),
            (EstadoSemaforo.AMARELO, CONFIG.AMARELO),
            (EstadoSemaforo.VERDE, CONFIG.VERDE)
        ]
        
        for i, (estado_luz, cor) in enumerate(estados_luz):
            # Calcular posição da luz
            x_luz = x_caixa + CONFIG.TAMANHO_SEMAFORO // 2
            y_luz = y_caixa + (i * (CONFIG.TAMANHO_SEMAFORO + CONFIG.ESPACAMENTO_SEMAFORO)) + CONFIG.TAMANHO_SEMAFORO // 2
            
            # Desenha o círculo da luz (escurecido se não for o estado atual)
            cor_luz = cor if self.estado == estado_luz else (cor[0]//4, cor[1]//4, cor[2]//4)
            pygame.draw.circle(tela, cor_luz, (x_luz, y_luz), CONFIG.TAMANHO_SEMAFORO // 2)
    
    def _obter_posicao_ajustada(self, largura: int, altura: int) -> Tuple[int, int]:
        """
        Ajusta a posição do semáforo com base na direção.
        
        Args:
            largura: Largura da caixa do semáforo
            altura: Altura da caixa do semáforo
            
        Returns:
            Tuple[int, int]: Posição ajustada (x, y)
        """
        x, y = self.posicao
        
        # Para melhor visualização, centralizamos o semáforo na sua posição
        x_ajustado = x - largura // 2
        y_ajustado = y - altura // 2
        
        return x_ajustado, y_ajustado


class ControladorSemaforo:
    """
    Controlador de semáforos que gerencia a sincronização
    entre os semáforos em um cruzamento.
    """
    
    def __init__(self, id_cruzamento: Tuple[int, int]):
        """
        Inicializa o controlador de semáforos.
        
        Args:
            id_cruzamento: Identificador (linha, coluna) do cruzamento
        """
        self.id_cruzamento = id_cruzamento
        self.semaforos = {}
        self.ciclo_iniciado = False
        
        # Flag para controlar quando ambos os semáforos devem estar vermelhos por segurança
        self.ambos_vermelhos = False
        self.contador_seguranca = 0
        self.periodo_seguranca = 60  # 1 segundo a 60 FPS
    
    def adicionar_semaforo(self, direcao: Direcao, semaforo: Semaforo) -> None:
        """
        Adiciona um semáforo ao controlador.
        
        Args:
            direcao: A direção que o semáforo controla
            semaforo: O objeto semáforo
        """
        self.semaforos[direcao] = semaforo
        
        # Configura os estados iniciais para garantir que Norte começa verde e Leste vermelho
        if direcao == Direcao.NORTE:
            semaforo.definir_estado(EstadoSemaforo.VERDE)
        elif direcao == Direcao.LESTE:
            semaforo.definir_estado(EstadoSemaforo.VERMELHO)
    
    def atualizar(self) -> None:
        """Atualiza todos os semáforos e mantém a sincronização adequada."""
        if not self.semaforos:
            return
        
        semaforo_norte = self.semaforos.get(Direcao.NORTE)
        semaforo_leste = self.semaforos.get(Direcao.LESTE)
        
        if not semaforo_norte or not semaforo_leste:
            return
            
        # Se os dois estão verdes ao mesmo tempo (situação incorreta)
        if semaforo_norte.esta_verde() and semaforo_leste.esta_verde():
            # Corrige fazendo o Leste ficar vermelho
            semaforo_leste.definir_estado(EstadoSemaforo.VERMELHO)
            return
            
        # Estado especial: ambos vermelhos (período de segurança)
        if self.ambos_vermelhos:
            self.contador_seguranca += 1
            if self.contador_seguranca >= self.periodo_seguranca:
                self.ambos_vermelhos = False
                self.contador_seguranca = 0
                
                # Após o período de segurança, um semáforo fica verde
                if semaforo_norte.esta_vermelho() and semaforo_leste.esta_vermelho():
                    # Alterna entre os semáforos
                    if semaforo_norte.temporizador > semaforo_leste.temporizador:
                        semaforo_leste.definir_estado(EstadoSemaforo.VERDE)
                    else:
                        semaforo_norte.definir_estado(EstadoSemaforo.VERDE)
            return
        
        # Estados anteriores para detectar mudanças
        estado_anterior_norte = semaforo_norte.estado
        estado_anterior_leste = semaforo_leste.estado
        
        # Atualizamos o semáforo Norte e verificamos mudanças
        semaforo_norte.atualizar()
        
        # Se o semáforo Norte mudou para amarelo, não fazemos nada (ele vai para vermelho naturalmente)
        if estado_anterior_norte != semaforo_norte.estado:
            if semaforo_norte.esta_amarelo():
                # Garantir que Leste está vermelho enquanto Norte está amarelo
                if not semaforo_leste.esta_vermelho():
                    semaforo_leste.definir_estado(EstadoSemaforo.VERMELHO)
            
            # Se Norte mudou para vermelho, entramos no estado de segurança (ambos vermelhos)
            elif semaforo_norte.esta_vermelho():
                self.ambos_vermelhos = True
                self.contador_seguranca = 0
                
            # Se Norte mudou para verde, Leste deve estar vermelho
            elif semaforo_norte.esta_verde():
                semaforo_leste.definir_estado(EstadoSemaforo.VERMELHO)
        
        # Atualizamos o semáforo Leste e verificamos mudanças
        semaforo_leste.atualizar()
        
        # Se o semáforo Leste mudou para amarelo, não fazemos nada (ele vai para vermelho naturalmente)
        if estado_anterior_leste != semaforo_leste.estado:
            if semaforo_leste.esta_amarelo():
                # Garantir que Norte está vermelho enquanto Leste está amarelo
                if not semaforo_norte.esta_vermelho():
                    semaforo_norte.definir_estado(EstadoSemaforo.VERMELHO)
            
            # Se Leste mudou para vermelho, entramos no estado de segurança (ambos vermelhos)
            elif semaforo_leste.esta_vermelho():
                self.ambos_vermelhos = True
                self.contador_seguranca = 0
                
            # Se Leste mudou para verde, Norte deve estar vermelho
            elif semaforo_leste.esta_verde():
                semaforo_norte.definir_estado(EstadoSemaforo.VERMELHO)
    
    def obter_semaforo(self, direcao: Direcao) -> Optional[Semaforo]:
        """
        Retorna o semáforo para a direção especificada.
        
        Args:
            direcao: A direção do semáforo desejado
            
        Returns:
            O objeto semáforo ou None se não existir
        """
        return self.semaforos.get(direcao)
    
    def desenhar(self, tela: pygame.Surface) -> None:
        """
        Desenha todos os semáforos.
        
        Args:
            tela: Superfície Pygame para desenhar
        """
        for semaforo in self.semaforos.values():
            semaforo.desenhar(tela)


class GerenciadorSemaforos:
    """Gerencia todos os controladores de semáforos da malha viária."""
    
    def __init__(self):
        """Inicializa o gerenciador de semáforos."""
        self.controladores: Dict[Tuple[int, int], ControladorSemaforo] = {}
    
    def adicionar_controlador(self, id_cruzamento: Tuple[int, int], controlador: ControladorSemaforo) -> None:
        """
        Adiciona um controlador de semáforos ao gerenciador.
        
        Args:
            id_cruzamento: Identificador (linha, coluna) do cruzamento
            controlador: O controlador de semáforos
        """
        self.controladores[id_cruzamento] = controlador
    
    def obter_controlador(self, id_cruzamento: Tuple[int, int]) -> Optional[ControladorSemaforo]:
        """
        Retorna o controlador de semáforos para o cruzamento especificado.
        
        Args:
            id_cruzamento: Identificador (linha, coluna) do cruzamento
            
        Returns:
            O controlador de semáforos ou None se não existir
        """
        return self.controladores.get(id_cruzamento)
    
    def atualizar(self) -> None:
        """Atualiza todos os controladores de semáforos."""
        for controlador in self.controladores.values():
            controlador.atualizar()
    
    def desenhar(self, tela: pygame.Surface) -> None:
        """
        Desenha todos os semáforos de todos os controladores.
        
        Args:
            tela: Superfície Pygame para desenhar
        """
        for controlador in self.controladores.values():
            controlador.desenhar(tela)