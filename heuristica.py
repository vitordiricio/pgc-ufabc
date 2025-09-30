"""
Módulo de heurísticas para controle de semáforos.
Implementa padrão Strategy para diferentes algoritmos de controle.
"""
from abc import ABC, abstractmethod
from typing import Dict, Tuple, TYPE_CHECKING
import random
from configuracao import TipoHeuristica, EstadoSemaforo, Direcao

if TYPE_CHECKING:
    from semaforo import Semaforo


class Heuristica(ABC):
    """Classe abstrata base para todas as heurísticas de controle de semáforos."""
    
    def __init__(self):
        """Inicializa a heurística."""
        self.config = self._inicializar_config()
        self.tempo_ciclo = 0
    
    @abstractmethod
    def _inicializar_config(self) -> Dict:
        """Inicializa configurações específicas da heurística."""
        pass
    
    @abstractmethod
    def atualizar(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                  densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """
        Atualiza todos os semáforos baseado na heurística.
        
        Args:
            semaforos: Dicionário de semáforos por cruzamento e direção
            densidade_por_cruzamento: Número de veículos por direção em cada cruzamento
        """
        pass
    
    def _verificar_alternancia_mao_unica(self, semaforos: Dict[Direcao, 'Semaforo']) -> None:
        """Verifica e corrige a alternância entre semáforos - MÃO ÚNICA."""
        # Apenas duas direções: NORTE e LESTE
        semaforo_norte = semaforos.get(Direcao.NORTE)
        semaforo_leste = semaforos.get(Direcao.LESTE)
        
        if not semaforo_norte or not semaforo_leste:
            return
        
        # Se ambos estão vermelhos, libera o que esperou mais
        if (semaforo_norte.estado == EstadoSemaforo.VERMELHO and 
            semaforo_leste.estado == EstadoSemaforo.VERMELHO):
            
            if semaforo_norte.tempo_no_estado > semaforo_leste.tempo_no_estado:
                semaforo_norte.forcar_mudanca(EstadoSemaforo.VERDE)
            else:
                semaforo_leste.forcar_mudanca(EstadoSemaforo.VERDE)
        
        # Se um acabou de ficar vermelho, o outro deve ficar verde
        elif (semaforo_norte.estado == EstadoSemaforo.VERMELHO and 
              semaforo_norte.tempo_no_estado < 2):
            if semaforo_leste.estado == EstadoSemaforo.VERMELHO:
                semaforo_leste.forcar_mudanca(EstadoSemaforo.VERDE)
        elif (semaforo_leste.estado == EstadoSemaforo.VERMELHO and 
              semaforo_leste.tempo_no_estado < 2):
            if semaforo_norte.estado == EstadoSemaforo.VERMELHO:
                semaforo_norte.forcar_mudanca(EstadoSemaforo.VERDE)


class HeuristicaVerticalHorizontal(Heuristica):
    """
    Heurística que alterna entre tráfego vertical e horizontal a cada 5 segundos.
    Quando os horizontais fecham, os verticais abrem e vice-versa.
    """
    
    def _inicializar_config(self) -> Dict:
        """Inicializa configurações para alternância vertical/horizontal."""
        return {
            'intervalo_alternancia': 300,  # 5 segundos (300 frames a 60 FPS)
            'tempo_desde_ultima_alternancia': 0,
            'fase_atual': 'horizontal'  # Começa com horizontal (LESTE)
        }
    
    def atualizar(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                  densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Atualização com alternância vertical/horizontal a cada 5 segundos."""
        self.config['tempo_desde_ultima_alternancia'] += 1
        
        # Verifica se é hora de alternar
        if self.config['tempo_desde_ultima_alternancia'] >= self.config['intervalo_alternancia']:
            self._alternar_fase(semaforos)
            self.config['tempo_desde_ultima_alternancia'] = 0
        
        # Atualiza todos os semáforos normalmente
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()
    
    def _alternar_fase(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']]) -> None:
        """Alterna entre fase horizontal e vertical."""
        if self.config['fase_atual'] == 'horizontal':
            # Muda para vertical (NORTE verde, LESTE vermelho)
            self._definir_fase_vertical(semaforos)
            self.config['fase_atual'] = 'vertical'
        else:
            # Muda para horizontal (LESTE verde, NORTE vermelho)
            self._definir_fase_horizontal(semaforos)
            self.config['fase_atual'] = 'horizontal'
    
    def _definir_fase_horizontal(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']]) -> None:
        """Define fase horizontal: LESTE verde, NORTE vermelho."""
        for semaforos_cruzamento in semaforos.values():
            if Direcao.LESTE in semaforos_cruzamento:
                semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.VERDE)
            if Direcao.NORTE in semaforos_cruzamento:
                semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.VERMELHO)
    
    def _definir_fase_vertical(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']]) -> None:
        """Define fase vertical: NORTE verde, LESTE vermelho."""
        for semaforos_cruzamento in semaforos.values():
            if Direcao.NORTE in semaforos_cruzamento:
                semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.VERDE)
            if Direcao.LESTE in semaforos_cruzamento:
                semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.VERMELHO)


class HeuristicaRandomOpenClose(Heuristica):
    """
    Heurística que muda aleatoriamente os estados dos semáforos,
    mas respeitando as interseções (não pode ter ambos abertos na mesma interseção).
    """
    
    def _inicializar_config(self) -> Dict:
        """Inicializa configurações para controle aleatório."""
        return {
            'intervalo_mudanca': 120,  # 2 segundos entre mudanças aleatórias
            'tempo_desde_ultima_mudanca': 0,
            'seed': 42  # Seed fixo para reproduzibilidade
        }
    
    def atualizar(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                  densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Atualização com mudanças aleatórias respeitando interseções."""
        self.config['tempo_desde_ultima_mudanca'] += 1
        
        # Verifica se é hora de fazer uma mudança aleatória
        if self.config['tempo_desde_ultima_mudanca'] >= self.config['intervalo_mudanca']:
            self._fazer_mudanca_aleatoria(semaforos)
            self.config['tempo_desde_ultima_mudanca'] = 0
        
        # Atualiza todos os semáforos normalmente
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()
    
    def _fazer_mudanca_aleatoria(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']]) -> None:
        """Faz mudanças aleatórias respeitando as interseções."""
        # Usa seed fixo para reproduzibilidade
        random.seed(self.config['seed'] + self.tempo_ciclo)
        
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            # Escolhe aleatoriamente qual direção abrir na interseção
            direcao_escolhida = random.choice([Direcao.NORTE, Direcao.LESTE])
            
            # Fecha ambas as direções primeiro
            if Direcao.NORTE in semaforos_cruzamento:
                semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.VERMELHO)
            if Direcao.LESTE in semaforos_cruzamento:
                semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.VERMELHO)
            
            # Abre a direção escolhida
            if direcao_escolhida in semaforos_cruzamento:
                semaforos_cruzamento[direcao_escolhida].forcar_mudanca(EstadoSemaforo.VERDE)


class HeuristicaManual(Heuristica):
    """Heurística de controle manual."""
    
    def _inicializar_config(self) -> Dict:
        """Inicializa configurações para controle manual."""
        return {}
    
    def atualizar(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                  densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Atualização manual - apenas atualiza semáforos sem lógica automática."""
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()
            self._verificar_alternancia_mao_unica(semaforos_cruzamento)


class HeuristicaLLM(Heuristica):
    """Heurística usando LLM para controle inteligente."""
    
    def __init__(self):
        """Inicializa a heurística LLM."""
        super().__init__()
        from llm_manager import LLMManager
        self.llm_manager = LLMManager()
    
    def _inicializar_config(self) -> Dict:
        """Inicializa configurações para LLM."""
        return {
            'intervalo_avaliacao': 120,  # Avalia densidade a cada 2 segundos
            'tempo_desde_avaliacao': 0
        }
    
    def atualizar(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                  densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Atualização usando LLM para controle inteligente - MÃO ÚNICA."""
        if not self.llm_manager or not self.llm_manager.llm_available:
            # Fallback to vertical/horizontal if LLM not available
            heuristica_fallback = HeuristicaVerticalHorizontal()
            heuristica_fallback.tempo_ciclo = self.tempo_ciclo
            heuristica_fallback.config = self.config.copy()
            heuristica_fallback.atualizar(semaforos, densidade_por_cruzamento)
            return
        
        # Check if it's time to evaluate
        if not self.llm_manager.should_evaluate(self.tempo_ciclo):
            # Just update semaphores normally without LLM decision
            for id_cruzamento, semaforos_cruzamento in semaforos.items():
                for semaforo in semaforos_cruzamento.values():
                    semaforo.atualizar()
                self._verificar_alternancia_mao_unica(semaforos_cruzamento)
            return
        
        try:
            # Prepare traffic state data
            global_metrics = {
                'total_vehicles': sum(sum(densidade.values()) for densidade in densidade_por_cruzamento.values()),
                'average_wait_time': 0,  # TODO: Calculate from vehicle data
                'traffic_density': 'medium'  # TODO: Calculate based on density
            }
            
            traffic_state = self.llm_manager.prepare_traffic_state(
                densidade_por_cruzamento, 
                semaforos, 
                global_metrics
            )
            
            # Get LLM decisions with timeout handling
            decisions = self.llm_manager.get_traffic_decisions(traffic_state, self.tempo_ciclo)
            
            if decisions:
                # Apply LLM decisions
                messages = self.llm_manager.apply_decisions(decisions, semaforos)
                if messages:
                    print(f"🤖 LLM Decisions: {', '.join(messages)}")
            else:
                # Fallback to vertical/horizontal if LLM fails
                print("⚠️ LLM failed, using fallback heuristic")
                heuristica_fallback = HeuristicaVerticalHorizontal()
                heuristica_fallback.tempo_ciclo = self.tempo_ciclo
                heuristica_fallback.config = self.config.copy()
                heuristica_fallback.atualizar(semaforos, densidade_por_cruzamento)
                return
                
        except Exception as e:
            print(f"❌ LLM heuristic error: {e}")
            # Fallback to vertical/horizontal
            heuristica_fallback = HeuristicaVerticalHorizontal()
            heuristica_fallback.tempo_ciclo = self.tempo_ciclo
            heuristica_fallback.config = self.config.copy()
            heuristica_fallback.atualizar(semaforos, densidade_por_cruzamento)
            return
        
        # Update all semaphores normally
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()
            self._verificar_alternancia_mao_unica(semaforos_cruzamento)


def criar_heuristica(tipo: TipoHeuristica) -> Heuristica:
    """
    Factory function para criar heurísticas baseado no tipo.
    
    Args:
        tipo: Tipo de heurística a ser criada
        
    Returns:
        Instância da heurística correspondente
    """
    heuristica_map = {
        TipoHeuristica.VERTICAL_HORIZONTAL: HeuristicaVerticalHorizontal,
        TipoHeuristica.RANDOM_OPEN_CLOSE: HeuristicaRandomOpenClose,
        TipoHeuristica.LLM_HEURISTICA: HeuristicaLLM,
        TipoHeuristica.MANUAL: HeuristicaManual
    }
    
    heuristica_class = heuristica_map.get(tipo)
    if not heuristica_class:
        raise ValueError(f"Tipo de heurística não suportado: {tipo}")
    
    return heuristica_class()