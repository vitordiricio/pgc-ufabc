"""
Gym environment for traffic control training.
Integrates with existing simulation system.
"""

import gymnasium as gym
import numpy as np
from typing import Dict, Tuple, Any, Optional
from configuracao import CONFIG, Direcao, EstadoSemaforo
from cruzamento import MalhaViaria


class TrafficRLEnvironment(gym.Env):
    """Gym environment for traffic control using RL."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        self._setup_spaces()
        self._reset_simulation()
        
    def _setup_spaces(self):
        """Setup observation and action spaces."""
        # Observation: density + states + timing for each intersection
        n_intersections = CONFIG.LINHAS_GRADE * CONFIG.COLUNAS_GRADE
        n_features_per_intersection = 6  # density_n, density_e, state_n, state_e, time_n, time_e
        self.observation_space = gym.spaces.Box(
            low=0, high=100, 
            shape=(n_intersections * n_features_per_intersection,), 
            dtype=np.float32
        )
        
        # Action: for each intersection, choose direction (0=maintain, 1=north, 2=east)
        self.action_space = gym.spaces.MultiDiscrete([3] * n_intersections)
        
    def _reset_simulation(self):
        """Reset the traffic simulation."""
        self.malha = MalhaViaria(CONFIG.LINHAS_GRADE, CONFIG.COLUNAS_GRADE)
        self.step_count = 0
        self.max_steps = self.config.get('max_steps', 3600)  # 1 hour at 1 FPS
        self.initial_vehicles = 0
        self.processed_vehicles = 0
        
    def reset(self) -> np.ndarray:
        """Reset environment and return initial observation."""
        self._reset_simulation()
        return self._get_observation()
        
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute one step in the environment."""
        # Apply action
        self._apply_action(action)
        
        # Advance simulation
        self.malha.atualizar()
        self.step_count += 1
        
        # Get new observation
        observation = self._get_observation()
        
        # Calculate reward
        reward = self._calculate_reward(action)
        
        # Check if done
        done = self.step_count >= self.max_steps
        
        # Info dict
        info = {
            'step_count': self.step_count,
            'total_vehicles': self._count_total_vehicles(),
            'average_wait_time': self._calculate_average_wait_time(),
            'throughput': self._calculate_throughput()
        }
        
        return observation, reward, done, info
        
    def _get_observation(self) -> np.ndarray:
        """Convert current state to observation vector."""
        obs = []
        
        # Get density data
        densidade_por_cruzamento = self.malha.obter_densidade_por_cruzamento()
        
        for id_cruzamento in sorted(self.malha.gerenciador_semaforos.semaforos.keys()):
            semaforos_cruzamento = self.malha.gerenciador_semaforos.semaforos[id_cruzamento]
            densidade = densidade_por_cruzamento.get(id_cruzamento, {})
            
            # Vehicle density (normalized to 0-10)
            obs.append(min(densidade.get(Direcao.NORTE, 0), 10))
            obs.append(min(densidade.get(Direcao.LESTE, 0), 10))
            
            # Traffic light states (one-hot)
            semaforo_norte = semaforos_cruzamento.get(Direcao.NORTE)
            semaforo_leste = semaforos_cruzamento.get(Direcao.LESTE)
            
            obs.extend([
                1 if semaforo_norte and semaforo_norte.estado == EstadoSemaforo.VERDE else 0,
                1 if semaforo_leste and semaforo_leste.estado == EstadoSemaforo.VERDE else 0
            ])
            
            # Time in current state (normalized to 0-10)
            obs.extend([
                min(semaforo_norte.tempo_no_estado if semaforo_norte else 0, 10),
                min(semaforo_leste.tempo_no_estado if semaforo_leste else 0, 10)
            ])
            
        return np.array(obs, dtype=np.float32)
        
    def _apply_action(self, action: np.ndarray):
        """Apply RL action to traffic lights."""
        for i, (id_cruzamento, semaforos_cruzamento) in enumerate(
            sorted(self.malha.gerenciador_semaforos.semaforos.items())
        ):
            if i < len(action):
                if action[i] == 1:  # Switch to north
                    if Direcao.NORTE in semaforos_cruzamento:
                        semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.VERDE)
                    if Direcao.LESTE in semaforos_cruzamento:
                        semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.VERMELHO)
                elif action[i] == 2:  # Switch to east
                    if Direcao.LESTE in semaforos_cruzamento:
                        semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.VERDE)
                    if Direcao.NORTE in semaforos_cruzamento:
                        semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.VERMELHO)
                # action[i] == 0: maintain current state
                
    def _calculate_reward(self, action: np.ndarray) -> float:
        """Calculate reward based on current state and action."""
        # Get current metrics
        total_vehicles = self._count_total_vehicles()
        wait_time = self._calculate_average_wait_time()
        throughput = self._calculate_throughput()
        
        # Reward components
        reward = (
            throughput * 0.1 -           # Encourage throughput
            wait_time * 0.01 -          # Penalize wait time
            len([a for a in action if a != 0]) * 0.05  # Penalize frequent changes
        )
        
        return float(reward)
        
    def _count_total_vehicles(self) -> int:
        """Count total vehicles in simulation."""
        return len([v for v in self.malha.veiculos if v.ativo])
        
    def _calculate_average_wait_time(self) -> float:
        """Calculate average wait time."""
        active_vehicles = [v for v in self.malha.veiculos if v.ativo]
        if not active_vehicles:
            return 0.0
        total_wait = sum(v.tempo_parado for v in active_vehicles)
        return total_wait / len(active_vehicles)
        
    def _calculate_throughput(self) -> float:
        """Calculate vehicles processed per time step."""
        # Count vehicles that completed their journey
        completed = len([v for v in self.malha.veiculos if not v.ativo and v.tempo_viagem > 0])
        return completed - self.processed_vehicles
    
    def render(self, mode='human'):
        """Render the environment (optional)."""
        pass
