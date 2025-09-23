"""
LLM Manager for traffic control using Ollama with structured output.
"""
import json
from typing import Dict, List, Optional, Tuple
from ollama import chat
from pydantic import ValidationError
import json

from llm_models import TrafficControlResponse, TrafficStateData, IntersectionDecision, TrafficAction
from configuracao import CONFIG, Direcao, EstadoSemaforo


class LLMManager:
    """Manages LLM-based traffic control decisions using Ollama."""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        """
        Initialize the LLM manager.
        
        Args:
            model_name: Name of the Ollama model to use
        """
        self.model_name = model_name
        self.last_evaluation_time = 0
        self.evaluation_interval = 600  # Evaluate every 10 seconds (600 frames at 60 FPS) - much reduced frequency
        self.response_cache = {}
        self.fallback_heuristica = "ADAPTATIVA_DENSIDADE"
        self.llm_available = False
        self.last_decision = None
        self.debug_mode = True  # Enable debug output
        
        # Connection test
        self.llm_available = self._test_connection()
    
    def _test_connection(self) -> bool:
        """Test connection to Ollama service."""
        try:
            response = chat(
                messages=[{'role': 'user', 'content': 'Hello'}],
                model=self.model_name
            )
            print(f"✅ Connected to Ollama model: {self.model_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Ollama: {e}")
            print("LLM heuristic will use fallback strategy")
            return False
    
    def should_evaluate(self, current_time: int) -> bool:
        """
        Check if it's time to evaluate traffic conditions.
        
        Args:
            current_time: Current simulation time in frames
            
        Returns:
            bool: True if evaluation should occur
        """
        return current_time - self.last_evaluation_time >= self.evaluation_interval
    
    def prepare_traffic_state(self, 
                            densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]],
                            semaforos: Dict[Tuple[int, int], Dict[Direcao, any]],
                            global_metrics: Dict) -> TrafficStateData:
        """
        Prepare traffic state data for LLM analysis.
        
        Args:
            densidade_por_cruzamento: Vehicle density per intersection
            semaforos: Current traffic light states
            global_metrics: Overall simulation metrics
            
        Returns:
            TrafficStateData: Formatted data for LLM
        """
        intersections = []
        
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            densidade = densidade_por_cruzamento.get(id_cruzamento, {})
            
            # Get semaforo objects safely
            semaforo_norte = semaforos_cruzamento.get(Direcao.NORTE)
            semaforo_leste = semaforos_cruzamento.get(Direcao.LESTE)
            
            intersection_data = {
                "id": id_cruzamento,
                "north_vehicles": densidade.get(Direcao.NORTE, 0),
                "east_vehicles": densidade.get(Direcao.LESTE, 0),
                "north_wait_time": 0,  # TODO: Calculate from vehicle data
                "east_wait_time": 0,   # TODO: Calculate from vehicle data
                "current_states": {
                    "north": semaforo_norte.estado.name if semaforo_norte else 'UNKNOWN',
                    "east": semaforo_leste.estado.name if semaforo_leste else 'UNKNOWN'
                },
                "north_time_in_state": semaforo_norte.tempo_no_estado if semaforo_norte else 0,
                "east_time_in_state": semaforo_leste.tempo_no_estado if semaforo_leste else 0
            }
            intersections.append(intersection_data)
        
        return TrafficStateData(
            intersections=intersections,
            global_metrics=global_metrics,
            time_since_last_change=0,  # TODO: Track this
            current_heuristica="LLM_HEURISTICA"
        )
    
    def generate_prompt(self, traffic_state: TrafficStateData) -> str:
        """
        Generate a prompt for the LLM based on traffic state.
        
        Args:
            traffic_state: Current traffic conditions
            
        Returns:
            str: Formatted prompt for the LLM
        """
        # Simplified prompt for faster response
        intersections_summary = []
        for intersection in traffic_state.intersections:
            intersections_summary.append(
                f"Intersection {intersection['id']}: North={intersection['north_vehicles']} vehicles, "
                f"East={intersection['east_vehicles']} vehicles, "
                f"States: North={intersection['current_states']['north']}, East={intersection['current_states']['east']}"
            )
        
        prompt = f"""Traffic lights: {chr(10).join(intersections_summary)}

Rules: One direction green per intersection. Prioritize higher vehicle counts.
Make 1-2 decisions max."""
        
        return prompt
    
    def get_traffic_decisions(self, traffic_state: TrafficStateData, current_time: int = 0) -> Optional[TrafficControlResponse]:
        """
        Get traffic control decisions from the LLM.
        
        Args:
            traffic_state: Current traffic conditions
            
        Returns:
            TrafficControlResponse or None if failed
        """
        if not self.llm_available:
            return None
            
        try:
            prompt = self.generate_prompt(traffic_state)
            
            if self.debug_mode:
                print(f"🤖 Sending prompt to LLM (length: {len(prompt)} chars)")
            
            # Add timeout and simplified prompt for faster response
            response = chat(
                messages=[{'role': 'user', 'content': prompt}],
                model=self.model_name,
                format=TrafficControlResponse.model_json_schema(),
                options={
                    'temperature': 0.1,  # Lower temperature for more consistent responses
                }
            )
            
            if self.debug_mode:
                print(f"🤖 LLM response received (type: {type(response)})")
                # Pretty-print the entire Ollama response including all metadata
                print("🤖 Complete LLM Response:")
                print(json.dumps(response, indent=2, ensure_ascii=False))
            
            # Parse and validate the response - handle different response formats
            if isinstance(response, dict) and 'message' in response:
                content = response['message']['content']
            elif hasattr(response, 'message') and hasattr(response.message, 'content'):
                content = response.message.content
            elif hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, dict) and 'content' in response:
                content = response['content']
            else:
                content = str(response)
            
            decisions = TrafficControlResponse.model_validate_json(content)
            
            # Update evaluation time (current_time is already in frames)
            self.last_evaluation_time = current_time
            self.last_decision = decisions
            
            return decisions
            
        except ValidationError as e:
            print(f"❌ LLM response validation failed: {e}")
            return self.last_decision  # Use last valid decision
        except Exception as e:
            print(f"❌ LLM request failed: {e}")
            return self.last_decision  # Use last valid decision
    
    def apply_decisions(self, 
                       decisions: TrafficControlResponse,
                       semaforos: Dict[Tuple[int, int], Dict[Direcao, any]]) -> List[str]:
        """
        Apply LLM decisions to traffic lights.
        
        Args:
            decisions: LLM traffic control decisions
            semaforos: Traffic light objects to modify
            
        Returns:
            List[str]: Messages about applied changes
        """
        messages = []
        
        for decision in decisions.decisions:
            intersection_id = decision.intersection_id
            direction_str = decision.direction
            action = decision.action
            
            if intersection_id not in semaforos:
                continue
                
            # Convert direction string to enum
            direction = Direcao.NORTE if direction_str.upper() == "NORTH" else Direcao.LESTE
            
            if direction not in semaforos[intersection_id]:
                continue
                
            semaforo = semaforos[intersection_id][direction]
            
            # Apply the decision
            if action == TrafficAction.CHANGE_TO_GREEN:
                if semaforo.estado != EstadoSemaforo.VERDE:
                    semaforo.forcar_mudanca(EstadoSemaforo.VERDE)
                    messages.append(f"Intersection {intersection_id} {direction_str}: Changed to GREEN")
            elif action == TrafficAction.CHANGE_TO_RED:
                if semaforo.estado != EstadoSemaforo.VERMELHO:
                    semaforo.forcar_mudanca(EstadoSemaforo.VERMELHO)
                    messages.append(f"Intersection {intersection_id} {direction_str}: Changed to RED")
            elif action == TrafficAction.EXTEND_GREEN:
                if semaforo.estado == EstadoSemaforo.VERDE:
                    # Extend green time by 60 frames (1 second)
                    semaforo.definir_tempo_verde(semaforo.tempo_maximo_estado + 60)
                    messages.append(f"Intersection {intersection_id} {direction_str}: Extended GREEN time")
            # KEEP_CURRENT requires no action
        
        return messages
