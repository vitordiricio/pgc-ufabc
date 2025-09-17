"""
Módulo de veículos para a simulação de malha viária com múltiplos cruzamentos.
Sistema com vias de mão única: Horizontal (Leste→Oeste) e Vertical (Norte→Sul)
"""
import random
import math
from typing import Tuple, Optional, List
import pygame
from configuracao import CONFIG, Direcao, EstadoSemaforo
from semaforo import Semaforo


class Veiculo:
    """Representa um veículo na simulação com física e comportamento realista - MÃO ÚNICA."""
    
    # Contador estático para IDs únicos
    _contador_id = 0
    
    def __init__(self, direcao: Direcao, posicao: Tuple[float, float], id_cruzamento_origem: Tuple[int, int]):
        """
        Inicializa um veículo.
        
        Args:
            direcao: Direção do veículo (apenas NORTE ou LESTE em mão única)
            posicao: Posição inicial (x, y) do veículo
            id_cruzamento_origem: ID do cruzamento onde o veículo foi gerado
        """
        # Valida direção - apenas direções permitidas
        if direcao not in CONFIG.DIRECOES_PERMITIDAS:
            raise ValueError(f"Direção {direcao} não permitida. Use apenas {CONFIG.DIRECOES_PERMITIDAS}")
        
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
        
        # Controle de semáforo - MELHORADO
        self.semaforo_proximo = None
        self.ultimo_semaforo_processado = None
        self.distancia_semaforo = float('inf')
        self.pode_passar_amarelo = False
        
        # Controle de colisão
        self.veiculo_frente = None
        self.distancia_veiculo_frente = float('inf')
        
        # Métricas
        self.tempo_viagem = 0
        self.tempo_parado = 0
        self.paradas_totais = 0
        self.distancia_percorrida = 0.0
        
        # Retângulo de colisão
        self._atualizar_rect()
    
    def _atualizar_rect(self) -> None:
        """Atualiza o retângulo de colisão do veículo."""
        if self.direcao == Direcao.NORTE:
            # Veículo vertical (Norte→Sul)
            self.rect = pygame.Rect(
                self.posicao[0] - self.largura // 2,
                self.posicao[1] - self.altura // 2,
                self.largura,
                self.altura
            )
        elif self.direcao == Direcao.LESTE:
            # Veículo horizontal (Leste→Oeste)
            self.rect = pygame.Rect(
                self.posicao[0] - self.altura // 2,
                self.posicao[1] - self.largura // 2,
                self.altura,
                self.largura
            )
    
    def resetar_controle_semaforo(self, novo_cruzamento_id: Optional[Tuple[int, int]] = None) -> None:
        """
        Reseta o controle de semáforo quando o veículo muda de cruzamento.
        
        Args:
            novo_cruzamento_id: ID do novo cruzamento (opcional)
        """
        if novo_cruzamento_id and novo_cruzamento_id != self.id_cruzamento_atual:
            self.id_cruzamento_atual = novo_cruzamento_id
            self.passou_semaforo = False
            self.aguardando_semaforo = False
            self.pode_passar_amarelo = False
            self.semaforo_proximo = None
            self.distancia_semaforo = float('inf')
    
    def verificar_colisao_futura(self, todos_veiculos: List['Veiculo']) -> bool:
        """
        Verifica se haverá colisão se o veículo continuar se movendo.
        
        Args:
            todos_veiculos: Lista de todos os veículos na simulação
            
        Returns:
            True se uma colisão é iminente
        """
        # Calcula posição futura
        dx, dy = 0, 0
        if self.direcao == Direcao.NORTE:
            dy = self.velocidade + CONFIG.DISTANCIA_MIN_VEICULO / 2
        elif self.direcao == Direcao.LESTE:
            dx = self.velocidade + CONFIG.DISTANCIA_MIN_VEICULO / 2
        
        posicao_futura = [self.posicao[0] + dx, self.posicao[1] + dy]
        
        # Cria retângulo futuro
        if self.direcao == Direcao.NORTE:
            rect_futuro = pygame.Rect(
                posicao_futura[0] - self.largura // 2,
                posicao_futura[1] - self.altura // 2,
                self.largura,
                self.altura
            )
        else:
            rect_futuro = pygame.Rect(
                posicao_futura[0] - self.altura // 2,
                posicao_futura[1] - self.largura // 2,
                self.altura,
                self.largura
            )
        
        # Verifica colisão com outros veículos
        for outro in todos_veiculos:
            if outro.id == self.id or not outro.ativo:
                continue
            
            # Só verifica veículos na mesma via
            if not self._mesma_via(outro):
                continue
            
            # Expande o retângulo do outro veículo para margem de segurança
            rect_outro_expandido = outro.rect.inflate(10, 10)
            
            if rect_futuro.colliderect(rect_outro_expandido):
                return True
        
        return False
    
    def processar_todos_veiculos(self, todos_veiculos: List['Veiculo']) -> None:
        """
        Processa interação com todos os veículos, não apenas os do cruzamento atual.
        
        Args:
            todos_veiculos: Lista de todos os veículos na simulação
        """
        veiculo_mais_proximo = None
        distancia_minima = float('inf')
        
        for outro in todos_veiculos:
            if outro.id == self.id or not outro.ativo:
                continue
            
            # Verifica se estão na mesma via e direção
            if self.direcao != outro.direcao or not self._mesma_via(outro):
                continue
            
            # Verifica se o outro está à frente
            if self.direcao == Direcao.NORTE:
                if outro.posicao[1] > self.posicao[1]:  # Outro está à frente (mais para baixo)
                    distancia = outro.posicao[1] - self.posicao[1]
                    if distancia < distancia_minima:
                        distancia_minima = distancia
                        veiculo_mais_proximo = outro
            elif self.direcao == Direcao.LESTE:
                if outro.posicao[0] > self.posicao[0]:  # Outro está à frente (mais para direita)
                    distancia = outro.posicao[0] - self.posicao[0]
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
            if not self.aguardando_semaforo:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO

    # troque a assinatura atual por esta
    def atualizar(self, dt: float = 1.0, todos_veiculos: List['Veiculo'] = None, malha=None) -> None:
        """
        Atualiza o estado do veículo.

        Args:
            dt: Delta time para cálculos de física
            todos_veiculos: Lista de todos os veículos para verificação de colisão
            malha: MalhaViaria para aplicar o fator de 'caos' (limite local de velocidade)
        """
        # métricas (igual ao seu)
        self.tempo_viagem += dt
        if self.velocidade < 0.1:
            self.tempo_parado += dt
            if not self.parado:
                self.paradas_totais += 1
            self.parado = True
        else:
            self.parado = False

        # aplica aceleração
        self.velocidade += self.aceleracao_atual * dt

        # >>> limite de velocidade com fator local (CAOS)
        fator = malha.obter_fator_caos(self) if malha is not None else 1.0
        vmax_local = CONFIG.VELOCIDADE_MAX_VEICULO * fator
        self.velocidade = max(CONFIG.VELOCIDADE_MIN_VEICULO, min(vmax_local, self.velocidade))

        # colisão futura (igual ao seu)
        if todos_veiculos and self.velocidade > 0:
            if self.verificar_colisao_futura(todos_veiculos):
                self.velocidade = 0
                self.aceleracao_atual = 0
                self._atualizar_rect()
                return

        # movimento (igual ao seu)
        dx, dy = 0, 0
        if self.direcao == Direcao.NORTE:
            dy = self.velocidade
        elif self.direcao == Direcao.LESTE:
            dx = self.velocidade

        self.posicao[0] += dx
        self.posicao[1] += dy
        self.distancia_percorrida += math.sqrt(dx ** 2 + dy ** 2)

        self._atualizar_rect()

        # saída da tela (igual ao seu)
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
        if not semaforo:
            # Sem semáforo, acelera normalmente (se não houver veículo à frente)
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        # Verifica se é um novo semáforo
        if self.ultimo_semaforo_processado != semaforo:
            self.passou_semaforo = False
            self.ultimo_semaforo_processado = semaforo
            self.pode_passar_amarelo = False

        # Se já passou deste semáforo específico, ignora
        if self.passou_semaforo:
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        # Calcula distância até a linha de parada
        self.distancia_semaforo = self._calcular_distancia_ate_ponto(posicao_parada)

        # Se já passou da linha de parada, marca como passado
        if self._passou_da_linha(posicao_parada):
            self.passou_semaforo = True
            self.aguardando_semaforo = False
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        # Lógica baseada no estado do semáforo
        if semaforo.estado == EstadoSemaforo.VERDE:
            # Semáforo verde: acelera normalmente (se não houver veículo à frente)
            self.aguardando_semaforo = False
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO

        elif semaforo.estado == EstadoSemaforo.AMARELO:
            # Semáforo amarelo: decide se passa ou freia
            if self.pode_passar_amarelo:
                # Já tinha decidido passar, mantém
                self.aceleracao_atual = 0
            else:
                # Avalia se pode passar
                tempo_ate_linha = self.distancia_semaforo / max(self.velocidade, 0.1)
                
                # Só passa se estiver muito próximo E em velocidade suficiente
                if (tempo_ate_linha < 1.0 and 
                    self.velocidade > CONFIG.VELOCIDADE_VEICULO * 0.7 and 
                    self.distancia_semaforo < CONFIG.DISTANCIA_PARADA_SEMAFORO * 3):
                    # Perto demais para parar com segurança
                    self.pode_passar_amarelo = True
                    self.aceleracao_atual = 0
                else:
                    # Tem tempo para parar com segurança
                    self._aplicar_frenagem_para_parada(self.distancia_semaforo)
                    self.aguardando_semaforo = True

        elif semaforo.estado == EstadoSemaforo.VERMELHO:
            # Semáforo vermelho: SEMPRE para
            self.aguardando_semaforo = True
            self.pode_passar_amarelo = False
            
            if self.distancia_semaforo <= CONFIG.DISTANCIA_PARADA_SEMAFORO:
                # Muito próximo da linha, para imediatamente
                self.velocidade = 0.0
                self.aceleracao_atual = 0.0
            else:
                # Aplica frenagem para parar antes da linha
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
        
        # Força parada se muito próximo
        if distancia < CONFIG.DISTANCIA_MIN_VEICULO:
            self.velocidade = 0
            self.aceleracao_atual = 0
            return
        
        if distancia < CONFIG.DISTANCIA_REACAO:
            # Calcula velocidade segura baseada na distância
            velocidade_segura = self._calcular_velocidade_segura(distancia, veiculo_frente.velocidade)
            
            if self.velocidade > velocidade_segura:
                # Precisa frear
                if distancia < CONFIG.DISTANCIA_MIN_VEICULO * 1.5:
                    self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
                else:
                    self.aceleracao_atual = -CONFIG.DESACELERACAO_VEICULO
            elif self.velocidade < velocidade_segura * 0.9:
                # Pode acelerar um pouco
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO * 0.3
            else:
                # Manter velocidade
                self.aceleracao_atual = 0
        else:
            # Distância segura, pode acelerar se não estiver aguardando semáforo
            if not self.aguardando_semaforo:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
    
    def _calcular_distancia_ate_ponto(self, ponto: Tuple[float, float]) -> float:
        """Calcula a distância até um ponto específico - MÃO ÚNICA."""
        if self.direcao == Direcao.NORTE:
            # Norte→Sul: distância é diferença em Y (positiva)
            return max(0, ponto[1] - self.posicao[1])
        elif self.direcao == Direcao.LESTE:
            # Leste→Oeste: distância é diferença em X (positiva)
            return max(0, ponto[0] - self.posicao[0])
        return float('inf')
    
    def _passou_da_linha(self, ponto: Tuple[float, float]) -> bool:
        """Verifica se o veículo já passou de um ponto - MÃO ÚNICA."""
        margem = 5
        if self.direcao == Direcao.NORTE:
            # Norte→Sul: passou se Y atual > Y do ponto
            return self.posicao[1] > ponto[1] + margem
        elif self.direcao == Direcao.LESTE:
            # Leste→Oeste: passou se X atual > X do ponto
            return self.posicao[0] > ponto[0] + margem
        return False
    
    def _calcular_distancia_para_veiculo(self, outro: 'Veiculo') -> float:
        """Calcula a distância até outro veículo - MÃO ÚNICA."""
        # Em vias de mão única, todos os veículos na mesma via vão na mesma direção
        if self.direcao != outro.direcao:
            return float('inf')
        
        # Verifica se estão na mesma via
        if not self._mesma_via(outro):
            return float('inf')
        
        # Calcula distância centro a centro
        dx = outro.posicao[0] - self.posicao[0]
        dy = outro.posicao[1] - self.posicao[1]
        
        # Ajusta pela direção e dimensões dos veículos
        if self.direcao == Direcao.NORTE:
            if dy > 0:  # Outro está à frente
                return max(0, dy - (self.altura + outro.altura) / 2)
        elif self.direcao == Direcao.LESTE:
            if dx > 0:  # Outro está à frente
                return max(0, dx - (self.altura + outro.altura) / 2)
        
        return float('inf')
    
    def _mesma_via(self, outro: 'Veiculo') -> bool:
        """Verifica se dois veículos estão na mesma via - MÃO ÚNICA."""
        tolerancia = CONFIG.LARGURA_RUA * 0.8
        
        if self.direcao == Direcao.NORTE:
            # Mesma via vertical
            return abs(self.posicao[0] - outro.posicao[0]) < tolerancia
        elif self.direcao == Direcao.LESTE:
            # Mesma via horizontal
            return abs(self.posicao[1] - outro.posicao[1]) < tolerancia
        
        return False
    
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
            # Muito próximo, frenagem de emergência
            self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
            self.velocidade_desejada = 0
            # Força parada completa se muito próximo
            if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO / 2:
                self.velocidade = 0.0
        else:
            # Cálculo de desaceleração necessária: v² = v₀² + 2*a*d
            if self.velocidade > 0.1:
                desaceleracao_necessaria = (self.velocidade ** 2) / (2 * distancia)
                self.aceleracao_atual = -min(desaceleracao_necessaria, CONFIG.DESACELERACAO_VEICULO)
            else:
                self.aceleracao_atual = 0
    