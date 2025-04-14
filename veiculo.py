"""
Módulo de veículos para a simulação de malha viária com múltiplos cruzamentos.
"""
import random
from typing import Optional, Tuple, List, Dict
import pygame
from configuracao import CONFIG, Direcao
from semaforo import Semaforo


class Veiculo:
    """Representa um veículo na simulação."""
    
    def __init__(self, direcao: Direcao, posicao: Tuple[int, int], id_via: Tuple[int, int] = None):
        """
        Inicializa um veículo.
        
        Args:
            direcao: Direção do veículo (NORTE, LESTE)
            posicao: Posição inicial (x, y) do veículo
            id_via: Identificador (linha, coluna) da via atual do veículo
        """
        self.direcao = direcao
        self.posicao = list(posicao)
        self.id_via = id_via  # Identificador da via atual (linha, coluna)
        self.cor = random.choice(CONFIG.CORES_VEICULO)
        self.ativo = True
        
        # Dimensões do veículo
        self.largura = CONFIG.LARGURA_VEICULO
        self.altura = CONFIG.ALTURA_VEICULO
        
        # Variáveis para movimento e física
        self.velocidade = CONFIG.VELOCIDADE_VEICULO
        self.velocidade_alvo = CONFIG.VELOCIDADE_VEICULO
        self.velocidade_maxima = CONFIG.VELOCIDADE_MAX_VEICULO
        self.aceleracao = CONFIG.ACELERACAO_VEICULO
        self.desaceleracao = CONFIG.DESACELERACAO_VEICULO
        
        # Estado do veículo
        self.parado = False
        self.no_cruzamento = False
        self.passou_cruzamento = False
        
        # Calcular a rotação com base na direção (NORTE = para baixo, LESTE = para direita)
        self.rotacao = 90 if direcao == Direcao.NORTE else 0
        
        # Retângulo para colisão
        self.rect = pygame.Rect(
            self.posicao[0] - self.largura // 2,
            self.posicao[1] - self.altura // 2,
            self.largura,
            self.altura
        )
        if self.direcao == Direcao.NORTE:
            self.rect.width, self.rect.height = self.rect.height, self.rect.width
        
        # Propriedades para navegação em múltiplos cruzamentos
        self.cruzamento_atual = None
        self.cruzamento_destino = None
        self._velocidade_alvo_semaforo = CONFIG.VELOCIDADE_VEICULO
        
        # Controle de estado para respeitar semáforos
        self.aguardando_semaforo = False
        self.semaforo_anterior = None
    
    def atualizar(self, semaforo: Optional[Semaforo] = None, veiculos_frente: List['Veiculo'] = None,
                  limites_cruzamento: Optional[Dict[str, int]] = None) -> None:
        """
        Atualiza a posição do veículo com base na sua direção e nas condições de tráfego.
        
        Args:
            semaforo: Semáforo que controla a direção deste veículo
            veiculos_frente: Lista de veículos à frente deste na mesma direção
            limites_cruzamento: Dicionário com os limites do cruzamento atual
        """
        # Verificar semáforo e ajustar velocidade - PRIORIDADE MÁXIMA
        if semaforo:
            self._responder_ao_semaforo(semaforo, limites_cruzamento)
        
        # Verificar veículos à frente e evitar colisões
        if veiculos_frente:
            self._evitar_colisoes(veiculos_frente)
        
        # Ajustar velocidade gradualmente (aceleração/frenagem)
        if self.velocidade < self.velocidade_alvo:
            self.velocidade = min(self.velocidade + self.aceleracao, self.velocidade_alvo)
        elif self.velocidade > self.velocidade_alvo:
            self.velocidade = max(self.velocidade - self.desaceleracao, self.velocidade_alvo)
        
        # Atualiza o estado "parado" com base na velocidade atual
        self.parado = self.velocidade < 0.1
        
        # Movimento baseado na direção
        if self.direcao == Direcao.NORTE:
            self.posicao[1] += self.velocidade  # De cima para baixo (↓)
        elif self.direcao == Direcao.LESTE:
            self.posicao[0] += self.velocidade  # Da esquerda para direita (→)
            
        # Atualiza o retângulo de colisão
        self._atualizar_rect_colisao()
            
        # Verifica se o veículo está fora dos limites
        if (self.posicao[0] < -self.largura or 
            self.posicao[0] > CONFIG.LARGURA_TELA + self.largura or
            self.posicao[1] < -self.altura or 
            self.posicao[1] > CONFIG.ALTURA_TELA + self.altura):
            self.ativo = False
            
        # Atualiza o estado de interseção
        if limites_cruzamento:
            self._atualizar_estado_cruzamento(limites_cruzamento)
    
    def _atualizar_estado_cruzamento(self, limites: Dict[str, int]) -> None:
        """
        Atualiza o estado de interseção do veículo.
        
        Args:
            limites: Dicionário com os limites do cruzamento
        """
        # Verifica a posição anterior
        estava_no_cruzamento = self.no_cruzamento
        
        # Determinar se o veículo está no cruzamento
        no_cruzamento_x = limites['esquerda'] <= self.posicao[0] <= limites['direita']
        no_cruzamento_y = limites['topo'] <= self.posicao[1] <= limites['base']
        
        self.no_cruzamento = no_cruzamento_x and no_cruzamento_y
        
        # Se acabamos de sair do cruzamento, registra que passamos por ele
        if estava_no_cruzamento and not self.no_cruzamento:
            self.passou_cruzamento = True
            # Resetamos a flag de aguardando semáforo quando saímos do cruzamento
            self.aguardando_semaforo = False
        
    def _atualizar_rect_colisao(self) -> None:
        """Atualiza a posição do retângulo de colisão com base na posição do veículo."""
        if self.direcao == Direcao.NORTE:
            self.rect.centerx = self.posicao[0]
            self.rect.centery = self.posicao[1]
        else:  # Direcao.LESTE
            self.rect.centerx = self.posicao[0]
            self.rect.centery = self.posicao[1]
    
    def _evitar_colisoes(self, veiculos_frente: List['Veiculo']) -> None:
        """
        Ajusta a velocidade para evitar colisões com veículos à frente.
        
        Args:
            veiculos_frente: Lista de veículos à frente deste na mesma direção
        """
        distancia_minima = float('inf')
        veiculo_mais_proximo = None
        
        for veiculo in veiculos_frente:
            distancia = self._calcular_distancia_para_veiculo(veiculo)
            if distancia < distancia_minima:
                distancia_minima = distancia
                veiculo_mais_proximo = veiculo
        
        # Ajustar velocidade com base na distância
        if distancia_minima < CONFIG.DISTANCIA_MIN_VEICULO and veiculo_mais_proximo:
            # Quanto mais perto, mais reduzimos a velocidade
            fator_reducao = min(1.0, distancia_minima / CONFIG.DISTANCIA_MIN_VEICULO)
            velocidade_segura = veiculo_mais_proximo.velocidade * fator_reducao
            
            # Limita a velocidade alvo pelo menor valor entre a velocidade segura e a velocidade alvo do semáforo
            self.velocidade_alvo = min(velocidade_segura, self._velocidade_alvo_semaforo)
            
            # Parar completamente se estiver muito perto
            if distancia_minima < CONFIG.DISTANCIA_MIN_VEICULO / 2:
                self.velocidade_alvo = 0
        else:
            # Se não há veículos próximos, a velocidade é determinada pelo semáforo
            self.velocidade_alvo = self._velocidade_alvo_semaforo
    
    def _calcular_distancia_para_veiculo(self, outro_veiculo: 'Veiculo') -> float:
        """
        Calcula a distância entre este veículo e outro na mesma direção.
        
        Args:
            outro_veiculo: O outro veículo
            
        Returns:
            float: Distância entre os veículos
        """
        if self.direcao == Direcao.NORTE:
            # Só nos importamos com veículos à frente (y maior, já que vamos de cima para baixo)
            if outro_veiculo.posicao[1] > self.posicao[1] and abs(outro_veiculo.posicao[0] - self.posicao[0]) < self.largura:
                return outro_veiculo.posicao[1] - self.posicao[1] - self.altura
        elif self.direcao == Direcao.LESTE:
            # Só nos importamos com veículos à frente (x maior)
            if outro_veiculo.posicao[0] > self.posicao[0] and abs(outro_veiculo.posicao[1] - self.posicao[1]) < self.altura:
                return outro_veiculo.posicao[0] - self.posicao[0] - self.largura
                
        return float('inf')  # Retorna "infinito" se não estiver na frente
    
    def _responder_ao_semaforo(self, semaforo: Semaforo, limites_cruzamento: Optional[Dict[str, int]] = None) -> None:
        """
        Ajusta o comportamento do veículo com base no semáforo.
        
        Args:
            semaforo: Semáforo relevante para este veículo
            limites_cruzamento: Dicionário com os limites do cruzamento
        """
        if not limites_cruzamento:
            return
        
        # Atualiza o semáforo anterior para controle
        if self.semaforo_anterior != semaforo:
            self.semaforo_anterior = semaforo
            self.aguardando_semaforo = False
            
        # Calcular a distância até o cruzamento
        distancia_ate_cruzamento = self._calcular_distancia_ate_cruzamento(limites_cruzamento)
        
        # Se estamos muito longe do cruzamento, não nos preocupamos com o semáforo
        if distancia_ate_cruzamento > CONFIG.DISTANCIA_DETECCAO_SEMAFORO and not self.no_cruzamento:
            self._velocidade_alvo_semaforo = CONFIG.VELOCIDADE_VEICULO
            self.aguardando_semaforo = False
            return
        
        # Se já estamos no cruzamento e o semáforo não está vermelho, continuamos
        if self.no_cruzamento and not semaforo.esta_vermelho():
            self._velocidade_alvo_semaforo = CONFIG.VELOCIDADE_VEICULO
            self.aguardando_semaforo = False
            return
        
        # Se já passamos pelo cruzamento, não precisamos verificar o semáforo
        if self.passou_cruzamento:
            self._velocidade_alvo_semaforo = CONFIG.VELOCIDADE_VEICULO
            self.aguardando_semaforo = False
            return
            
        # Reagir ao estado do semáforo
        if semaforo.esta_vermelho():
            # Parar completamente antes do cruzamento
            if distancia_ate_cruzamento < 50:
                self._velocidade_alvo_semaforo = 0
                self.aguardando_semaforo = True
            else:
                # Desacelerar gradualmente
                fator_parada = max(0, 1.0 - (distancia_ate_cruzamento / CONFIG.DISTANCIA_DETECCAO_SEMAFORO))
                self._velocidade_alvo_semaforo = CONFIG.VELOCIDADE_VEICULO * (1 - fator_parada * 2.0)
        
        elif semaforo.esta_amarelo():
            # Decisão baseada na distância
            if distancia_ate_cruzamento < 30:
                # Muito próximo, continua
                self._velocidade_alvo_semaforo = CONFIG.VELOCIDADE_VEICULO
            elif distancia_ate_cruzamento < 80:
                # Distância média, desacelera
                self._velocidade_alvo_semaforo = CONFIG.VELOCIDADE_VEICULO * 0.5
            else:
                # Distância suficiente para parar
                self._velocidade_alvo_semaforo = 0
                self.aguardando_semaforo = True
        
        else:  # VERDE
            # Semáforo verde, prosseguir normalmente
            self._velocidade_alvo_semaforo = CONFIG.VELOCIDADE_VEICULO
            self.aguardando_semaforo = False
    
    def _calcular_distancia_ate_cruzamento(self, limites: Dict[str, int]) -> float:
        """
        Calcula a distância do veículo até o cruzamento.
        
        Args:
            limites: Dicionário com os limites do cruzamento
            
        Returns:
            float: Distância até o cruzamento
        """
        if self.direcao == Direcao.NORTE:
            # Para veículos que se movem de cima para baixo
            if self.posicao[1] < limites['topo']:
                # Se estamos antes do cruzamento
                return limites['topo'] - self.posicao[1]
            elif self.posicao[1] <= limites['base']:
                # Se estamos no cruzamento
                return 0
            else:
                # Se já passamos do cruzamento
                return float('inf')
                
        elif self.direcao == Direcao.LESTE:
            # Para veículos que se movem da esquerda para direita
            if self.posicao[0] < limites['esquerda']:
                # Se estamos antes do cruzamento
                return limites['esquerda'] - self.posicao[0]
            elif self.posicao[0] <= limites['direita']:
                # Se estamos no cruzamento
                return 0
            else:
                # Se já passamos do cruzamento
                return float('inf')
                
        return float('inf')
    
    def desenhar(self, tela: pygame.Surface) -> None:
        """
        Desenha o veículo na tela.
        
        Args:
            tela: Superfície Pygame para desenhar
        """
        # Criar uma superfície para o veículo
        superficie = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
        
        # Desenhar o formato do veículo
        pygame.draw.rect(superficie, self.cor, (0, 0, self.largura, self.altura), 0, 3)
        
        # Adicionar janelas
        cor_janela = (200, 220, 255)  # Azul claro para janelas
        margem_janela = 3
        largura_janela = self.largura * 0.7
        altura_janela = self.altura * 0.4
        x_janela = (self.largura - largura_janela) / 2
        y_janela = margem_janela
        
        pygame.draw.rect(
            superficie, 
            cor_janela, 
            (x_janela, y_janela, largura_janela, altura_janela),
            0, 
            2
        )
        
        # Rotacionar o veículo com base na direção
        superficie_rotacionada = pygame.transform.rotate(superficie, self.rotacao)
        
        # Obter o retângulo rotacionado
        rect_rotacionado = superficie_rotacionada.get_rect(center=(self.posicao[0], self.posicao[1]))
        
        # Desenhar na tela
        tela.blit(superficie_rotacionada, rect_rotacionado.topleft)
        
        # Debug: desenhar um ponto no centro e o retângulo de colisão
        if CONFIG.MODO_DEBUG:
            pygame.draw.circle(tela, (255, 255, 255), (int(self.posicao[0]), int(self.posicao[1])), 2)
            pygame.draw.rect(tela, (255, 255, 255), self.rect, 1)
            
            # Mostrar estado do veículo
            if self.parado:
                # Desenha um ícone de parado
                pygame.draw.rect(tela, (255, 0, 0), (int(self.posicao[0]) - 5, int(self.posicao[1]) - 5, 10, 10), 2)
            
            # Mostrar estado de espera por semáforo
            if self.aguardando_semaforo:
                pygame.draw.circle(tela, (255, 255, 0), (int(self.posicao[0]), int(self.posicao[1]) - 15), 5)