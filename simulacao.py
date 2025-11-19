"""
Módulo principal de simulação com suporte a múltiplas heurísticas e análise de desempenho.
"""
import pygame
import json
import os
import time
import queue
from datetime import datetime
from typing import Dict
from configuracao import CONFIG, TipoHeuristica, Direcao, EstadoSemaforo
from cruzamento import MalhaViaria
from renderizador import Renderizador
from llm_manager import LLMWorker


class GerenciadorMetricas:
    """Gerencia a coleta e análise de métricas da simulação."""

    def __init__(self):
        self.metricas_por_heuristica = {
            heuristica: {
                'tempo_viagem': [],
                'tempo_parado': [],
                'veiculos_processados': 0,
                'eficiencia': [],
                # Séries adicionais
                'throughput_por_minuto': [],
                'paradas_media_por_veiculo': [],
                'tempo_viagem_p95': [],
                # Backlog
                'backlog_medio': [],
                'backlog_max': []
            } for heuristica in TipoHeuristica
        }

        self.sessao_atual = {
            'inicio': datetime.now(),
            'heuristica_atual': None,
            'dados_temporais': []
        }

    def calcular_score(self, heuristica: TipoHeuristica) -> float:
        """
        Score composto com normalizações suaves:
          - tm_norm = 1 / (1 + tm)
          - tp_norm = 1 / (1 + tp)
          - th_norm = min(1, th/60)
          - bk_norm = 1 / (1 + backlog_medio)  (penaliza backlog alto)

        Pesos:
          tm 40%, tp 25%, th 25%, backlog 10%.
        """
        m = self.metricas_por_heuristica[heuristica]
        if not m['tempo_viagem'] or not m['throughput_por_minuto']:
            return 0.0

        tm = sum(m['tempo_viagem']) / len(m['tempo_viagem'])
        tp = sum(m['tempo_parado']) / len(m['tempo_parado'])
        th = sum(m['throughput_por_minuto']) / len(m['throughput_por_minuto'])
        bk = (sum(m['backlog_medio']) / len(m['backlog_medio'])) if m['backlog_medio'] else 0.0

        tm_norm = 1.0 / (1.0 + max(0.0, tm))
        tp_norm = 1.0 / (1.0 + max(0.0, tp))
        th_norm = min(1.0, max(0.0, th) / 60.0)
        bk_norm = 1.0 / (1.0 + max(0.0, bk))

        score = (0.40 * tm_norm + 0.25 * tp_norm + 0.25 * th_norm + 0.10 * bk_norm) * 100.0
        return score

    def registrar_metricas(self, estatisticas: Dict, heuristica: TipoHeuristica) -> None:
        if estatisticas['veiculos_concluidos'] >= 0:
            metricas = self.metricas_por_heuristica[heuristica]
            # tempos médios (apenas quando houver base)
            if estatisticas['veiculos_concluidos'] > 0:
                metricas['tempo_viagem'].append(estatisticas['tempo_viagem_medio'])
                metricas['tempo_parado'].append(estatisticas['tempo_parado_medio'])
                if estatisticas['tempo_viagem_medio'] > 0:
                    eficiencia = ((estatisticas['tempo_viagem_medio'] - estatisticas['tempo_parado_medio']) /
                                  estatisticas['tempo_viagem_medio']) * 100
                    metricas['eficiencia'].append(eficiencia)
            metricas['veiculos_processados'] = estatisticas['veiculos_concluidos']

            # séries comparativas novas (se existirem nas estatísticas)
            metricas['throughput_por_minuto'].append(estatisticas.get('throughput_por_minuto', 0.0))
            metricas['paradas_media_por_veiculo'].append(estatisticas.get('paradas_media_por_veiculo', 0.0))
            metricas['tempo_viagem_p95'].append(estatisticas.get('tempo_viagem_p95', 0.0))

            # backlog
            metricas['backlog_medio'].append(estatisticas.get('backlog_medio', 0.0))
            metricas['backlog_max'].append(estatisticas.get('backlog_max', 0.0))

    def obter_comparacao(self) -> Dict:
        comparacao = {}
        for heuristica, metricas in self.metricas_por_heuristica.items():
            if metricas['tempo_viagem'] or metricas['throughput_por_minuto']:
                comparacao[heuristica.name] = {
                    'tempo_viagem_medio': sum(metricas['tempo_viagem']) / len(metricas['tempo_viagem'])
                    if metricas['tempo_viagem'] else 0.0,
                    'tempo_parado_medio': sum(metricas['tempo_parado']) / len(metricas['tempo_parado'])
                    if metricas['tempo_parado'] else 0.0,
                    'eficiencia_media': sum(metricas['eficiencia']) / len(metricas['eficiencia'])
                    if metricas['eficiencia'] else 0.0,
                    'veiculos_processados': metricas['veiculos_processados'],
                    'throughput_medio_por_minuto': (
                        sum(metricas['throughput_por_minuto']) / len(metricas['throughput_por_minuto'])
                        if metricas['throughput_por_minuto'] else 0.0
                    ),
                    'paradas_medias_por_veiculo': (
                        sum(metricas['paradas_media_por_veiculo']) / len(metricas['paradas_media_por_veiculo'])
                        if metricas['paradas_media_por_veiculo'] else 0.0
                    ),
                    'tempo_viagem_p95_medio': (
                        sum(metricas['tempo_viagem_p95']) / len(metricas['tempo_viagem_p95'])
                        if metricas['tempo_viagem_p95'] else 0.0
                    ),
                    'backlog_medio': (
                        sum(metricas['backlog_medio']) / len(metricas['backlog_medio'])
                        if metricas['backlog_medio'] else 0.0
                    ),
                    'backlog_max_medio': (
                        sum(metricas['backlog_max']) / len(metricas['backlog_max'])
                        if metricas['backlog_max'] else 0.0
                    )
                }
        return comparacao

    def salvar_relatorio(self, nome_arquivo: str = None, estatisticas_finais: Dict = None,
                        linhas: int = None, colunas: int = None) -> str:
        if nome_arquivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"relatorio_simulacao_{timestamp}.json"

        estat_final = estatisticas_finais or {}

        relatorio = {
            'sessao': {
                'inicio': self.sessao_atual['inicio'].isoformat(),
                'fim': datetime.now().isoformat(),
                'duracao_minutos': (datetime.now() - self.sessao_atual['inicio']).seconds / 60
            },
            'scores': {
                h.name: self.calcular_score(h)
                for h in self.metricas_por_heuristica
            },
            'comparacao_heuristicas': self.obter_comparacao(),
            'estatisticas_finais': estat_final,
            'configuracoes': {
                'grade': f"{linhas or CONFIG.LINHAS_GRADE}x{colunas or CONFIG.COLUNAS_GRADE}",
                'taxa_geracao': CONFIG.TAXA_GERACAO_VEICULO,
                'velocidade_max': CONFIG.VELOCIDADE_MAX_VEICULO
            }
        }

        os.makedirs('relatorios', exist_ok=True)
        caminho_completo = os.path.join('relatorios', nome_arquivo)
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        return caminho_completo


class Simulacao:
    """Classe principal que coordena toda a simulação de tráfego."""

    def __init__(self, heuristica: TipoHeuristica = None, use_gui: bool = True,
                 duracao_segundos: int = None, nome_arquivo: str = None,
                 verbose: bool = False, linhas: int = CONFIG.LINHAS_GRADE,
                 colunas: int = CONFIG.COLUNAS_GRADE, engine: str = 'ollama'):
        self.linhas = linhas
        self.colunas = colunas
        self.use_gui = use_gui
        self.heuristica_atual = heuristica or CONFIG.HEURISTICA_ATIVA
        self.duracao_segundos = duracao_segundos
        self.nome_arquivo = nome_arquivo
        self.verbose = verbose
        self.engine = engine

        # LLM Worker Thread setup
        self.llm_request_queue = queue.Queue()
        self.llm_response_queue = queue.Queue()
        if self.heuristica_atual == TipoHeuristica.LLM_HEURISTICA:
            self.llm_worker = LLMWorker(self.llm_request_queue, self.llm_response_queue, self.engine)
            self.llm_worker.start()
        else:
            self.llm_worker = None

        self.malha = MalhaViaria(
            linhas, colunas, engine,
            request_queue=self.llm_request_queue,
            response_queue=self.llm_response_queue
        )
        self.gerenciador_metricas = GerenciadorMetricas()

        # Initialize renderer (always active now)
        self.renderizador = Renderizador()
        self.rodando = True
        self.pausado = False
        self.awaiting_llm_response = False # New state for pausing simulation
        self.mostrar_estatisticas = True
        self.multiplicador_velocidade = 1.0
        self.tempo_acumulado = 0.0
        self.tempo_por_heuristica = {}
        self.inicio_heuristica = pygame.time.get_ticks()
        self.mensagem_temporaria = None
        self.tempo_mensagem = 0

        # Set the heuristic for the simulation
        self.malha.mudar_heuristica(self.heuristica_atual, self.engine)

    def processar_eventos(self) -> None:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            elif evento.type == pygame.KEYDOWN:
                self._processar_tecla(evento)
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                self._processar_clique(evento.pos)

    def _processar_clique(self, pos) -> None:
        resultado = self.malha.gerenciador_semaforos.clique_em(pos)
        if resultado:
            (cid, direcao, estado) = resultado
            nome_dir = "NORTE" if direcao == Direcao.NORTE else "LESTE"
            nome_est = {EstadoSemaforo.VERDE: "VERDE", EstadoSemaforo.AMARELO: "AMARELO", EstadoSemaforo.VERMELHO: "VERMELHO"}[estado]
            self._mostrar_mensagem(f"Cruz {cid} • {nome_dir}: {nome_est}")
        else:
            if self.heuristica_atual != TipoHeuristica.MANUAL:
                self._mostrar_mensagem("Ative o modo Manual (tecla 4) para controlar por clique")

    def _processar_tecla(self, evento: pygame.event.Event) -> None:
        if evento.key == pygame.K_ESCAPE:
            self._finalizar_simulacao()
        elif evento.key == pygame.K_SPACE:
            self.pausado = not self.pausado
            estado = "Pausado" if self.pausado else "Executando"
            self._mostrar_mensagem(f"Simulação {estado}")
        elif evento.key == pygame.K_r:
            self._reiniciar()
        elif evento.key == pygame.K_TAB:
            self.mostrar_estatisticas = not self.mostrar_estatisticas
        elif evento.key in [pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS]:
            self.multiplicador_velocidade = min(4.0, self.multiplicador_velocidade + 0.5)
            self._mostrar_mensagem(f"Velocidade: {self.multiplicador_velocidade}x")
        elif evento.key in [pygame.K_MINUS, pygame.K_KP_MINUS]:
            self.multiplicador_velocidade = max(0.5, self.multiplicador_velocidade - 0.5)
            self._mostrar_mensagem(f"Velocidade: {self.multiplicador_velocidade}x")
        elif evento.key == pygame.K_n and self.heuristica_atual == TipoHeuristica.MANUAL:
            self.malha.gerenciador_semaforos.avancar_manual()
            self._mostrar_mensagem("Manual: semáforos avançados")


    def _reiniciar(self) -> None:
        self._coletar_metricas()
        self.malha = MalhaViaria(self.linhas, self.colunas, self.engine)
        self.malha.mudar_heuristica(self.heuristica_atual, self.engine)
        self.pausado = False
        self.multiplicador_velocidade = 1.0
        self.tempo_acumulado = 0.0
        self._mostrar_mensagem("Simulação Reiniciada")

    def _mostrar_mensagem(self, mensagem: str) -> None:
        self.mensagem_temporaria = mensagem
        self.tempo_mensagem = pygame.time.get_ticks()


    def _finalizar_simulacao(self) -> None:
        self._coletar_metricas()
        print("\nSimulação finalizada!")

        # Auto-save report for GUI mode
        self._gerar_relatorio_gui()

        # Stop the LLM worker thread
        if self.llm_worker:
            self.llm_request_queue.put((None, None)) # Sentinel to stop the worker
            self.llm_worker.join(timeout=2) # Wait for the worker to finish

        self.rodando = False

    def _gerar_relatorio_gui(self) -> None:
        """Generate and save report for GUI mode using headless pattern."""
        try:
            estatisticas = self.malha.obter_estatisticas()

            # Calculate duration (approximate from simulation time)
            duracao_real = self.malha.metricas['tempo_simulacao'] / CONFIG.FPS

            # Generate filename using headless pattern
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"relatorio_{self.heuristica_atual.name.lower()}_{timestamp}.json"

            # Use unified report generation
            self._gerar_relatorio_unificado(
                estatisticas=estatisticas,
                duracao_real=duracao_real,
                duracao_solicitada=None,
                tempo_inicio=datetime.now(),
                tempo_fim=datetime.now(),
                nome_arquivo=nome_arquivo,
                modo='gui'
            )

            print(f"Relatório salvo automaticamente: {nome_arquivo}")

        except Exception as e:
            print(f"Erro ao salvar relatório: {str(e)}")

    def _coletar_metricas(self) -> None:
        estatisticas = self.malha.obter_estatisticas()
        self.gerenciador_metricas.registrar_metricas(estatisticas, self.heuristica_atual)

    def atualizar(self, dt: float) -> None:
        if self.pausado or self.awaiting_llm_response:
            # If paused by user or waiting for LLM, do not update simulation state
            return

        self.tempo_acumulado += dt * self.multiplicador_velocidade
        while self.tempo_acumulado >= 1.0 / CONFIG.FPS:
            # Malha.atualizar now returns a boolean indicating if it's waiting for LLM
            is_waiting = self.malha.atualizar()
            if is_waiting:
                self.awaiting_llm_response = True
                self._mostrar_mensagem("Aguardando decisão da Inteligência Artificial...")
                break  # Exit the update loop to pause simulation time

            self.tempo_acumulado -= 1.0 / CONFIG.FPS
            if self.malha.metricas['tempo_simulacao'] % CONFIG.INTERVALO_METRICAS == 0:
                self._coletar_metricas()

    def renderizar(self) -> None:
        estado_str = 'Executando'
        if self.pausado:
            estado_str = 'Pausado'
        elif self.awaiting_llm_response:
            estado_str = 'Aguardando LLM'

        info_simulacao = {
            'velocidade': self.multiplicador_velocidade,
            'estado': estado_str,
            'fps': self.renderizador.obter_fps(),
            'score': self.gerenciador_metricas.calcular_score(self.heuristica_atual)
        }
        self.renderizador.renderizar(self.malha, info_simulacao)
        if self.mensagem_temporaria:
            tempo_decorrido = pygame.time.get_ticks() - self.tempo_mensagem
            if tempo_decorrido < 2000:
                self.renderizador.desenhar_mensagem(self.mensagem_temporaria)
            else:
                self.mensagem_temporaria = None

    def _executar_gui(self) -> None:
        """Execute simulation in GUI mode."""
        clock = pygame.time.Clock()
        print("Simulação de Tráfego Urbano iniciada!")
        print("Pressione F1 para ajuda com os controles.")
        while self.rodando:
            dt = clock.tick(CONFIG.FPS) / 1000.0
            
            self.processar_eventos()
            
            # Non-blocking check for LLM response
            try:
                llm_decision = self.llm_response_queue.get_nowait()
                if llm_decision:
                    # Apply decision and unpause
                    print("🤖 Decisão do LLM recebida e aplicada.")
                    self.malha.gerenciador_semaforos.heuristica.ultima_decisao = llm_decision
                else:
                    print(f"⚠️ LLM retornou uma decisão inválida ou um erro. Valor recebido da fila: {llm_decision!r}")
                
                self.awaiting_llm_response = False
                self.mensagem_temporaria = None # Clear "waiting" message
            except queue.Empty:
                pass # No response yet, continue as normal

            self.atualizar(dt)
            self.renderizar()
            
            # Check for duration limit if specified
            if self.duracao_segundos is not None:
                simulation_time_frames = self.malha.metricas.get('tempo_simulacao', 0)
                simulation_time_seconds = simulation_time_frames / CONFIG.FPS
                if simulation_time_seconds >= self.duracao_segundos:
                    print(f"\nTempo de simulação ({self.duracao_segundos}s) atingido.")
                    self._finalizar_simulacao()

        # Cleanup worker thread on exit
        if self.llm_worker:
            self.llm_request_queue.put((None, None))
            self.llm_worker.join(timeout=2)

        print("\nSimulação encerrada.")
        pygame.quit()

    def executar(self) -> None:
        self._executar_gui()

    def _gerar_relatorio_unificado(self, estatisticas: dict, duracao_real: float,
                                  duracao_solicitada: int, tempo_inicio: datetime,
                                  tempo_fim: datetime, nome_arquivo: str, modo: str) -> str:
        """Unified report generation for both GUI and headless modes."""
        relatorio = {
            'simulacao': {
                'heuristica': self.heuristica_atual.name,
                'duracao_solicitada': duracao_solicitada,
                'duracao_real': duracao_real,
                'inicio': tempo_inicio.isoformat(),
                'fim': tempo_fim.isoformat(),
                'grade': f"{self.linhas}x{self.colunas}",
                'fps': CONFIG.FPS,
                'modo': modo,
                'engine': self.engine
            },
            'metricas': {
                'veiculos_concluidos': estatisticas['veiculos_concluidos'],
                'tempo_viagem_medio': estatisticas['tempo_viagem_medio'],
                'tempo_parado_medio': estatisticas['tempo_parado_medio'],
                'eficiencia_media': self._calcular_eficiencia(estatisticas),
                'score_heuristica': self.gerenciador_metricas.calcular_score(self.heuristica_atual),
                # extras (se presentes)
                'velocidade_media_global_px_s': estatisticas.get('velocidade_media_global', 0.0),
                'paradas_media_por_veiculo': estatisticas.get('paradas_media_por_veiculo', 0.0),
                'tempo_viagem_p50': estatisticas.get('tempo_viagem_p50', 0.0),
                'tempo_viagem_p95': estatisticas.get('tempo_viagem_p95', 0.0),
                'throughput_por_minuto': estatisticas.get('throughput_por_minuto', 0.0),
                'veiculos_aguardando_instante': estatisticas.get('veiculos_aguardando', 0),
                'velocidade_media_ativa': estatisticas.get('velocidade_media_ativa', 0.0),
                'maior_fila_cruzamento_atual': estatisticas.get('maior_fila_cruzamento_atual', 0),
                # backlog
                'backlog_total_atual': estatisticas.get('backlog_total', 0),
                'backlog_max_total': estatisticas.get('backlog_max', 0),
                'backlog_gerado_total': estatisticas.get('backlog_gerado_total', 0),
                'backlog_despachado_total': estatisticas.get('backlog_despachado_total', 0),
                'backlog_medio': estatisticas.get('backlog_medio', 0.0),
            },
            'configuracao': {
                'taxa_geracao': CONFIG.TAXA_GERACAO_VEICULO,
                'velocidade_max': CONFIG.VELOCIDADE_MAX_VEICULO,
                'fps_simulacao': CONFIG.FPS,
                'intervalo_metricas': CONFIG.INTERVALO_METRICAS,
                'backlog': {
                    'ativo': CONFIG.BACKLOG_ATIVO,
                    'limite_global': CONFIG.BACKLOG_TAMANHO_MAX,
                    'flush_por_frame': CONFIG.BACKLOG_FLUSH_MAX_POR_FRAME
                }
            }
        }

        os.makedirs('relatorios', exist_ok=True)
        caminho_completo = os.path.join('relatorios', nome_arquivo)
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)

        return caminho_completo

    def _calcular_eficiencia(self, estatisticas: dict) -> float:
        if estatisticas['tempo_viagem_medio'] > 0:
            return ((estatisticas['tempo_viagem_medio'] - estatisticas['tempo_parado_medio']) /
                   estatisticas['tempo_viagem_medio']) * 100
        return 0.0


