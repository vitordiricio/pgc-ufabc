"""
Módulo de heurísticas para controle de semáforos.
Implementa padrão Strategy para diferentes algoritmos de controle.
"""
from abc import ABC, abstractmethod
from typing import Dict, Tuple, TYPE_CHECKING
from configuracao import TipoHeuristica, EstadoSemaforo, Direcao, CONFIG

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
    
    def _ajustar_tempos_por_densidade(self, semaforos: Dict[Direcao, 'Semaforo'], 
                                     densidade: Dict[Direcao, int]) -> None:
        """Ajusta os tempos dos semáforos baseado na densidade - MÃO ÚNICA."""
        for direcao, semaforo in semaforos.items():
            if direcao not in CONFIG.DIRECOES_PERMITIDAS:
                continue
                
            qtd_veiculos = densidade.get(direcao, 0)
            
            if qtd_veiculos <= CONFIG.LIMIAR_DENSIDADE_BAIXA:
                tempo_verde = CONFIG.TEMPO_VERDE_DENSIDADE_BAIXA
            elif qtd_veiculos <= CONFIG.LIMIAR_DENSIDADE_MEDIA:
                tempo_verde = CONFIG.TEMPO_VERDE_DENSIDADE_MEDIA
            else:
                tempo_verde = CONFIG.TEMPO_VERDE_DENSIDADE_ALTA
            
            semaforo.definir_tempo_verde(tempo_verde)


class HeuristicaTempoFixo(Heuristica):
    """Heurística com tempos fixos e alternância simples."""
    
    def _inicializar_config(self) -> Dict:
        """Inicializa configurações para tempo fixo."""
        return {}
    
    def atualizar(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                  densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Atualização com tempos fixos e alternância simples - MÃO ÚNICA."""
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            # Atualiza cada semáforo
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()
            
            # Verifica alternância simples entre Norte e Leste
            self._verificar_alternancia_mao_unica(semaforos_cruzamento)


class HeuristicaAdaptativaSimples(Heuristica):
    """Heurística adaptativa baseada em densidade simples."""
    
    def _inicializar_config(self) -> Dict:
        """Inicializa configurações para adaptativa simples."""
        return {}
    
    def atualizar(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                  densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Atualização adaptativa baseada em densidade simples - MÃO ÚNICA."""
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            densidade_cruzamento = densidade_por_cruzamento.get(id_cruzamento, {})
            
            # Calcula densidade para cada direção
            densidade_norte = densidade_cruzamento.get(Direcao.NORTE, 0)
            densidade_leste = densidade_cruzamento.get(Direcao.LESTE, 0)
            
            # Ajusta tempos baseado na densidade
            for direcao, semaforo in semaforos_cruzamento.items():
                if direcao == Direcao.NORTE:
                    if densidade_norte > densidade_leste * 1.5:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_ALTA)
                    else:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_MEDIA)
                elif direcao == Direcao.LESTE:
                    if densidade_leste > densidade_norte * 1.5:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_ALTA)
                    else:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_MEDIA)
                
                semaforo.atualizar()
            
            self._verificar_alternancia_mao_unica(semaforos_cruzamento)


class HeuristicaAdaptativaDensidade(Heuristica):
    """Heurística adaptativa com análise detalhada de densidade."""
    
    def _inicializar_config(self) -> Dict:
        """Inicializa configurações para adaptativa densidade."""
        return {
            'intervalo_avaliacao': 120,  # Avalia densidade a cada 2 segundos
            'tempo_desde_avaliacao': 0
        }
    
    def atualizar(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                  densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Atualização adaptativa com análise detalhada de densidade - MÃO ÚNICA."""
        self.config['tempo_desde_avaliacao'] += 1
        
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            # Atualiza normalmente
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()
            
            # Avalia densidade periodicamente
            if self.config['tempo_desde_avaliacao'] >= self.config['intervalo_avaliacao']:
                densidade_cruzamento = densidade_por_cruzamento.get(id_cruzamento, {})
                self._ajustar_tempos_por_densidade(semaforos_cruzamento, densidade_cruzamento)
            
            self._verificar_alternancia_mao_unica(semaforos_cruzamento)
        
        if self.config['tempo_desde_avaliacao'] >= self.config['intervalo_avaliacao']:
            self.config['tempo_desde_avaliacao'] = 0


class HeuristicaWaveGreen(Heuristica):
    """Heurística de onda verde para fluxo contínuo."""
    
    def _inicializar_config(self) -> Dict:
        """Inicializa configurações para onda verde."""
        return {
            'offset_por_cruzamento': 60,  # 1 segundo de offset entre cruzamentos
            'direcao_onda': Direcao.LESTE  # Direção prioritária da onda verde
        }
    
    def atualizar(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                  densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Atualização com onda verde para fluxo contínuo - MÃO ÚNICA."""
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            # Calcula offset baseado na posição do cruzamento
            offset = id_cruzamento[1] * self.config['offset_por_cruzamento']
            
            # Determina fase atual considerando offset
            fase_ajustada = (self.tempo_ciclo + offset) % 480  # Ciclo completo de 8 segundos
            
            # Define estados baseado na fase - simplificado para mão única
            if fase_ajustada < 180:  # Primeiros 3 segundos - prioridade horizontal
                # Leste verde, Norte vermelho
                if Direcao.LESTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.LESTE].estado != EstadoSemaforo.VERDE:
                        semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.VERDE)
                if Direcao.NORTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.NORTE].estado != EstadoSemaforo.VERMELHO:
                        semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.VERMELHO)
            elif fase_ajustada < 240:  # 1 segundo amarelo
                if Direcao.LESTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.LESTE].estado == EstadoSemaforo.VERDE:
                        semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.AMARELO)
            elif fase_ajustada < 420:  # 3 segundos - prioridade vertical
                # Norte verde, Leste vermelho
                if Direcao.NORTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.NORTE].estado != EstadoSemaforo.VERDE:
                        semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.VERDE)
                if Direcao.LESTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.LESTE].estado != EstadoSemaforo.VERMELHO:
                        semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.VERMELHO)
            else:  # Último segundo amarelo
                if Direcao.NORTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.NORTE].estado == EstadoSemaforo.VERDE:
                        semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.AMARELO)
            
            # Atualiza os semáforos
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()


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
            # Fallback to adaptive density if LLM not available
            heuristica_fallback = HeuristicaAdaptativaDensidade()
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
                # Fallback to adaptive density if LLM fails
                print("⚠️ LLM failed, using fallback heuristic")
                heuristica_fallback = HeuristicaAdaptativaDensidade()
                heuristica_fallback.tempo_ciclo = self.tempo_ciclo
                heuristica_fallback.config = self.config.copy()
                heuristica_fallback.atualizar(semaforos, densidade_por_cruzamento)
                return
                
        except Exception as e:
            print(f"❌ LLM heuristic error: {e}")
            # Fallback to adaptive density
            heuristica_fallback = HeuristicaAdaptativaDensidade()
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
        TipoHeuristica.TEMPO_FIXO: HeuristicaTempoFixo,
        TipoHeuristica.ADAPTATIVA_SIMPLES: HeuristicaAdaptativaSimples,
        TipoHeuristica.ADAPTATIVA_DENSIDADE: HeuristicaAdaptativaDensidade,
        TipoHeuristica.WAVE_GREEN: HeuristicaWaveGreen,
        TipoHeuristica.MANUAL: HeuristicaManual,
        TipoHeuristica.LLM_HEURISTICA: HeuristicaLLM
    }
    
    heuristica_class = heuristica_map.get(tipo)
    if not heuristica_class:
        raise ValueError(f"Tipo de heurística não suportado: {tipo}")
    
    return heuristica_class()
