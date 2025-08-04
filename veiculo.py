"""
Módulo de veículos para a simulação de malha viária com múltiplos cruzamentos.
"""
import random
import math
from typing import Optional, Tuple, List, Dict
import pygame
from configuracao import CONFIG, Direcao, EstadoSemaforo
from semaforo import Semaforo


class Veiculo:
    """Representa um veículo na simulação com física e comportamento realista."""
    
    # Contador estático para IDs únicos
    _contador_id = 0
    
    def __init__(self, direcao: Direcao, posicao: Tuple[float, float], id_cruzamento_origem: Tuple[int, int]):
        """
        Inicializa um veículo.
        
        Args:
            direcao: Direção do veículo
            posicao: Posição inicial (x, y) do veículo
            id_cruzamento_origem: ID do cruzamento onde o veículo foi gerado
        """
        # ID único para o veículo
        Veiculo._contador_id += 1
        self.id = Veiculo._contador_id
        
        # Propriedades básicas
        self.direcao = direcao
        self.posicao = list(posicao)
        self.posicao_inicial = list(posicao)
        self.id_cruzamento_origem = id_cruzamento_origem
        self.id_cruzamento_atual = id_cruzamento_origem
        self.cor = random.choice(CONFIG.CORES_VEICULO)
        self.ativo = True
        
        # Dimensões
        self.largura = CONFIG.LARGURA_VEICULO
        self.altura = CONFIG.ALTURA_VEICULO
        
        # Física e movimento
        self.velocidade = 0.0
        self.velocidade_desejada = CONFIG.VELOCIDADE_VEICULO
        self.aceleracao_atual = 0.0
        
        # Estados
        self.parado = True
        self.no_cruzamento = False
        self.passou_semaforo = False
        self.aguardando_semaforo = False
        self.em_desaceleracao = False
        
        # Controle de semáforo
        self.semaforo_proximo = None
        self.distancia_semaforo = float('inf')
        self.pode_passar_amarelo = False
        
        # Métricas
        self.tempo_viagem = 0
        self.tempo_parado = 0
        self.paradas_totais = 0
        self.distancia_percorrida = 0.0
        
        # Retângulo de colisão
        self._atualizar_rect()
    
    def _atualizar_rect(self) -> None:
        """Atualiza o retângulo de colisão do veículo."""
        if self.direcao in [Direcao.NORTE, Direcao.SUL]:
            # Veículos verticais
            self.rect = pygame.Rect(
                self.posicao[0] - self.largura // 2,
                self.posicao[1] - self.altura // 2,
                self.largura,
                self.altura
            )
        else:
            # Veículos horizontais
            self.rect = pygame.Rect(
                self.posicao[0] - self.altura // 2,
                self.posicao[1] - self.largura // 2,
                self.altura,
                self.largura
            )
    
    def atualizar(self, dt: float = 1.0) -> None:
        """
        Atualiza o estado do veículo.
        
        Args:
            dt: Delta time para cálculos de física
        """
        # Atualiza métricas
        self.tempo_viagem += dt
        if self.velocidade < 0.1:
            self.tempo_parado += dt
            if not self.parado:
                self.paradas_totais += 1
            self.parado = True
        else:
            self.parado = False
        
        # Aplica aceleração
        self.velocidade += self.aceleracao_atual * dt
        self.velocidade = max(CONFIG.VELOCIDADE_MIN_VEICULO, 
                            min(CONFIG.VELOCIDADE_MAX_VEICULO, self.velocidade))
        
        # Move o veículo
        dx, dy = 0, 0
        if self.direcao == Direcao.NORTE:
            dy = self.velocidade
        elif self.direcao == Direcao.SUL:
            dy = -self.velocidade
        elif self.direcao == Direcao.LESTE:
            dx = self.velocidade
        elif self.direcao == Direcao.OESTE:
            dx = -self.velocidade
        
        self.posicao[0] += dx
        self.posicao[1] += dy
        self.distancia_percorrida += math.sqrt(dx**2 + dy**2)
        
        # Atualiza retângulo de colisão
        self._atualizar_rect()
        
        # Verifica se saiu da tela
        margem = 100
        if (self.posicao[0] < -margem or 
            self.posicao[0] > CONFIG.LARGURA_TELA + margem or
            self.posicao[1] < -margem or 
            self.posicao[1] > CONFIG.ALTURA_TELA + margem):
            self.ativo = False

    def processar_semaforo(self, semaforo: Semaforo, posicao_parada: Tuple[float, float]) -> None:
        """
        Processa a reação do veículo ao semáforo.

        Args:
            semaforo: Semáforo a ser processado
            posicao_parada: Posição onde o veículo deve parar
        """
        if not semaforo or self.passou_semaforo:
            # Sem semáforo ou já passou, acelera normalmente
            self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        # Calcula distância até a linha de parada
        self.distancia_semaforo = self._calcular_distancia_ate_ponto(posicao_parada)

        # Se já passou da linha de parada, ignora o semáforo
        if self._passou_da_linha(posicao_parada):
            self.passou_semaforo = True
            self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        # Lógica baseada no estado do semáforo
        if semaforo.estado == EstadoSemaforo.VERDE:
            # Semáforo verde: acelera normalmente
            self.aguardando_semaforo = False
            self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO

        elif semaforo.estado == EstadoSemaforo.AMARELO:
            # Semáforo amarelo: decide se passa ou freia de emergência
            tempo_ate_linha = self.distancia_semaforo / max(self.velocidade, 0.1)
            tempo_ate_parar = self.velocidade / CONFIG.DESACELERACAO_EMERGENCIA
            if tempo_ate_linha < 1.0 and self.velocidade > CONFIG.VELOCIDADE_VEICULO * 0.7:
                # Perto demais e rápido demais: mantém velocidade para não parar no meio
                self.pode_passar_amarelo = True
                self.aceleracao_atual = 0
            else:
                # Freia para parar antes da linha
                self._aplicar_frenagem_para_parada(self.distancia_semaforo)

        elif semaforo.estado == EstadoSemaforo.VERMELHO:
            # Semáforo vermelho: para completamente ao chegar na linha
            self.aguardando_semaforo = True
            # Se estiver dentro da zona de parada, zera velocidade imediatamente
            if self.distancia_semaforo <= CONFIG.DISTANCIA_PARADA_SEMAFORO:
                self.velocidade = 0.0
                self.aceleracao_atual = 0.0
            else:
                # Senão, freia suavemente para atingir exatamente 0 na linha
                self._aplicar_frenagem_para_parada(self.distancia_semaforo)

    def processar_veiculo_frente(self, veiculo_frente: 'Veiculo') -> None:
        """
        Processa a reação a um veículo à frente.
        
        Args:
            veiculo_frente: Veículo detectado à frente
        """
        if not veiculo_frente:
            return
        
        distancia = self._calcular_distancia_para_veiculo(veiculo_frente)
        
        if distancia < CONFIG.DISTANCIA_REACAO:
            # Calcula velocidade segura baseada na distância
            velocidade_segura = self._calcular_velocidade_segura(distancia, veiculo_frente.velocidade)
            
            if self.velocidade > velocidade_segura:
                # Precisa frear
                if distancia < CONFIG.DISTANCIA_MIN_VEICULO:
                    self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
                else:
                    self.aceleracao_atual = -CONFIG.DESACELERACAO_VEICULO
            elif self.velocidade < velocidade_segura * 0.9:
                # Pode acelerar um pouco
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO * 0.5
            else:
                # Manter velocidade
                self.aceleracao_atual = 0
    
    def _calcular_distancia_ate_ponto(self, ponto: Tuple[float, float]) -> float:
        """Calcula a distância até um ponto específico."""
        if self.direcao == Direcao.NORTE:
            return max(0, ponto[1] - self.posicao[1])
        elif self.direcao == Direcao.SUL:
            return max(0, self.posicao[1] - ponto[1])
        elif self.direcao == Direcao.LESTE:
            return max(0, ponto[0] - self.posicao[0])
        elif self.direcao == Direcao.OESTE:
            return max(0, self.posicao[0] - ponto[0])
        return float('inf')
    
    def _passou_da_linha(self, ponto: Tuple[float, float]) -> bool:
        """Verifica se o veículo já passou de um ponto."""
        margem = 10
        if self.direcao == Direcao.NORTE:
            return self.posicao[1] > ponto[1] + margem
        elif self.direcao == Direcao.SUL:
            return self.posicao[1] < ponto[1] - margem
        elif self.direcao == Direcao.LESTE:
            return self.posicao[0] > ponto[0] + margem
        elif self.direcao == Direcao.OESTE:
            return self.posicao[0] < ponto[0] - margem
        return False
    
    def _calcular_distancia_para_veiculo(self, outro: 'Veiculo') -> float:
        """Calcula a distância até outro veículo considerando as dimensões."""
        # Verifica se estão na mesma faixa
        if not self._mesma_faixa(outro):
            return float('inf')
        
        # Calcula distância centro a centro
        dx = outro.posicao[0] - self.posicao[0]
        dy = outro.posicao[1] - self.posicao[1]
        
        # Ajusta pela direção e dimensões dos veículos
        if self.direcao == Direcao.NORTE:
            if dy > 0:  # Outro está à frente
                return dy - (self.altura + outro.altura) / 2
        elif self.direcao == Direcao.SUL:
            if dy < 0:  # Outro está à frente
                return -dy - (self.altura + outro.altura) / 2
        elif self.direcao == Direcao.LESTE:
            if dx > 0:  # Outro está à frente
                return dx - (self.altura + outro.altura) / 2
        elif self.direcao == Direcao.OESTE:
            if dx < 0:  # Outro está à frente
                return -dx - (self.altura + outro.altura) / 2
        
        return float('inf')
    
    def _mesma_faixa(self, outro: 'Veiculo') -> bool:
        """Verifica se dois veículos estão na mesma faixa."""
        tolerancia = CONFIG.LARGURA_FAIXA * 0.8
        
        if self.direcao in [Direcao.NORTE, Direcao.SUL]:
            return abs(self.posicao[0] - outro.posicao[0]) < tolerancia
        else:
            return abs(self.posicao[1] - outro.posicao[1]) < tolerancia
    
    def _calcular_velocidade_segura(self, distancia: float, velocidade_lider: float) -> float:
        """Calcula a velocidade segura baseada na distância e velocidade do veículo à frente."""
        if distancia < CONFIG.DISTANCIA_MIN_VEICULO:
            return 0
        
        # Modelo de car-following simplificado
        tempo_reacao = 1.0  # 1 segundo
        distancia_segura = CONFIG.DISTANCIA_SEGURANCA + velocidade_lider * tempo_reacao
        
        if distancia < distancia_segura:
            fator = distancia / distancia_segura
            return velocidade_lider * fator
        
        return CONFIG.VELOCIDADE_VEICULO
    
    def _aplicar_frenagem_para_parada(self, distancia: float) -> None:
        """Aplica frenagem suave para parar em uma distância específica."""
        if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO:
            self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
            self.velocidade_desejada = 0
        else:
            # Cálculo de desaceleração necessária: v² = v₀² + 2*a*d
            if self.velocidade > 0.1:
                desaceleracao_necessaria = (self.velocidade ** 2) / (2 * distancia)
                self.aceleracao_atual = -min(desaceleracao_necessaria, CONFIG.DESACELERACAO_VEICULO)
            else:
                self.aceleracao_atual = 0
    
    def obter_faixa(self) -> int:
        """Retorna o índice da faixa em que o veículo está."""
        if self.direcao in [Direcao.NORTE, Direcao.SUL]:
            # Faixas verticais
            faixa_esquerda = self.posicao[0] - CONFIG.LARGURA_FAIXA // 2
            faixa_direita = self.posicao[0] + CONFIG.LARGURA_FAIXA // 2
            return 0 if self.posicao[0] < (faixa_esquerda + faixa_direita) / 2 else 1
        else:
            # Faixas horizontais
            faixa_superior = self.posicao[1] - CONFIG.LARGURA_FAIXA // 2
            faixa_inferior = self.posicao[1] + CONFIG.LARGURA_FAIXA // 2
            return 0 if self.posicao[1] < (faixa_superior + faixa_inferior) / 2 else 1
    
    def desenhar(self, tela: pygame.Surface) -> None:
        """Desenha o veículo na tela com visual aprimorado."""
        # Cria superfície para o veículo
        if self.direcao in [Direcao.NORTE, Direcao.SUL]:
            superficie = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
        else:
            superficie = pygame.Surface((self.altura, self.largura), pygame.SRCALPHA)
        
        # Desenha o corpo do veículo
        pygame.draw.rect(superficie, self.cor, superficie.get_rect(), border_radius=4)
        
        # Adiciona detalhes (janelas)
        cor_janela = (200, 220, 255, 180)
        if self.direcao in [Direcao.NORTE, Direcao.SUL]:
            # Janela frontal
            pygame.draw.rect(superficie, cor_janela, 
                           (3, 3, self.largura - 6, self.altura * 0.3), 
                           border_radius=2)
            # Janela traseira
            pygame.draw.rect(superficie, cor_janela, 
                           (3, self.altura * 0.7, self.largura - 6, self.altura * 0.25), 
                           border_radius=2)
        else:
            # Janela frontal
            pygame.draw.rect(superficie, cor_janela, 
                           (3, 3, self.altura * 0.3, self.largura - 6), 
                           border_radius=2)
            # Janela traseira
            pygame.draw.rect(superficie, cor_janela, 
                           (self.altura * 0.7, 3, self.altura * 0.25, self.largura - 6), 
                           border_radius=2)
        
        # Adiciona luzes de freio se estiver freando
        if self.aceleracao_atual < -0.1:
            cor_freio = (255, 100, 100)
            if self.direcao == Direcao.NORTE:
                pygame.draw.rect(superficie, cor_freio, 
                               (2, self.altura - 4, 6, 3))
                pygame.draw.rect(superficie, cor_freio, 
                               (self.largura - 8, self.altura - 4, 6, 3))
            elif self.direcao == Direcao.SUL:
                pygame.draw.rect(superficie, cor_freio, 
                               (2, 1, 6, 3))
                pygame.draw.rect(superficie, cor_freio, 
                               (self.largura - 8, 1, 6, 3))
            elif self.direcao == Direcao.LESTE:
                pygame.draw.rect(superficie, cor_freio, 
                               (self.altura - 4, 2, 3, 6))
                pygame.draw.rect(superficie, cor_freio, 
                               (self.altura - 4, self.largura - 8, 3, 6))
            elif self.direcao == Direcao.OESTE:
                pygame.draw.rect(superficie, cor_freio, 
                               (1, 2, 3, 6))
                pygame.draw.rect(superficie, cor_freio, 
                               (1, self.largura - 8, 3, 6))
        
        # Rotaciona se necessário
        angulo = {
            Direcao.NORTE: 0,
            Direcao.SUL: 180,
            Direcao.LESTE: -90,
            Direcao.OESTE: 90
        }[self.direcao]
        
        if angulo != 0:
            superficie = pygame.transform.rotate(superficie, angulo)
        
        # Desenha na tela
        rect = superficie.get_rect(center=(int(self.posicao[0]), int(self.posicao[1])))
        tela.blit(superficie, rect)
        
        # Debug info
        if CONFIG.MOSTRAR_INFO_VEICULO:
            fonte = pygame.font.SysFont('Arial', 10)
            texto = f"V:{self.velocidade:.1f}"
            superficie_texto = fonte.render(texto, True, CONFIG.BRANCO)
            tela.blit(superficie_texto, (self.posicao[0] - 15, self.posicao[1] - 25))