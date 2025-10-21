"""
LLM managers responsible for orchestrating traffic control decisions via
different large language model providers.
"""
import json
import os
from typing import Dict, List, Optional, Tuple

from ollama import chat
from openai import OpenAI
from pydantic import ValidationError

from llm_models import (
    TrafficControlResponse,
    TrafficStateData,
    IntersectionDecision,
    TrafficAction,
)
from configuracao import CONFIG, Direcao, EstadoSemaforo


class BaseLLMManager:
    """Common behaviour shared by LLM backends."""

    def __init__(self, evaluation_interval: int = 600):
        self.last_evaluation_time = 0
        self.evaluation_interval = evaluation_interval
        self.response_cache: Dict = {}
        self.fallback_heuristica = "ADAPTATIVA_DENSIDADE"
        self.llm_available = False
        self.last_decision: Optional[TrafficControlResponse] = None
        self.debug_mode = True  # Enable debug output

    def should_evaluate(self, current_time: int) -> bool:
        """Check if it's time to evaluate traffic conditions."""

        return current_time - self.last_evaluation_time >= self.evaluation_interval

    def prepare_traffic_state(
        self,
        densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]],
        semaforos: Dict[Tuple[int, int], Dict[Direcao, any]],
        global_metrics: Dict,
    ) -> TrafficStateData:
        """Prepare traffic state data for LLM analysis."""

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
                "east_wait_time": 0,  # TODO: Calculate from vehicle data
                "current_states": {
                    "north": semaforo_norte.estado.name if semaforo_norte else "UNKNOWN",
                    "east": semaforo_leste.estado.name if semaforo_leste else "UNKNOWN",
                },
                "north_time_in_state": semaforo_norte.tempo_no_estado if semaforo_norte else 0,
                "east_time_in_state": semaforo_leste.tempo_no_estado if semaforo_leste else 0,
            }
            intersections.append(intersection_data)

        return TrafficStateData(
            intersections=intersections,
            global_metrics=global_metrics,
            time_since_last_change=0,  # TODO: Track this
            current_heuristica="LLM_HEURISTICA",
        )

    def generate_prompt(self, traffic_state: TrafficStateData) -> str:
        """Generate a prompt for the LLM based on traffic state."""

        intersections_summary = []
        for intersection in traffic_state.intersections:
            intersections_summary.append(
                f"Intersection {intersection['id']}: North={intersection['north_vehicles']} vehicles, "
                f"East={intersection['east_vehicles']} vehicles, "
                f"States: North={intersection['current_states']['north']}, East={intersection['current_states']['east']}"
            )

        prompt = (
            "Traffic lights: "
            + os.linesep.join(intersections_summary)
            + f"{os.linesep}{os.linesep}Rules: One direction green per intersection. "
            "Prioritize higher vehicle counts.\nMake 1-2 decisions max."
        )

        return prompt

    def apply_decisions(
        self,
        decisions: TrafficControlResponse,
        semaforos: Dict[Tuple[int, int], Dict[Direcao, any]],
    ) -> List[str]:
        """Apply LLM decisions to traffic lights."""

        messages = []

        for decision in decisions.decisions:
            intersection_id = tuple(decision.intersection_id)
            direcao_str = decision.direction.upper()
            action = decision.action

            semaforos_cruzamento = semaforos.get(intersection_id)
            if not semaforos_cruzamento:
                continue

            if direcao_str == "NORTH":
                direcao = Direcao.NORTE
            elif direcao_str == "EAST":
                direcao = Direcao.LESTE
            else:
                continue

            semaforo = semaforos_cruzamento.get(direcao)
            if not semaforo:
                continue

            if action == TrafficAction.CHANGE_TO_GREEN:
                semaforo.forcar_mudanca(EstadoSemaforo.VERDE)
                # Ensure perpendicular direction is red
                outra_direcao = Direcao.LESTE if direcao == Direcao.NORTE else Direcao.NORTE
                outro_semaforo = semaforos_cruzamento.get(outra_direcao)
                if outro_semaforo:
                    outro_semaforo.forcar_mudanca(EstadoSemaforo.VERMELHO)
                messages.append(
                    f"Intersection {intersection_id}: {direcao.name} -> GREEN ({decision.reasoning})"
                )
            elif action == TrafficAction.CHANGE_TO_RED:
                semaforo.forcar_mudanca(EstadoSemaforo.VERMELHO)
                messages.append(
                    f"Intersection {intersection_id}: {direcao.name} -> RED ({decision.reasoning})"
                )
            elif action == TrafficAction.EXTEND_GREEN:
                tempo_atual = semaforo.tempo_maximo_estado
                semaforo.definir_tempo_verde(int(tempo_atual * 1.2))
                messages.append(
                    f"Intersection {intersection_id}: {direcao.name} GREEN extended ({decision.reasoning})"
                )
            else:
                messages.append(
                    f"Intersection {intersection_id}: {direcao.name} unchanged ({decision.reasoning})"
                )

        return messages


class LLMManager(BaseLLMManager):
    """Manages LLM-based traffic control decisions using Ollama."""

    def __init__(self, model_name: str = "gemma3:1b"):
        """Initialize the Ollama-backed LLM manager."""

        super().__init__(evaluation_interval=600)
        self.model_name = model_name

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
    
        return super().apply_decisions(decisions, semaforos)


class OpenAIChatManager(BaseLLMManager):
    """LLM manager backed by OpenAI's Responses API."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(evaluation_interval=600)
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client: Optional[OpenAI] = None

        self._initialize_client()

    def _initialize_client(self) -> None:
        if not self.api_key:
            print("❌ OPENAI_API_KEY not configured. Set the environment variable to enable ChatGPT heuristic.")
            self.llm_available = False
            return

        try:
            self.client = OpenAI(api_key=self.api_key)
            self.llm_available = self._test_connection()
        except Exception as exc:
            print(f"❌ Failed to initialize OpenAI client: {exc}")
            self.llm_available = False

    def _test_connection(self) -> bool:
        if not self.client:
            return False

        try:
            response = self.client.responses.create(
                model=self.model_name,
                input="ping",
                max_output_tokens=2,
            )
            if self.debug_mode:
                print(f"✅ Connected to OpenAI model: {self.model_name}")
            return bool(response)
        except Exception as exc:
            print(f"❌ Failed to connect to OpenAI: {exc}")
            print("ChatGPT heuristic will use fallback strategy")
            return False

    def _extract_response_text(self, response) -> str:
        if response is None:
            return ""

        # The SDK may expose convenience attributes
        text_segments: List[str] = []

        if hasattr(response, "output_text") and response.output_text:
            return response.output_text

        output = getattr(response, "output", None)
        if output:
            for item in output:
                content = getattr(item, "content", None)
                if not content and isinstance(item, dict):
                    content = item.get("content")
                if not content:
                    continue
                for chunk in content:
                    chunk_type = getattr(chunk, "type", None)
                    if chunk_type is None and isinstance(chunk, dict):
                        chunk_type = chunk.get("type")
                    if chunk_type == "output_text":
                        text = getattr(chunk, "text", None)
                        if text is None and isinstance(chunk, dict):
                            text = chunk.get("text")
                        if text:
                            text_segments.append(text)

        if text_segments:
            return "".join(text_segments)

        # Fallback to dumping dictionary content
        if hasattr(response, "model_dump"):
            return json.dumps(response.model_dump(), ensure_ascii=False)

        try:
            return json.dumps(response, ensure_ascii=False)
        except TypeError:
            return str(response)

    def get_traffic_decisions(
        self, traffic_state: TrafficStateData, current_time: int = 0
    ) -> Optional[TrafficControlResponse]:
        if not self.llm_available or not self.client:
            return None

        try:
            prompt = self.generate_prompt(traffic_state)

            if self.debug_mode:
                print(f"🤖 Sending prompt to OpenAI (length: {len(prompt)} chars)")

            schema = TrafficControlResponse.model_json_schema()

            response = self.client.responses.create(
                model=self.model_name,
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "You are an expert urban traffic controller. "
                                    "Follow all provided rules strictly and return JSON only."
                                ),
                            }
                        ],
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "traffic_control_response",
                        "schema": schema,
                    },
                },
                temperature=0.1,
                max_output_tokens=800,
            )

            if self.debug_mode:
                print("🤖 OpenAI response received")

            content = self._extract_response_text(response)

            decisions = TrafficControlResponse.model_validate_json(content)

            self.last_evaluation_time = current_time
            self.last_decision = decisions

            return decisions

        except ValidationError as exc:
            print(f"❌ OpenAI response validation failed: {exc}")
            return self.last_decision
        except Exception as exc:
            print(f"❌ OpenAI request failed: {exc}")
            return self.last_decision
