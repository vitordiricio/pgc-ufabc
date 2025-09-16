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
from fisica_veiculo import FisicaVeiculo
from sistema_colisao import SistemaColisao
from sistema_metricas import SistemaMetricas
from renderizador_veiculo import RenderizadorVeiculo
from utils import calcular_distancia_ate_ponto, passou_da_linha


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
        
        # Velocidade individual do veículo
        self.velocidade_maxima_individual = random.uniform(
            CONFIG.VELOCIDADE_MIN_INDIVIDUAL, 
            CONFIG.VELOCIDADE_MAX_INDIVIDUAL
        )
        
        # Dimensões
        self.largura = CONFIG.LARGURA_VEICULO
        self.altura = CONFIG.ALTURA_VEICULO
        
        # Estados
        self.no_cruzamento = False
        self.passou_semaforo = False
        self.aguardando_semaforo = False
        
        # Controle de semáforo
        self.semaforo_proximo = None
        self.ultimo_semaforo_processado = None
        self.distancia_semaforo = float('inf')
        self.pode_passar_amarelo = False
        
        # Inicializa sistemas especializados
        self.fisica = FisicaVeiculo(self)
        self.colisao = SistemaColisao(self)
        self.metricas = SistemaMetricas(self)
        self.renderizador = RenderizadorVeiculo(self)
        
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
    
    
    def processar_todos_veiculos(self, todos_veiculos: List['Veiculo']) -> None:
        """
        Processa interação com todos os veículos, não apenas os do cruzamento atual.
        
        Args:
            todos_veiculos: Lista de todos os veículos na simulação
        """
        self.colisao.processar_todos_veiculos(todos_veiculos)

    def atualizar(self, dt: float = 1.0, todos_veiculos: List['Veiculo'] = None, malha=None) -> None:
        """
        Atualiza o estado do veículo.

        Args:
            dt: Delta time para cálculos de física
            todos_veiculos: Lista de todos os veículos para verificação de colisão
            malha: MalhaViaria para aplicar o fator de 'caos' (limite local de velocidade)
        """
        # Atualiza métricas
        self.metricas.atualizar_metricas(dt)

        # Aplica aceleração
        self.fisica.aplicar_aceleracao(dt)

        # Aplica limite de velocidade com fator local (CAOS)
        fator = malha.obter_fator_caos(self) if malha is not None else 1.0
        self.fisica.aplicar_limite_velocidade(fator)

        # Verifica colisão futura
        if todos_veiculos and self.fisica.velocidade > 0:
            if self.colisao.verificar_colisao_futura(todos_veiculos):
                self.fisica.parar_veiculo()
                self._atualizar_rect()
                return

        # Move o veículo
        dx, dy = self.fisica.mover_veiculo(dt)

        self._atualizar_rect()

        # Verifica saída da tela
        if self.fisica.verificar_saida_tela():
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
            if not self.colisao.veiculo_frente or self.colisao.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.fisica.acelerar_normalmente()
            return

        # Verifica se é um novo semáforo
        if self.ultimo_semaforo_processado != semaforo:
            self.passou_semaforo = False
            self.ultimo_semaforo_processado = semaforo
            self.pode_passar_amarelo = False

        # Se já passou deste semáforo específico, ignora
        if self.passou_semaforo:
            if not self.colisao.veiculo_frente or self.colisao.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.fisica.acelerar_normalmente()
            return

        # Calcula distância até a linha de parada
        self.distancia_semaforo = calcular_distancia_ate_ponto(self.posicao, posicao_parada, self.direcao)

        # Se já passou da linha de parada, marca como passado
        if passou_da_linha(self.posicao, posicao_parada, self.direcao):
            self.passou_semaforo = True
            self.aguardando_semaforo = False
            if not self.colisao.veiculo_frente or self.colisao.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.fisica.acelerar_normalmente()
            return

        # Lógica baseada no estado do semáforo
        if semaforo.estado == EstadoSemaforo.VERDE:
            # Semáforo verde: acelera normalmente (se não houver veículo à frente)
            self.aguardando_semaforo = False
            if not self.colisao.veiculo_frente or self.colisao.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.fisica.acelerar_normalmente()

        elif semaforo.estado == EstadoSemaforo.AMARELO:
            # Semáforo amarelo: decide se passa ou freia
            if self.pode_passar_amarelo:
                # Já tinha decidido passar, mantém
                self.fisica.definir_aceleracao(0)
            else:
                # Avalia se pode passar
                tempo_ate_linha = self.distancia_semaforo / max(self.fisica.velocidade, 0.1)
                
                # Só passa se estiver muito próximo E em velocidade suficiente
                if (tempo_ate_linha < 1.0 and 
                    self.fisica.velocidade > CONFIG.VELOCIDADE_BASE * 0.7 and 
                    self.distancia_semaforo < CONFIG.DISTANCIA_PARADA_SEMAFORO * 3):
                    # Perto demais para parar com segurança
                    self.pode_passar_amarelo = True
                    self.fisica.definir_aceleracao(0)
                else:
                    # Tem tempo para parar com segurança
                    self.fisica.aplicar_frenagem_para_parada(self.distancia_semaforo)
                    self.aguardando_semaforo = True

        elif semaforo.estado == EstadoSemaforo.VERMELHO:
            # Semáforo vermelho: SEMPRE para
            self.aguardando_semaforo = True
            self.pode_passar_amarelo = False
            
            if self.distancia_semaforo <= CONFIG.DISTANCIA_PARADA_SEMAFORO:
                # Muito próximo da linha, para imediatamente
                self.fisica.parar_veiculo()
            else:
                # Aplica frenagem para parar antes da linha
                self.fisica.aplicar_frenagem_para_parada(self.distancia_semaforo)

    
    
    def desenhar(self, tela: pygame.Surface) -> None:
        """Desenha o veículo na tela com visual aprimorado - MÃO ÚNICA."""
        self.renderizador.desenhar(tela)
    
    # Propriedades para compatibilidade com código existente
    @property
    def velocidade(self) -> float:
        """Retorna a velocidade atual do veículo."""
        return self.fisica.velocidade
    
    @property
    def aceleracao_atual(self) -> float:
        """Retorna a aceleração atual do veículo."""
        return self.fisica.aceleracao_atual
    
    @property
    def parado(self) -> bool:
        """Retorna se o veículo está parado."""
        return self.metricas.parado
    
    @property
    def veiculo_frente(self):
        """Retorna o veículo à frente."""
        return self.colisao.veiculo_frente
    
    @property
    def distancia_veiculo_frente(self) -> float:
        """Retorna a distância até o veículo à frente."""
        return self.colisao.distancia_veiculo_frente
    
    @property
    def tempo_viagem(self) -> float:
        """Retorna o tempo de viagem do veículo."""
        return self.metricas.tempo_viagem
    
    @property
    def tempo_parado(self) -> float:
        """Retorna o tempo parado do veículo."""
        return self.metricas.tempo_parado
    
    @property
    def paradas_totais(self) -> int:
        """Retorna o número total de paradas."""
        return self.metricas.paradas_totais
    
    @property
    def distancia_percorrida(self) -> float:
        """Retorna a distância percorrida pelo veículo."""
        return self.metricas.distancia_percorrida