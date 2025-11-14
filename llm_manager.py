"""
LLM Manager for traffic control using Ollama or OpenAI with structured output.
"""
import json
import os
import time
import threading
import queue
from typing import Dict, List, Optional, Tuple
from ollama import chat
from openai import OpenAI
from pydantic import ValidationError
from dotenv import load_dotenv

from llm_models import TrafficControlResponse, TrafficStateData
from configuracao import Direcao, EstadoSemaforo

# Load environment variables
load_dotenv()


class LLMWorker(threading.Thread):
    """Worker thread to handle blocking LLM API calls."""

    def __init__(self, request_queue: queue.Queue, response_queue: queue.Queue, engine: str, debug_mode: bool = True):
        super().__init__(daemon=True)
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.engine = engine
        self.debug_mode = debug_mode
        self.llm_manager = LLMManager(engine, debug_mode)

    def run(self):
        """Continuously process LLM requests from the queue."""
        while True:
            try:
                traffic_state, current_time = self.request_queue.get()
                if traffic_state is None:  # Sentinel for stopping the thread
                    break

                if self.debug_mode:
                    print(f"[LLMWorker] Received request for time {current_time}. Processing...")

                decisions = self.llm_manager.get_traffic_decisions(traffic_state, current_time)
                self.response_queue.put(decisions)

            except Exception as e:
                print(f"❌ [LLMWorker] Error during processing: {e}")
                # Optionally put an error message or a fallback decision on the response queue
                self.response_queue.put(None)


class LLMManager:
    """Manages LLM-based traffic control decisions using Ollama or OpenAI."""

    def __init__(self, engine: str = "ollama", debug_mode: bool = True):
        self.engine = engine
        self.debug_mode = debug_mode
        self.llm_available = False
        self.api_key = None
        self.model_name = ""
        
        if engine == "ollama":
            self.model_name = os.getenv('OLLAMA_MODEL', 'llama3:8b')
            self.llm_available = True
        elif engine == "openai":
            self.model_name = os.getenv('OPENAI_MODEL', 'gpt-4-turbo')
            self.api_key = os.getenv('OPENAI_API_KEY')
            if not self.api_key:
                print("❌ OPENAI_API_KEY not found in environment variables. LLM heuristic will not work.")
                self.llm_available = False
            else:
                self.llm_available = True
        else:
            print(f"❌ Unknown engine: {engine}")
            self.llm_available = False

    def _call_llm(self, prompt: str, schema: dict) -> Optional[str]:
        try:
            if self.engine == "ollama":
                return self._call_ollama(prompt, schema)
            elif self.engine == "openai":
                return self._call_openai(prompt)
            return None
        except Exception as e:
            print(f"❌ LLM call failed: {e}")
            return None

    def _call_ollama(self, prompt: str, schema: dict) -> Optional[str]:
        response = chat(
            messages=[{'role': 'user', 'content': prompt}],
            model=self.model_name,
            format='json' if schema else None,
            options={'temperature': 0.1}
        )
        content = response.get('message', {}).get('content') if isinstance(response, dict) else None
        if self.debug_mode and content:
            print(f"🤖 LLM Response Content:\n{content}")
        return content

    def _call_openai(self, prompt: str) -> Optional[str]:
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
            print("🤖 OpenAI response received.")
        

        if response and response.output_parsed:
            content = response.output_parsed
            return content
        return None

    @staticmethod
    def prepare_traffic_state(
        densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]],
        semaforos: Dict[Tuple[int, int], Dict[Direcao, any]],
        global_metrics: Dict
    ) -> TrafficStateData:
        intersections = []
        for id_cruzamento, semaforos_cruzamento in semaforos.items():
            densidade = densidade_por_cruzamento.get(id_cruzamento, {})
            semaforo_norte = semaforos_cruzamento.get(Direcao.NORTE)
            semaforo_leste = semaforos_cruzamento.get(Direcao.LESTE)
            
            intersection_data = {
                "id": id_cruzamento,
                "north_vehicles": densidade.get(Direcao.NORTE, 0),
                "east_vehicles": densidade.get(Direcao.LESTE, 0),
                "north_wait_time": 0,
                "east_wait_time": 0,
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
            time_since_last_change=0,
            current_heuristica="LLM_HEURISTICA"
        )

    @staticmethod
    def generate_prompt(traffic_state: TrafficStateData) -> str:
        intersections_summary = [
            f"Intersection {i['id']}: North={i['north_vehicles']} vehicles, "
            f"East={i['east_vehicles']} vehicles, "
            f"States: North={i['current_states']['north']}, East={i['current_states']['east']}"
            for i in traffic_state.intersections
        ]
        return (
            f"Traffic lights: {chr(10).join(intersections_summary)}\n\n"
            "Rules: One direction green per intersection. Prioritize higher vehicle counts.\n"
            "Make 1-2 decisions max."
        )

    def get_traffic_decisions(self, traffic_state: TrafficStateData, current_time: int) -> Optional[TrafficControlResponse]:
        if not self.llm_available:
            return None
        
        try:
            prompt = self.generate_prompt(traffic_state)
            if self.debug_mode:
                print(f"🤖 Sending prompt to LLM (length: {len(prompt)} chars) at sim time {current_time}")
            
            start_time = time.time()
            content = self._call_llm(prompt, TrafficControlResponse.model_json_schema())
            duration = time.time() - start_time
            
            if self.debug_mode:
                print(f"🤖 LLM call duration: {duration:.2f}s")

            if not content:
                return None
            
            return TrafficControlResponse.model_validate_json(content)
            
        except ValidationError as e:
            print(f"❌ LLM response validation failed: {e}")
            return None
        except Exception as e:
            print(f"❌ LLM request failed: {e}")
            return None
