"""
Sistema de gerenciamento de faixas com IDM e MOBIL.
Implementa mudança de faixa inteligente com checagens de segurança.
"""
import math
import random
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import pygame
from configuracao import CONFIG, Direcao


class EstadoFaixa(Enum):
    """Estados possíveis de mudança de faixa."""
    KEEP_LANE = "KeepLane"
    LANE_CHANGE_LEFT = "LaneChangeLeft"
    LANE_CHANGE_RIGHT = "LaneChangeRight"


class TipoVeiculo(Enum):
    """Tipos de veículo para preferências de faixa."""
    CARRO = "carro"
    ONIBUS = "onibus"
    CAMINHAO = "caminhao"


@dataclass
class Faixa:
    """Representa uma faixa de tráfego."""
    id: int
    direcao: Direcao
    posicao_central: float  # Posição central da faixa
    largura: float
    veiculos: List['Veiculo'] = None
    
    def __post_init__(self):
        if self.veiculos is None:
            self.veiculos = []
    
    def adicionar_veiculo(self, veiculo: 'Veiculo'):
        """Adiciona um veículo à faixa."""
        if veiculo not in self.veiculos:
            self.veiculos.append(veiculo)
    
    def remover_veiculo(self, veiculo: 'Veiculo'):
        """Remove um veículo da faixa."""
        if veiculo in self.veiculos:
            self.veiculos.remove(veiculo)
    
    def obter_veiculo_frente(self, veiculo: 'Veiculo') -> Optional['Veiculo']:
        """Obtém o veículo à frente na mesma faixa."""
        veiculo_frente = None
        distancia_minima = float('inf')
        
        for outro in self.veiculos:
            if outro.id == veiculo.id or not outro.ativo:
                continue
            
            distancia = self._calcular_distancia_longitudinal(veiculo, outro)
            if distancia > 0 and distancia < distancia_minima:
                distancia_minima = distancia
                veiculo_frente = outro
        
        return veiculo_frente
    
    def obter_veiculo_atras(self, veiculo: 'Veiculo') -> Optional['Veiculo']:
        """Obtém o veículo atrás na mesma faixa."""
        veiculo_atras = None
        distancia_minima = float('inf')
        
        for outro in self.veiculos:
            if outro.id == veiculo.id or not outro.ativo:
                continue
            
            distancia = self._calcular_distancia_longitudinal(veiculo, outro)
            if distancia < 0 and abs(distancia) < distancia_minima:
                distancia_minima = abs(distancia)
                veiculo_atras = outro
        
        return veiculo_atras
    
    def _calcular_distancia_longitudinal(self, veiculo1: 'Veiculo', veiculo2: 'Veiculo') -> float:
        """Calcula distância longitudinal entre dois veículos."""
        if veiculo1.direcao == Direcao.NORTE:
            return veiculo2.posicao[1] - veiculo1.posicao[1]
        elif veiculo1.direcao == Direcao.LESTE:
            return veiculo2.posicao[0] - veiculo1.posicao[0]
        return 0.0


class LaneManager:
    """Gerencia faixas e veículos para mudança de faixa."""
    
    def __init__(self, direcao: Direcao, posicao_central: float, num_faixas: int = CONFIG.NUM_FAIXAS):
        """
        Inicializa o gerenciador de faixas.
        
        Args:
            direcao: Direção da via
            posicao_central: Posição central da via
            num_faixas: Número de faixas
        """
        self.direcao = direcao
        self.posicao_central = posicao_central
        self.num_faixas = num_faixas
        self.faixas: List[Faixa] = []
        
        self._criar_faixas()
    
    def _criar_faixas(self):
        """Cria as faixas da via."""
        largura_total = self.num_faixas * CONFIG.LARGURA_FAIXA
        inicio = self.posicao_central - largura_total / 2
        
        for i in range(self.num_faixas):
            posicao_central = inicio + (i + 0.5) * CONFIG.LARGURA_FAIXA
            faixa = Faixa(
                id=i,
                direcao=self.direcao,
                posicao_central=posicao_central,
                largura=CONFIG.LARGURA_FAIXA
            )
            self.faixas.append(faixa)
    
    def obter_faixa_veiculo(self, veiculo: 'Veiculo') -> Optional[Faixa]:
        """Obtém a faixa atual de um veículo."""
        for faixa in self.faixas:
            if veiculo in faixa.veiculos:
                return faixa
        return None
    
    def atribuir_veiculo_faixa(self, veiculo: 'Veiculo', faixa_id: int):
        """Atribui um veículo a uma faixa específica."""
        # Remove de todas as faixas
        for faixa in self.faixas:
            faixa.remover_veiculo(veiculo)
        
        # Adiciona à faixa especificada
        if 0 <= faixa_id < len(self.faixas):
            self.faixas[faixa_id].adicionar_veiculo(veiculo)
    
    def obter_faixa_aleatoria(self) -> int:
        """Obtém ID de uma faixa aleatória."""
        return random.randint(0, self.num_faixas - 1)
    
    def obter_faixas_vizinhas(self, faixa_id: int) -> Tuple[Optional[int], Optional[int]]:
        """Obtém IDs das faixas vizinhas (esquerda, direita)."""
        esquerda = faixa_id - 1 if faixa_id > 0 else None
        direita = faixa_id + 1 if faixa_id < self.num_faixas - 1 else None
        return esquerda, direita
    
    def obter_faixa_por_posicao(self, posicao: float) -> Optional[int]:
        """Obtém ID da faixa baseado na posição."""
        for i, faixa in enumerate(self.faixas):
            if abs(posicao - faixa.posicao_central) <= faixa.largura / 2:
                return i
        return None
    
    def atualizar_posicoes_veiculos(self):
        """Atualiza as posições dos veículos nas faixas."""
        for faixa in self.faixas:
            # Remove veículos inativos
            faixa.veiculos = [v for v in faixa.veiculos if v.ativo]
            
            # Ordena veículos por posição
            if self.direcao == Direcao.NORTE:
                faixa.veiculos.sort(key=lambda v: v.posicao[1], reverse=True)
            elif self.direcao == Direcao.LESTE:
                faixa.veiculos.sort(key=lambda v: v.posicao[0], reverse=True)


class IDM:
    """Implementa o Intelligent Driver Model para dinâmica longitudinal."""
    
    @staticmethod
    def calcular_aceleracao(veiculo: 'Veiculo', veiculo_frente: Optional['Veiculo'] = None) -> float:
        """
        Calcula aceleração usando IDM.
        
        Args:
            veiculo: Veículo para calcular aceleração
            veiculo_frente: Veículo à frente (opcional)
            
        Returns:
            Aceleração calculada
        """
        v = veiculo.velocidade
        v0 = CONFIG.IDM_V0
        T = CONFIG.IDM_T
        a = CONFIG.IDM_A
        b = CONFIG.IDM_B
        s0 = CONFIG.IDM_S0
        delta = CONFIG.IDM_DELTA
        s1 = CONFIG.IDM_S1
        
        # Termo de aceleração livre
        acel_livre = a * (1 - (v / v0) ** delta)
        
        # Termo de interação
        if veiculo_frente is None:
            acel_interacao = 0.0
        else:
            s = IDM._calcular_distancia_seguimento(veiculo, veiculo_frente)
            v_rel = veiculo_frente.velocidade - v
            s_star = s0 + max(0, v * T + (v * v_rel) / (2 * math.sqrt(a * b)))
            acel_interacao = -a * (s_star / (s + s1)) ** 2
        
        return acel_livre + acel_interacao
    
    @staticmethod
    def _calcular_distancia_seguimento(veiculo: 'Veiculo', veiculo_frente: 'Veiculo') -> float:
        """Calcula distância de seguimento entre veículos."""
        if veiculo.direcao == Direcao.NORTE:
            return veiculo_frente.posicao[1] - veiculo.posicao[1]
        elif veiculo.direcao == Direcao.LESTE:
            return veiculo_frente.posicao[0] - veiculo.posicao[0]
        return float('inf')


class MOBIL:
    """Implementa o modelo MOBIL para decisão de mudança de faixa."""
    
    @staticmethod
    def deve_mudar_faixa(veiculo: 'Veiculo', faixa_atual: Faixa, faixa_alvo: Faixa, 
                        lane_manager: LaneManager) -> bool:
        """
        Decide se deve mudar de faixa usando MOBIL.
        
        Args:
            veiculo: Veículo considerando mudança
            faixa_atual: Faixa atual
            faixa_alvo: Faixa alvo
            lane_manager: Gerenciador de faixas
            
        Returns:
            True se deve mudar de faixa
        """
        # Ganho próprio de aceleração
        ganho_proprio = MOBIL._calcular_ganho_proprio(veiculo, faixa_atual, faixa_alvo)
        
        if ganho_proprio < CONFIG.MOBIL_A_THRESHOLD:
            return False
        
        # Verifica impacto no seguidor da faixa alvo
        seguidor_alvo = faixa_alvo.obter_veiculo_atras(veiculo)
        if seguidor_alvo:
            impacto_seguidor = MOBIL._calcular_impacto_seguidor(
                veiculo, seguidor_alvo, faixa_atual, faixa_alvo
            )
            if impacto_seguidor < CONFIG.MOBIL_A_BACK_MIN:
                return False
        
        # Aplica fator de polidez
        p = CONFIG.MOBIL_P
        return ganho_proprio > p * abs(impacto_seguidor) if seguidor_alvo else True
    
    @staticmethod
    def _calcular_ganho_proprio(veiculo: 'Veiculo', faixa_atual: Faixa, faixa_alvo: Faixa) -> float:
        """Calcula ganho próprio de aceleração."""
        # Aceleração na faixa atual
        lider_atual = faixa_atual.obter_veiculo_frente(veiculo)
        acel_atual = IDM.calcular_aceleracao(veiculo, lider_atual)
        
        # Aceleração na faixa alvo
        lider_alvo = faixa_alvo.obter_veiculo_frente(veiculo)
        acel_alvo = IDM.calcular_aceleracao(veiculo, lider_alvo)
        
        return acel_alvo - acel_atual
    
    @staticmethod
    def _calcular_impacto_seguidor(veiculo: 'Veiculo', seguidor: 'Veiculo', 
                                  faixa_atual: Faixa, faixa_alvo: Faixa) -> float:
        """Calcula impacto no seguidor da faixa alvo."""
        # Aceleração do seguidor sem mudança
        lider_seguidor = faixa_alvo.obter_veiculo_frente(seguidor)
        acel_sem_mudanca = IDM.calcular_aceleracao(seguidor, lider_seguidor)
        
        # Aceleração do seguidor com mudança (veiculo na frente)
        acel_com_mudanca = IDM.calcular_aceleracao(seguidor, veiculo)
        
        return acel_com_mudanca - acel_sem_mudanca


class SafetyChecker:
    """Implementa checagens de segurança para mudança de faixa."""
    
    @staticmethod
    def verificar_seguranca_troca(veiculo: 'Veiculo', faixa_alvo: Faixa, 
                                 lane_manager: LaneManager) -> bool:
        """
        Verifica se é seguro mudar de faixa.
        
        Args:
            veiculo: Veículo considerando mudança
            faixa_alvo: Faixa alvo
            lane_manager: Gerenciador de faixas
            
        Returns:
            True se é seguro mudar
        """
        # Verifica distância mínima
        if not SafetyChecker._verificar_distancia_minima(veiculo, faixa_alvo):
            return False
        
        # Verifica TTC
        if not SafetyChecker._verificar_ttc(veiculo, faixa_alvo):
            return False
        
        # Verifica janela lateral
        if not SafetyChecker._verificar_janela_lateral(veiculo, faixa_alvo):
            return False
        
        return True
    
    @staticmethod
    def _verificar_distancia_minima(veiculo: 'Veiculo', faixa_alvo: Faixa) -> bool:
        """Verifica distância mínima para troca."""
        lider = faixa_alvo.obter_veiculo_frente(veiculo)
        seguidor = faixa_alvo.obter_veiculo_atras(veiculo)
        
        # Distância mínima à frente
        if lider:
            distancia_frente = abs(faixa_alvo._calcular_distancia_longitudinal(veiculo, lider))
            if distancia_frente < CONFIG.D_MIN + CONFIG.D_B:
                return False
        
        # Distância mínima atrás
        if seguidor:
            distancia_atras = abs(faixa_alvo._calcular_distancia_longitudinal(veiculo, seguidor))
            if distancia_atras < CONFIG.D_MIN + CONFIG.D_B:
                return False
        
        return True
    
    @staticmethod
    def _verificar_ttc(veiculo: 'Veiculo', faixa_alvo: Faixa) -> bool:
        """Verifica TTC (Time To Collision)."""
        lider = faixa_alvo.obter_veiculo_frente(veiculo)
        seguidor = faixa_alvo.obter_veiculo_atras(veiculo)
        
        # TTC com líder
        if lider:
            ttc_lider = SafetyChecker._calcular_ttc(veiculo, lider)
            if ttc_lider < CONFIG.TTC_MIN:
                return False
        
        # TTC com seguidor
        if seguidor:
            ttc_seguidor = SafetyChecker._calcular_ttc(seguidor, veiculo)
            if ttc_seguidor < CONFIG.TTC_MIN:
                return False
        
        return True
    
    @staticmethod
    def _calcular_ttc(veiculo1: 'Veiculo', veiculo2: 'Veiculo') -> float:
        """Calcula TTC entre dois veículos."""
        if veiculo1.velocidade <= veiculo2.velocidade:
            return float('inf')
        
        distancia = abs(veiculo1._calcular_distancia_para_veiculo(veiculo2))
        velocidade_relativa = veiculo1.velocidade - veiculo2.velocidade
        
        if velocidade_relativa <= 0:
            return float('inf')
        
        return distancia / velocidade_relativa
    
    @staticmethod
    def _verificar_janela_lateral(veiculo: 'Veiculo', faixa_alvo: Faixa) -> bool:
        """Verifica se há janela lateral livre."""
        # Simplificado: verifica se não há veículos muito próximos lateralmente
        for outro in faixa_alvo.veiculos:
            if outro.id == veiculo.id or not outro.ativo:
                continue
            
            distancia_lateral = abs(veiculo.posicao[0] - outro.posicao[0]) if veiculo.direcao == Direcao.NORTE else abs(veiculo.posicao[1] - outro.posicao[1])
            
            if distancia_lateral < CONFIG.LARGURA_FAIXA:
                return False
        
        return True
