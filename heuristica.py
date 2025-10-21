"""
Módulo de heurísticas para controle de semáforos.
Implementa padrão Strategy para diferentes algoritmos de controle.
"""
from abc import ABC, abstractmethod
from typing import Dict, Tuple, TYPE_CHECKING
import random
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


class HeuristicaAdaptativaDensidade(Heuristica):
    """
    Heurística adaptativa baseada em densidade de veículos.
    Ajusta dinamicamente os tempos dos semáforos baseado na densidade atual e histórica.
    """
    
    def _inicializar_config(self) -> Dict:
        """Inicializa configurações para controle adaptativo de densidade."""
        return {
            'intervalo_avaliacao': 60,  # Avalia densidade a cada 1 segundo
            'tempo_desde_avaliacao': 0,
            'historico_densidade': {},  # Histórico de densidade por cruzamento
            'tempos_base': {
                'verde_minimo': 90,    # 1.5 segundos mínimo
                'verde_maximo': 360,   # 6 segundos máximo
                'verde_padrao': 180,   # 3 segundos padrão
                'amarelo': 60,         # 1 segundo
                'vermelho_minimo': 120 # 2 segundos mínimo
            },
            'limiares_densidade': {
                'baixa': 2,    # 0-2 veículos
                'media': 5,    # 3-5 veículos
                'alta': 8      # 6+ veículos
            },
            'fatores_ajuste': {
                'baixa': 0.7,   # Reduz tempo em 30%
                'media': 1.0,   # Tempo padrão
                'alta': 1.5     # Aumenta tempo em 50%
            },
            'prioridade_zones': {},  # Zonas de prioridade por cruzamento
            'tempo_ultima_mudanca': {}  # Controle de mudanças frequentes
        }
    
    def atualizar(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                  densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Atualização adaptativa baseada em densidade."""
        self.config['tempo_desde_avaliacao'] += 1
        
        # Verifica se é hora de avaliar e ajustar
        if self.config['tempo_desde_avaliacao'] >= self.config['intervalo_avaliacao']:
            self._avaliar_e_ajustar_densidade(semaforos, densidade_por_cruzamento)
            self.config['tempo_desde_avaliacao'] = 0
        
        # Atualiza todos os semáforos normalmente
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()
            self._verificar_alternancia_mao_unica(semaforos_cruzamento)
    
    def _avaliar_e_ajustar_densidade(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                                   densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Avalia densidade atual e ajusta tempos dos semáforos."""
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            densidade = densidade_por_cruzamento.get(id_cruzamento, {})
            
            # Atualiza histórico de densidade
            self._atualizar_historico_densidade(id_cruzamento, densidade)
            
            # Calcula densidade média e tendência
            densidade_media, tendencia = self._calcular_metricas_densidade(id_cruzamento)
            
            # Determina prioridade do cruzamento
            prioridade = self._calcular_prioridade_cruzamento(id_cruzamento, densidade_media, tendencia)
            
            # Ajusta tempos baseado na densidade e prioridade
            self._ajustar_tempos_semaforos(semaforos_cruzamento, densidade, prioridade)
    
    def _atualizar_historico_densidade(self, id_cruzamento: Tuple[int, int], 
                                     densidade_atual: Dict[Direcao, int]) -> None:
        """Atualiza o histórico de densidade para um cruzamento."""
        if id_cruzamento not in self.config['historico_densidade']:
            self.config['historico_densidade'][id_cruzamento] = {
                Direcao.NORTE: [],
                Direcao.LESTE: []
            }
        
        # Adiciona densidade atual ao histórico (mantém últimos 10 registros)
        for direcao in [Direcao.NORTE, Direcao.LESTE]:
            historico = self.config['historico_densidade'][id_cruzamento][direcao]
            historico.append(densidade_atual.get(direcao, 0))
            if len(historico) > 10:
                historico.pop(0)
    
    def _calcular_metricas_densidade(self, id_cruzamento: Tuple[int, int]) -> Tuple[float, str]:
        """Calcula densidade média e tendência para um cruzamento."""
        if id_cruzamento not in self.config['historico_densidade']:
            return 0.0, 'estavel'
        
        historico = self.config['historico_densidade'][id_cruzamento]
        
        # Calcula densidade total média (NORTE + LESTE)
        densidade_total = []
        for direcao in [Direcao.NORTE, Direcao.LESTE]:
            if historico[direcao]:
                densidade_total.extend(historico[direcao])
        
        if not densidade_total:
            return 0.0, 'estavel'
        
        densidade_media = sum(densidade_total) / len(densidade_total)
        
        # Calcula tendência (comparando primeiros vs últimos registros)
        if len(densidade_total) >= 6:
            primeira_metade = sum(densidade_total[:3]) / 3
            segunda_metade = sum(densidade_total[-3:]) / 3
            
            if segunda_metade > primeira_metade * 1.2:
                tendencia = 'crescendo'
            elif segunda_metade < primeira_metade * 0.8:
                tendencia = 'diminuindo'
            else:
                tendencia = 'estavel'
        else:
            tendencia = 'estavel'
        
        return densidade_media, tendencia
    
    def _calcular_prioridade_cruzamento(self, id_cruzamento: Tuple[int, int], 
                                      densidade_media: float, tendencia: str) -> float:
        """Calcula prioridade de um cruzamento baseado em densidade e tendência."""
        prioridade_base = densidade_media
        
        # Ajusta prioridade baseado na tendência
        if tendencia == 'crescendo':
            prioridade_base *= 1.3  # Aumenta prioridade se densidade está crescendo
        elif tendencia == 'diminuindo':
            prioridade_base *= 0.8  # Diminui prioridade se densidade está diminuindo
        
        # Aplica prioridade de zona
        fator_zona = self._calcular_prioridade_zona(id_cruzamento)
        
        return prioridade_base * fator_zona
    
    def _ajustar_tempos_semaforos(self, semaforos_cruzamento: Dict[Direcao, 'Semaforo'], 
                                densidade: Dict[Direcao, int], prioridade: float) -> None:
        """Ajusta os tempos dos semáforos baseado na densidade e prioridade."""
        tempos_base = self.config['tempos_base']
        limiares = self.config['limiares_densidade']
        fatores = self.config['fatores_ajuste']
        
        # Determina qual direção tem mais veículos
        densidade_norte = densidade.get(Direcao.NORTE, 0)
        densidade_leste = densidade.get(Direcao.LESTE, 0)
        
        # Calcula fator de ajuste baseado na densidade
        densidade_total = densidade_norte + densidade_leste
        if densidade_total <= limiares['baixa']:
            fator_densidade = fatores['baixa']
        elif densidade_total <= limiares['media']:
            fator_densidade = fatores['media']
        else:
            fator_densidade = fatores['alta']
        
        # Aplica fator de prioridade
        fator_final = fator_densidade * (1.0 + prioridade * 0.1)
        
        # Calcula novo tempo verde
        tempo_verde_novo = int(tempos_base['verde_padrao'] * fator_final)
        tempo_verde_novo = max(tempos_base['verde_minimo'], 
                              min(tempos_base['verde_maximo'], tempo_verde_novo))
        
        # Aplica ajustes aos semáforos
        for direcao, semaforo in semaforos_cruzamento.items():
            if semaforo.estado == EstadoSemaforo.VERDE:
                # Prediz tamanho da fila para esta direção
                fila_predita = self._prever_tamanho_fila(semaforo.id_cruzamento, direcao)
                
                # Ajusta tempo do verde atual
                tempo_restante = semaforo.tempo_maximo_estado - semaforo.tempo_no_estado
                if tempo_restante < 30:  # Se está próximo de mudar
                    # Estende o verde se a densidade ou fila predita justifica
                    if densidade.get(direcao, 0) > 3 or fila_predita > 4:
                        tempo_estendido = int(tempo_verde_novo * 1.2)  # Estende 20% extra
                        semaforo.definir_tempo_verde(tempo_estendido)
                else:
                    # Ajusta para o próximo ciclo baseado na fila predita
                    if fila_predita > 6:
                        tempo_ajustado = int(tempo_verde_novo * 1.3)  # Aumenta 30% para filas grandes
                    elif fila_predita < 2:
                        tempo_ajustado = int(tempo_verde_novo * 0.8)  # Reduz 20% para filas pequenas
                    else:
                        tempo_ajustado = tempo_verde_novo
                    
                    semaforo.definir_tempo_verde(tempo_ajustado)
    
    def _prever_tamanho_fila(self, id_cruzamento: Tuple[int, int], direcao: Direcao) -> int:
        """Prediz o tamanho da fila baseado no histórico de densidade."""
        if id_cruzamento not in self.config['historico_densidade']:
            return 0
        
        historico = self.config['historico_densidade'][id_cruzamento][direcao]
        if len(historico) < 3:
            return historico[-1] if historico else 0
        
        # Calcula tendência simples (média móvel)
        recente = sum(historico[-3:]) / 3
        anterior = sum(historico[-6:-3]) / 3 if len(historico) >= 6 else recente
        
        # Prediz crescimento da fila
        if recente > anterior * 1.1:
            return int(recente * 1.2)  # Prediz crescimento de 20%
        elif recente < anterior * 0.9:
            return int(recente * 0.8)  # Prediz redução de 20%
        else:
            return int(recente)  # Mantém estável
    
    def _calcular_prioridade_zona(self, id_cruzamento: Tuple[int, int]) -> float:
        """Calcula prioridade baseada na zona do cruzamento."""
        # Zonas de prioridade: centro > bordas > cantos
        centro_x = CONFIG.COLUNAS_GRADE // 2
        centro_y = CONFIG.LINHAS_GRADE // 2
        
        distancia_centro = abs(id_cruzamento[0] - centro_x) + abs(id_cruzamento[1] - centro_y)
        
        # Prioridade decresce com distância do centro
        if distancia_centro == 0:
            return 1.2  # Centro - máxima prioridade
        elif distancia_centro == 1:
            return 1.0  # Adjacente ao centro
        elif distancia_centro == 2:
            return 0.8  # Bordas
        else:
            return 0.6  # Cantos


class HeuristicaReinforcementLearning(Heuristica):
    """
    Heurística baseada em Reinforcement Learning para controle de semáforos.
    Usa PPO (Proximal Policy Optimization) para aprender políticas ótimas.
    """
    
    def __init__(self):
        """Inicializa a heurística RL."""
        super().__init__()
        self.agent = None
        self.model_loaded = False
        self.fallback_heuristica = None
        
        # Preload the model to avoid freezing during simulation
        print("🔄 Loading RL model...")
        self._load_agent()
    
    def _inicializar_config(self) -> Dict:
        """Inicializa configurações para RL."""
        return {
            'intervalo_avaliacao': 60,  # Avalia a cada 1 segundo
            'tempo_desde_avaliacao': 0,
            'model_path': 'rl/models/best_model.zip',  # Use best model by default
            'model_loaded': False,
            'fallback_enabled': True
        }
    
    def _load_agent(self):
        """Carrega o agente RL."""
        if self.model_loaded:
            return True
            
        try:
            from rl import RLTrafficAgent
            self.agent = RLTrafficAgent(model_path=self.config['model_path'])
            self.model_loaded = True
            print("✅ RL Agent loaded successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to load RL agent: {e}")
            if self.config['fallback_enabled']:
                print("🔄 Using Adaptive Density as fallback")
                self.fallback_heuristica = HeuristicaAdaptativaDensidade()
            return False
    
    def atualizar(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                  densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Atualização usando RL."""
        self.config['tempo_desde_avaliacao'] += 1
        
        # Tenta carregar o agente se ainda não foi carregado
        if not self.model_loaded:
            if not self._load_agent():
                # Usa fallback se não conseguir carregar
                if self.fallback_heuristica:
                    self.fallback_heuristica.atualizar(semaforos, densidade_por_cruzamento)
                return
        
        # Verifica se é hora de avaliar e tomar ação
        if self.config['tempo_desde_avaliacao'] >= self.config['intervalo_avaliacao']:
            self._take_rl_action(semaforos, densidade_por_cruzamento)
            self.config['tempo_desde_avaliacao'] = 0
        
        # Atualiza todos os semáforos normalmente
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()
            self._verificar_alternancia_mao_unica(semaforos_cruzamento)
    
    def _take_rl_action(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                       densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """Toma ação baseada no modelo RL."""
        try:
            # Converte estado atual em observação
            observation = self._get_observation(semaforos, densidade_por_cruzamento)
            
            # Prediz ação
            action = self.agent.predict(observation, deterministic=True)
            
            # Aplica ação
            self._apply_action(action, semaforos)
            
        except Exception as e:
            print(f"❌ RL action failed: {e}")
            # Fallback para heurística adaptativa
            if self.fallback_heuristica:
                self.fallback_heuristica.atualizar(semaforos, densidade_por_cruzamento)
    
    def _get_observation(self, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']], 
                        densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]):
        """Converte estado atual em observação para o modelo RL."""
        import numpy as np
        
        obs = []
        
        for id_cruzamento in sorted(semaforos.keys()):
            semaforos_cruzamento = semaforos[id_cruzamento]
            densidade = densidade_por_cruzamento.get(id_cruzamento, {})
            
            # Densidade de veículos (normalizada)
            obs.append(min(densidade.get(Direcao.NORTE, 0), 10))
            obs.append(min(densidade.get(Direcao.LESTE, 0), 10))
            
            # Estados dos semáforos (one-hot)
            semaforo_norte = semaforos_cruzamento.get(Direcao.NORTE)
            semaforo_leste = semaforos_cruzamento.get(Direcao.LESTE)
            
            obs.extend([
                1 if semaforo_norte and semaforo_norte.estado == EstadoSemaforo.VERDE else 0,
                1 if semaforo_leste and semaforo_leste.estado == EstadoSemaforo.VERDE else 0
            ])
            
            # Tempo no estado atual (normalizado)
            obs.extend([
                min(semaforo_norte.tempo_no_estado if semaforo_norte else 0, 10),
                min(semaforo_leste.tempo_no_estado if semaforo_leste else 0, 10)
            ])
            
        return np.array(obs, dtype=np.float32)
    
    def _apply_action(self, action, semaforos: Dict[Tuple[int, int], Dict[Direcao, 'Semaforo']]) -> None:
        """Aplica ação do modelo RL aos semáforos."""
        for i, (id_cruzamento, semaforos_cruzamento) in enumerate(sorted(semaforos.items())):
            if i < len(action):
                if action[i] == 1:  # Mudar para norte
                    if Direcao.NORTE in semaforos_cruzamento:
                        semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.VERDE)
                    if Direcao.LESTE in semaforos_cruzamento:
                        semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.VERMELHO)
                elif action[i] == 2:  # Mudar para leste
                    if Direcao.LESTE in semaforos_cruzamento:
                        semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.VERDE)
                    if Direcao.NORTE in semaforos_cruzamento:
                        semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.VERMELHO)
                # action[i] == 0: manter estado atual


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
        TipoHeuristica.ADAPTATIVA_DENSIDADE: HeuristicaAdaptativaDensidade,
        TipoHeuristica.REINFORCEMENT_LEARNING: HeuristicaReinforcementLearning,
        TipoHeuristica.MANUAL: HeuristicaManual
    }
    
    heuristica_class = heuristica_map.get(tipo)
    if not heuristica_class:
        raise ValueError(f"Tipo de heurística não suportado: {tipo}")
    
    return heuristica_class()