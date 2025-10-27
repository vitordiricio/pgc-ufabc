"""
LLM Manager for traffic control using Ollama or OpenAI with structured output.
"""
import json
import os
from typing import Dict, List, Optional, Tuple
from ollama import chat
from openai import OpenAI
from pydantic import ValidationError
from dotenv import load_dotenv

from llm_models import TrafficControlResponse, TrafficStateData, IntersectionDecision, TrafficAction
from configuracao import CONFIG, Direcao, EstadoSemaforo

# Load environment variables
load_dotenv()


class LLMManager:
    """Manages LLM-based traffic control decisions using Ollama or OpenAI."""
    
    def __init__(self, engine: str = "ollama"):
        """
        Initialize the LLM manager.
        
        Args:
            engine: LLM engine to use ('ollama' or 'openai')
        """
        self.engine = engine
        self.last_evaluation_time = 0
        self.evaluation_interval = 600  # Evaluate every 10 seconds (600 frames at 60 FPS) - much reduced frequency
        self.response_cache = {}
        self.fallback_heuristica = "ADAPTATIVA_DENSIDADE"
        self.llm_available = False
        self.last_decision = None
        self.debug_mode = True  # Enable debug output
        
        # Set model name based on engine
        if engine == "ollama":
            self.model_name = os.getenv('OLLAMA_MODEL', 'gemma3:1b')
            self.llm_available = True  # Assume available, will fail gracefully on first call
        elif engine == "openai":
            self.model_name = os.getenv('OPENAI_MODEL', 'gpt-5-mini')
            self.api_key = os.getenv('OPENAI_API_KEY')
            if not self.api_key:
                print(f"❌ OPENAI_API_KEY not found in environment variables")
                print("LLM heuristic will use fallback strategy")
                self.llm_available = False
            else:
                self.llm_available = True  # Assume available, will fail gracefully on first call
        else:
            print(f"❌ Unknown engine: {engine}")
            self.llm_available = False
    
    def _call_llm(self, prompt: str, schema: dict) -> Optional[str]:
        """
        Call the appropriate LLM engine with structured output.
        
        Args:
            prompt: The prompt to send to the LLM
            schema: JSON schema for structured output
            
        Returns:
            str: JSON response from the LLM, or None if failed
        """
        try:
            if self.engine == "ollama":
                return self._call_ollama(prompt, schema)
            elif self.engine == "openai":
                return self._call_openai(prompt, schema)
            else:
                return None
        except Exception as e:
            print(f"❌ LLM call failed: {e}")
            return None
    
    def _call_ollama(self, prompt: str, schema: dict) -> Optional[str]:
        """Call Ollama API with structured output."""
        response = chat(
            messages=[{'role': 'user', 'content': prompt}],
            model=self.model_name,
            format=schema,
            options={
                'temperature': 0.1,  # Lower temperature for more consistent responses
            }
        )
        
        if self.debug_mode:
            print(f"🤖 LLM response received (type: {type(response)})")
            # Try to safely extract and print the content
            try:
                content = self._extract_content(response)
                if content:
                    print("🤖 LLM Response Content:")
                    print(content)
            except Exception as e:
                print(f"🤖 Could not extract content for display: {e}")
        
        # Parse response content using helper function
        content = self._extract_content(response)
        if content:
            return content
        
        # Fallback: convert to string if no content found
        return str(response)
    
    def _extract_content(self, response) -> Optional[str]:
        """Safely extract content from various response types."""
        if isinstance(response, dict):
            if 'message' in response:
                return response['message'].get('content')
            elif 'content' in response:
                return response['content']
        elif hasattr(response, 'message'):
            if hasattr(response.message, 'content'):
                return response.message.content
        elif hasattr(response, 'content'):
            return response.content
        return None
    
    def _call_openai(self, prompt: str, schema: dict) -> Optional[str]:
        """Call OpenAI API with structured output using .parse() method."""
        from llm_models import TrafficControlResponse
        client = OpenAI(api_key=self.api_key)
        
        # Use the official .parse() method for structured output
        response = client.responses.parse(
            model=self.model_name,
            input=[
                {'role': 'user', 'content': prompt}
            ],
            text_format=TrafficControlResponse
        )
        
        if self.debug_mode:
            print(f"🤖 LLM response received (type: {type(response)})")
            print("🤖 Response parsed successfully")
        
        # Extract the parsed output and convert back to JSON
        if response.output_parsed:
            # Convert back to JSON string for consistency with Ollama
            return response.output_parsed.model_dump_json()
        return None
    
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
            
            # Get schema for structured output
            schema = TrafficControlResponse.model_json_schema()
            
            # Call LLM with abstraction layer
            content = self._call_llm(prompt, schema)
            
            if not content:
                return self.last_decision
            
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
            # Convert list to tuple for dictionary key lookup
            intersection_id = tuple(decision.intersection_id)
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
