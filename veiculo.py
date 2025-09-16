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
from malha_viaria import TipoMovimento, MalhaViaria
from sistema_faixas import EstadoFaixa, TipoVeiculo, LaneManager, IDM, MOBIL, SafetyChecker
from intersection_manager import IntersectionManager


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
        
        # Sistema de rotas
        self.rota: List[Tuple[int, int]] = []  # Lista de IDs de cruzamentos da rota
        self.proximo_no: Optional[Tuple[int, int]] = None  # Próximo nó da rota
        self.proximo_movimento: TipoMovimento = TipoMovimento.RETA  # Próximo movimento
        self.estado_reserva: bool = False  # Se tem reserva ativa na interseção
        self.destino: Optional[Tuple[int, int]] = None  # Destino final
        self.malha_viaria: Optional[MalhaViaria] = None  # Referência à malha
        
        # Sistema de mudança de faixa
        self.estado_faixa: EstadoFaixa = EstadoFaixa.KEEP_LANE
        self.faixa_atual: int = 0  # ID da faixa atual
        self.faixa_alvo: Optional[int] = None  # ID da faixa alvo
        self.tipo_veiculo: TipoVeiculo = TipoVeiculo.CARRO
        self.lane_manager: Optional[LaneManager] = None  # Gerenciador de faixas
        
        # Controle de mudança de faixa
        self.frames_troca: int = 0  # Frames restantes para completar troca
        self.posicao_lateral_inicial: float = 0.0  # Posição lateral inicial da troca
        self.posicao_lateral_final: float = 0.0  # Posição lateral final da troca
        self.velocidade_lateral: float = 0.0  # Velocidade lateral atual
        
        # Predição de trajetória
        self.trajetoria_predita: List[Tuple[float, float]] = []  # Trajetória predita
        self.tempo_predicao: float = 0.0  # Tempo de predição atual
        
        # Sistema de reservas de interseção
        self.intersection_manager: Optional[IntersectionManager] = None  # Gerenciador de interseção
        self.reserva_ativa: bool = False  # Se tem reserva ativa
        self.tempo_espera_intersecao: float = 0.0  # Tempo esperando na interseção
        self.prioridade: int = CONFIG.PRIORIDADE_NORMAL  # Prioridade do veículo
        
        # Controle de segurança
        self.velocidade_alvo = CONFIG.VELOCIDADE_VEICULO
        self.ttc_lider = float('inf')  # Tempo para colisão com líder
        self.distancia_frenagem_segura = 0.0
        
        # Retângulo de colisão
        self._atualizar_rect()
    
    def definir_rota(self, rota: List[Tuple[int, int]], malha_viaria: MalhaViaria):
        """
        Define uma rota para o veículo.
        
        Args:
            rota: Lista de IDs de cruzamentos da rota
            malha_viaria: Referência à malha viária
        """
        self.rota = rota.copy()
        self.malha_viaria = malha_viaria
        self.destino = rota[-1] if rota else None
        self._atualizar_proximo_no()
    
    def _atualizar_proximo_no(self):
        """Atualiza o próximo nó da rota."""
        if not self.rota:
            self.proximo_no = None
            return
        
        # Encontra o próximo nó na rota
        for i, no in enumerate(self.rota):
            if no == self.id_cruzamento_atual:
                if i + 1 < len(self.rota):
                    self.proximo_no = self.rota[i + 1]
                else:
                    self.proximo_no = None
                break
    
    def recalcular_rota(self) -> bool:
        """
        Recalcula a rota do veículo.
        
        Returns:
            True se a rota foi recalculada com sucesso
        """
        if not self.malha_viaria or not self.destino:
            return False
        
        nova_rota = self.malha_viaria.calcular_rota(
            self.id_cruzamento_atual, 
            self.destino, 
            CONFIG.ALGORITMO_PATHFINDING
        )
        
        if nova_rota:
            self.rota = nova_rota
            self._atualizar_proximo_no()
            return True
        
        return False
    
    def verificar_necessidade_recalculo(self) -> bool:
        """
        Verifica se é necessário recalcular a rota.
        
        Returns:
            True se deve recalcular
        """
        if not self.rota or not self.malha_viaria:
            return False
        
        # Recalcula com probabilidade configurada
        if random.random() < CONFIG.PROBABILIDADE_MUDANCA_ROTA:
            return True
        
        # Verifica se a rota atual está bloqueada
        for i in range(len(self.rota) - 1):
            origem = self.rota[i]
            destino = self.rota[i + 1]
            
            # Verifica se a aresta está bloqueada
            for aresta in self.malha_viaria.arestas:
                if aresta.origem == origem and aresta.destino == destino and aresta.bloqueada:
                    return True
        
        return False
    
    def calcular_distancia_frenagem_segura(self) -> float:
        """
        Calcula a distância de frenagem segura.
        
        Returns:
            Distância de frenagem segura em pixels
        """
        if self.velocidade <= 0:
            return 0.0
        
        # Fórmula: d = v²/(2*a) + margem
        distancia_fisica = (self.velocidade ** 2) / (2 * CONFIG.ACELERACAO_MAX_FREIO)
        return distancia_fisica + CONFIG.MARGEM_SEGURANCA_FREIO
    
    def calcular_ttc_lider(self, veiculo_lider: 'Veiculo') -> float:
        """
        Calcula o tempo para colisão com o veículo líder.
        
        Args:
            veiculo_lider: Veículo à frente
            
        Returns:
            Tempo para colisão em segundos
        """
        if not veiculo_lider or self.velocidade <= veiculo_lider.velocidade:
            return float('inf')
        
        distancia = self._calcular_distancia_para_veiculo(veiculo_lider)
        velocidade_relativa = self.velocidade - veiculo_lider.velocidade
        
        if velocidade_relativa <= 0:
            return float('inf')
        
        return distancia / velocidade_relativa
    
    def aplicar_controle_seguranca(self, todos_veiculos: List['Veiculo']) -> None:
        """
        Aplica controle de segurança baseado em TTC e distância de frenagem.
        
        Args:
            todos_veiculos: Lista de todos os veículos
        """
        # Calcula distância de frenagem segura
        self.distancia_frenagem_segura = self.calcular_distancia_frenagem_segura()
        
        # Atualiza TTC com líder
        if self.veiculo_frente:
            self.ttc_lider = self.calcular_ttc_lider(self.veiculo_frente)
            
            # Aplica controle baseado em TTC
            if self.ttc_lider < CONFIG.TTC_LIMIAR_CRITICO:
                # Situação crítica: para imediatamente
                self.velocidade_alvo = 0.0
                self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
            elif self.ttc_lider < CONFIG.TTC_LIMIAR_ALERTA:
                # Situação de alerta: reduz velocidade
                self.velocidade_alvo = self.veiculo_frente.velocidade * 0.8
                if self.velocidade > self.velocidade_alvo:
                    self.aceleracao_atual = -CONFIG.DESACELERACAO_VEICULO
            else:
                # Situação normal: mantém velocidade desejada
                self.velocidade_alvo = CONFIG.VELOCIDADE_VEICULO
        else:
            # Sem veículo à frente: velocidade normal
            self.velocidade_alvo = CONFIG.VELOCIDADE_VEICULO
            self.ttc_lider = float('inf')
    
    def solicitar_reserva_intersecao(self, cruzamento) -> bool:
        """
        Solicita reserva de interseção no cruzamento.
        
        Args:
            cruzamento: Cruzamento onde solicitar reserva
            
        Returns:
            True se a reserva foi concedida
        """
        if not cruzamento or self.estado_reserva:
            return False
        
        # Calcula bounding box da trajetória
        bbox_trajetoria = self._calcular_bbox_trajetoria()
        
        # Solicita reserva
        reserva_concedida = cruzamento.solicitar_reserva_intersecao(
            self.id, self.proximo_movimento, self.direcao, bbox_trajetoria
        )
        
        if reserva_concedida:
            self.estado_reserva = True
        
        return reserva_concedida
    
    def liberar_reserva_intersecao(self, cruzamento):
        """
        Libera reserva de interseção no cruzamento.
        
        Args:
            cruzamento: Cruzamento onde liberar reserva
        """
        if cruzamento and self.estado_reserva:
            cruzamento.liberar_reserva_intersecao(self.id)
            self.estado_reserva = False
    
    def _calcular_bbox_trajetoria(self) -> pygame.Rect:
        """
        Calcula bounding box da trajetória do veículo.
        
        Returns:
            Retângulo da trajetória
        """
        # Simplificado: usa o retângulo atual do veículo
        # Em uma implementação completa, projetaria a trajetória futura
        return self.rect.copy()
    
    def definir_lane_manager(self, lane_manager: LaneManager):
        """
        Define o gerenciador de faixas para o veículo.
        
        Args:
            lane_manager: Gerenciador de faixas
        """
        self.lane_manager = lane_manager
        # Atribui veículo à faixa inicial
        if lane_manager:
            faixa_inicial = lane_manager.obter_faixa_aleatoria()
            lane_manager.atribuir_veiculo_faixa(self, faixa_inicial)
            self.faixa_atual = faixa_inicial
    
    def definir_intersection_manager(self, intersection_manager: IntersectionManager):
        """
        Define o gerenciador de interseção para o veículo.
        
        Args:
            intersection_manager: Gerenciador de interseção
        """
        self.intersection_manager = intersection_manager
    
    def atualizar_mudanca_faixa(self) -> None:
        """Atualiza o processo de mudança de faixa."""
        if self.estado_faixa == EstadoFaixa.KEEP_LANE:
            self._avaliar_mudanca_faixa()
        elif self.estado_faixa in [EstadoFaixa.LANE_CHANGE_LEFT, EstadoFaixa.LANE_CHANGE_RIGHT]:
            self._executar_mudanca_faixa()
    
    def _avaliar_mudanca_faixa(self) -> None:
        """Avalia se deve mudar de faixa."""
        if not self.lane_manager:
            return
        
        # Verifica se está próximo de interseção
        if self._proximo_de_intersecao():
            return
        
        # Obtém faixa atual
        faixa_atual = self.lane_manager.obter_faixa_veiculo(self)
        if not faixa_atual:
            return
        
        # Obtém faixas vizinhas
        esquerda_id, direita_id = self.lane_manager.obter_faixas_vizinhas(faixa_atual.id)
        
        # Avalia mudança de faixa se há múltiplos veículos na faixa atual
        if len(faixa_atual.veiculos) > 1:
            # Avalia mudança para esquerda
            if esquerda_id is not None:
                faixa_esquerda = self.lane_manager.faixas[esquerda_id]
                if self._deve_mudar_para_faixa(faixa_esquerda):
                    self._iniciar_mudanca_faixa(esquerda_id, EstadoFaixa.LANE_CHANGE_LEFT)
                    return
            
            # Avalia mudança para direita
            if direita_id is not None:
                faixa_direita = self.lane_manager.faixas[direita_id]
                if self._deve_mudar_para_faixa(faixa_direita):
                    self._iniciar_mudanca_faixa(direita_id, EstadoFaixa.LANE_CHANGE_RIGHT)
                    return
    
    def _deve_mudar_para_faixa(self, faixa_alvo) -> bool:
        """Verifica se deve mudar para uma faixa específica."""
        if not self.lane_manager:
            return False
        
        faixa_atual = self.lane_manager.obter_faixa_veiculo(self)
        if not faixa_atual:
            return False
        
        # Verifica segurança
        if not SafetyChecker.verificar_seguranca_troca(self, faixa_alvo, self.lane_manager):
            return False
        
        # Aplica MOBIL
        return MOBIL.deve_mudar_faixa(self, faixa_atual, faixa_alvo, self.lane_manager)
    
    def _iniciar_mudanca_faixa(self, faixa_alvo_id: int, estado: EstadoFaixa):
        """Inicia o processo de mudança de faixa."""
        self.estado_faixa = estado
        self.faixa_alvo = faixa_alvo_id
        self.frames_troca = CONFIG.FRAMES_TROCA_FAIXA
        
        # Calcula posições inicial e final
        if self.lane_manager:
            faixa_atual = self.lane_manager.faixas[self.faixa_atual]
            faixa_alvo = self.lane_manager.faixas[faixa_alvo_id]
            
            self.posicao_lateral_inicial = faixa_atual.posicao_central
            self.posicao_lateral_final = faixa_alvo.posicao_central
    
    def _executar_mudanca_faixa(self) -> None:
        """Executa a mudança de faixa."""
        if self.frames_troca <= 0:
            self._finalizar_mudanca_faixa()
            return
        
        # Verifica se deve abortar
        if self._deve_abortar_mudanca():
            self._abortar_mudanca_faixa()
            return
        
        # Calcula progresso da interpolação
        progresso = 1.0 - (self.frames_troca / CONFIG.FRAMES_TROCA_FAIXA)
        progresso = self._aplicar_easing(progresso)
        
        # Calcula posição lateral atual
        posicao_lateral_atual = self.posicao_lateral_inicial + progresso * (self.posicao_lateral_final - self.posicao_lateral_inicial)
        
        # Atualiza posição lateral
        if self.direcao == Direcao.NORTE:
            self.posicao[0] = posicao_lateral_atual
        elif self.direcao == Direcao.LESTE:
            self.posicao[1] = posicao_lateral_atual
        
        self.frames_troca -= 1
    
    def _finalizar_mudanca_faixa(self) -> None:
        """Finaliza a mudança de faixa."""
        if self.faixa_alvo is not None and self.lane_manager:
            # Move veículo para nova faixa
            self.lane_manager.atribuir_veiculo_faixa(self, self.faixa_alvo)
            self.faixa_atual = self.faixa_alvo
        
        # Reseta estado
        self.estado_faixa = EstadoFaixa.KEEP_LANE
        self.faixa_alvo = None
        self.frames_troca = 0
        self.velocidade_lateral = 0.0
    
    def _abortar_mudanca_faixa(self) -> None:
        """Aborta a mudança de faixa e retorna à faixa original."""
        # Retorna à posição original
        if self.lane_manager:
            faixa_atual = self.lane_manager.faixas[self.faixa_atual]
            if self.direcao == Direcao.NORTE:
                self.posicao[0] = faixa_atual.posicao_central
            elif self.direcao == Direcao.LESTE:
                self.posicao[1] = faixa_atual.posicao_central
        
        # Reseta estado
        self.estado_faixa = EstadoFaixa.KEEP_LANE
        self.faixa_alvo = None
        self.frames_troca = 0
        self.velocidade_lateral = 0.0
    
    def _deve_abortar_mudanca(self) -> bool:
        """Verifica se deve abortar a mudança de faixa."""
        if not self.lane_manager or self.faixa_alvo is None:
            return True
        
        faixa_alvo = self.lane_manager.faixas[self.faixa_alvo]
        
        # Verifica TTC crítico
        lider = faixa_alvo.obter_veiculo_frente(self)
        if lider:
            ttc = SafetyChecker._calcular_ttc(self, lider)
            if ttc < CONFIG.TTC_ABORT:
                return True
        
        seguidor = faixa_alvo.obter_veiculo_atras(self)
        if seguidor:
            ttc = SafetyChecker._calcular_ttc(seguidor, self)
            if ttc < CONFIG.TTC_ABORT:
                return True
        
        return False
    
    def _proximo_de_intersecao(self) -> bool:
        """Verifica se está próximo de uma interseção."""
        # Simplificado: verifica se está próximo de um cruzamento
        if not self.malha_viaria:
            return False
        
        # Acessa cruzamentos através da malha
        if hasattr(self.malha_viaria, 'cruzamentos'):
            for cruzamento_id, cruzamento in self.malha_viaria.cruzamentos.items():
                distancia = math.sqrt(
                    (self.posicao[0] - cruzamento.centro_x) ** 2 + 
                    (self.posicao[1] - cruzamento.centro_y) ** 2
                )
                if distancia < CONFIG.ZONA_INTERSECAO:
                    return True
        
        return False
    
    def _aplicar_easing(self, progresso: float) -> float:
        """Aplica easing à interpolação."""
        if CONFIG.EASING_TROCA == "ease_in_out":
            # Easing suave
            return 3 * progresso ** 2 - 2 * progresso ** 3
        else:
            # Linear
            return progresso
    
    def aplicar_idm(self, todos_veiculos: List['Veiculo']) -> None:
        """Aplica IDM para controle longitudinal."""
        if not self.lane_manager:
            return
        
        faixa_atual = self.lane_manager.obter_faixa_veiculo(self)
        if not faixa_atual:
            return
        
        # Obtém veículo à frente
        veiculo_frente = faixa_atual.obter_veiculo_frente(self)
        
        # Calcula aceleração usando IDM
        acel_idm = IDM.calcular_aceleracao(self, veiculo_frente)
        
        # Aplica aceleração
        self.aceleracao_atual = acel_idm
    
    def solicitar_reserva_intersecao(self) -> bool:
        """
        Solicita reserva de interseção se próximo de uma.
        
        Returns:
            True se a reserva foi concedida
        """
        if not self.intersection_manager:
            return False
        
        # Verifica se está próximo de interseção
        if not self._proximo_de_intersecao():
            return False
        
        # Se já tem reserva, não solicita novamente
        if self.reserva_ativa:
            return True
        
        # Determina movimento baseado na direção e rota
        movimento = self._determinar_movimento_intersecao()
        if not movimento:
            return False
        
        # Calcula janela temporal
        t0 = self.tempo_atual
        t1 = t0 + CONFIG.DT_RESERVA
        
        # Calcula bounding box da trajetória
        bbox_traj = self._calcular_bbox_trajetoria_intersecao()
        
        # Solicita reserva
        if self.intersection_manager.request(
            self.id, movimento, t0, t1, bbox_traj, self.prioridade
        ):
            self.reserva_ativa = True
            self.tempo_espera_intersecao = 0.0
            return True
        
        return False
    
    def liberar_reserva_intersecao(self) -> None:
        """Libera reserva de interseção."""
        if self.intersection_manager and self.reserva_ativa:
            self.intersection_manager.release(self.id)
            self.reserva_ativa = False
            self.tempo_espera_intersecao = 0.0
    
    def _determinar_movimento_intersecao(self) -> Optional[Tuple[Direcao, TipoMovimento]]:
        """
        Determina o movimento na interseção baseado na direção e rota.
        
        Returns:
            Tupla (direção, tipo_movimento) ou None
        """
        # Por simplicidade, assume movimento reto
        # Em uma implementação completa, usaria a rota planejada
        if self.direcao == Direcao.NORTE:
            return (Direcao.NORTE, TipoMovimento.RETA)
        elif self.direcao == Direcao.LESTE:
            return (Direcao.LESTE, TipoMovimento.RETA)
        
        return None
    
    def _calcular_bbox_trajetoria_intersecao(self) -> pygame.Rect:
        """
        Calcula bounding box da trajetória na interseção.
        
        Returns:
            Bounding box da trajetória
        """
        # Por simplicidade, usa o retângulo atual do veículo
        # Em uma implementação completa, projetaria a trajetória futura
        return self.rect.copy()
    
    def verificar_bloqueio_intersecao(self) -> bool:
        """
        Verifica se deve ser bloqueado por não ter reserva de interseção.
        
        Returns:
            True se deve ser bloqueado
        """
        if not self.intersection_manager:
            return False
        
        # Se não está próximo de interseção, não bloqueia
        if not self._proximo_de_intersecao():
            return False
        
        # Se tem reserva ativa, não bloqueia
        if self.reserva_ativa:
            return False
        
        # Verifica se está tentando entrar sem reserva
        return self.intersection_manager.verificar_entrada_sem_reserva(self.id)
    
    def _atualizar_reservas_intersecao(self, dt: float) -> None:
        """Atualiza sistema de reservas de interseção."""
        if not self.intersection_manager:
            return
        
        # Solicita reserva se próximo de interseção
        if self._proximo_de_intersecao():
            if not self.reserva_ativa:
                self.solicitar_reserva_intersecao()
        else:
            # Libera reserva se saiu da interseção
            if self.reserva_ativa:
                self.liberar_reserva_intersecao()
        
        # Verifica timeout de espera
        if self.tempo_espera_intersecao > CONFIG.TEMPO_ESPERA_MAX:
            # Fallback: libera via movimento retilíneo se possível
            if self._pode_liberar_fallback():
                self.liberar_reserva_intersecao()
                self.tempo_espera_intersecao = 0.0
    
    def _pode_liberar_fallback(self) -> bool:
        """Verifica se pode liberar via fallback (movimento retilíneo)."""
        if not self.intersection_manager:
            return False
        
        # Verifica se semáforo está verde
        if not self.intersection_manager.semaforo_verde:
            return False
        
        # Verifica se não há conflitos com movimento reto
        movimento = self._determinar_movimento_intersecao()
        if not movimento:
            return False
        
        # Verifica se pode solicitar reserva
        t0 = self.tempo_atual
        t1 = t0 + CONFIG.DT_RESERVA
        bbox_traj = self._calcular_bbox_trajetoria_intersecao()
        
        return self.intersection_manager.can_request(movimento, (t0, t1), bbox_traj)
    
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

    def atualizar(self, dt: float = 1.0, todos_veiculos: List['Veiculo'] = None, malha=None) -> None:
        """
        Atualiza o estado do veículo com sistema de rotas e segurança.

        Args:
            dt: Delta time para cálculos de física
            todos_veiculos: Lista de todos os veículos para verificação de colisão
            malha: MalhaViaria para aplicar o fator de 'caos' (limite local de velocidade)
        """
        # Métricas
        self.tempo_viagem += dt
        if self.velocidade < 0.1:
            self.tempo_parado += dt
            if not self.parado:
                self.paradas_totais += 1
            self.parado = True
        else:
            self.parado = False

        # Sistema de rotas
        if self.malha_viaria and self.verificar_necessidade_recalculo():
            self.recalcular_rota()

        # Sistema de mudança de faixa
        self.atualizar_mudanca_faixa()

        # Sistema de reservas de interseção
        self._atualizar_reservas_intersecao(dt)

        # Aplica IDM para controle longitudinal
        self.aplicar_idm(todos_veiculos)

        # Controle de segurança
        if todos_veiculos:
            self.aplicar_controle_seguranca(todos_veiculos)

        # Aplica aceleração
        self.velocidade += self.aceleracao_atual * dt

        # Limite de velocidade com fator local (CAOS)
        fator = malha.obter_fator_caos(self) if malha is not None else 1.0
        vmax_local = CONFIG.VELOCIDADE_MAX_VEICULO * fator
        self.velocidade = max(CONFIG.VELOCIDADE_MIN_VEICULO, min(vmax_local, self.velocidade))

        # Verificação de colisão futura
        if todos_veiculos and self.velocidade > 0:
            if self.verificar_colisao_futura(todos_veiculos):
                self.velocidade = 0
                self.aceleracao_atual = 0
                self._atualizar_rect()
                return

        # Movimento
        dx, dy = 0, 0
        if self.direcao == Direcao.NORTE:
            dy = self.velocidade
        elif self.direcao == Direcao.LESTE:
            dx = self.velocidade

        self.posicao[0] += dx
        self.posicao[1] += dy
        self.distancia_percorrida += math.sqrt(dx ** 2 + dy ** 2)

        self._atualizar_rect()

        # Atualiza próximo nó da rota
        self._atualizar_proximo_no()

        # Saída da tela
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
        margem = 10
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
    
    def desenhar(self, tela: pygame.Surface) -> None:
        """Desenha o veículo na tela com visual aprimorado - MÃO ÚNICA."""
        # Cria superfície para o veículo
        if self.direcao == Direcao.NORTE:
            superficie = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
        else:  # Direcao.LESTE
            superficie = pygame.Surface((self.altura, self.largura), pygame.SRCALPHA)
        
        # Desenha o corpo do veículo
        pygame.draw.rect(superficie, self.cor, superficie.get_rect(), border_radius=4)
        
        # Adiciona detalhes (janelas)
        cor_janela = (200, 220, 255, 180)
        if self.direcao == Direcao.NORTE:
            # Janela frontal (parte de baixo - direção do movimento)
            pygame.draw.rect(superficie, cor_janela, 
                           (3, self.altura * 0.7, self.largura - 6, self.altura * 0.25), 
                           border_radius=2)
            # Janela traseira (parte de cima)
            pygame.draw.rect(superficie, cor_janela, 
                           (3, 3, self.largura - 6, self.altura * 0.3), 
                           border_radius=2)
        else:  # Direcao.LESTE
            # Janela frontal (parte direita - direção do movimento)
            pygame.draw.rect(superficie, cor_janela, 
                           (self.altura * 0.7, 3, self.altura * 0.25, self.largura - 6), 
                           border_radius=2)
            # Janela traseira (parte esquerda)
            pygame.draw.rect(superficie, cor_janela, 
                           (3, 3, self.altura * 0.3, self.largura - 6), 
                           border_radius=2)
        
        # Adiciona luzes de freio se estiver freando
        if self.aceleracao_atual < -0.1:
            cor_freio = (255, 100, 100)
            if self.direcao == Direcao.NORTE:
                # Luzes na parte de cima (traseira)
                pygame.draw.rect(superficie, cor_freio, (2, 1, 6, 3))
                pygame.draw.rect(superficie, cor_freio, (self.largura - 8, 1, 6, 3))
            elif self.direcao == Direcao.LESTE:
                # Luzes na parte esquerda (traseira)
                pygame.draw.rect(superficie, cor_freio, (1, 2, 3, 6))
                pygame.draw.rect(superficie, cor_freio, (1, self.largura - 8, 3, 6))
        
        # Adiciona faróis
        cor_farol = (255, 255, 200, 150)
        if self.direcao == Direcao.NORTE:
            # Faróis na frente (parte de baixo)
            pygame.draw.circle(superficie, cor_farol, (8, self.altura - 5), 3)
            pygame.draw.circle(superficie, cor_farol, (self.largura - 8, self.altura - 5), 3)
        elif self.direcao == Direcao.LESTE:
            # Faróis na frente (parte direita)
            pygame.draw.circle(superficie, cor_farol, (self.altura - 5, 8), 3)
            pygame.draw.circle(superficie, cor_farol, (self.altura - 5, self.largura - 8), 3)
        
        # Desenha na tela
        rect = superficie.get_rect(center=(int(self.posicao[0]), int(self.posicao[1])))
        tela.blit(superficie, rect)
        
        # Debug info
        if CONFIG.MOSTRAR_INFO_VEICULO:
            fonte = pygame.font.SysFont('Arial', 10)
            # Adiciona indicador se está aguardando semáforo ou veículo
            aguardando = ""
            if self.aguardando_semaforo:
                aguardando = "🔴"
            elif self.veiculo_frente and self.distancia_veiculo_frente < CONFIG.DISTANCIA_REACAO:
                aguardando = "🚗"
            
            # Adiciona indicador de mudança de faixa
            mudanca_faixa = ""
            if self.estado_faixa == EstadoFaixa.LANE_CHANGE_LEFT:
                mudanca_faixa = "⬅️"
            elif self.estado_faixa == EstadoFaixa.LANE_CHANGE_RIGHT:
                mudanca_faixa = "➡️"
            
            # Adiciona indicador de reserva de interseção
            reserva = "🔒" if self.reserva_ativa else ""
            
            texto = f"V:{self.velocidade:.1f} ID:{self.id} F:{self.faixa_atual} {aguardando}{mudanca_faixa}{reserva}"
            superficie_texto = fonte.render(texto, True, CONFIG.BRANCO)
            tela.blit(superficie_texto, (self.posicao[0] - 20, self.posicao[1] - 25))