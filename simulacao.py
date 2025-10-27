"""
Módulo principal de simulação com suporte a múltiplas heurísticas e análise de desempenho.
"""
import pygame
import json
import os
import time
from datetime import datetime
from typing import Dict
from configuracao import CONFIG, TipoHeuristica, Direcao, EstadoSemaforo
from cruzamento import MalhaViaria
from renderizador import Renderizador
from tqdm import tqdm


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
        
        self.malha = MalhaViaria(linhas, colunas, engine)
        self.gerenciador_metricas = GerenciadorMetricas()
        
        # Initialize renderer only for GUI mode
        if self.use_gui:
            self.renderizador = Renderizador()
            self.rodando = True
            self.pausado = False
            self.mostrar_estatisticas = True
            self.multiplicador_velocidade = 1.0
            self.tempo_acumulado = 0.0
            self.tempo_por_heuristica = {}
            self.inicio_heuristica = pygame.time.get_ticks()
            self.mensagem_temporaria = None
            self.tempo_mensagem = 0
        else:
            # Headless mode variables
            self.tempo_inicio = None
            self.tempo_fim = None
            self.fps = 60
            self.tempo_acumulado = 0.0
        
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
        if self.pausado:
            return
        self.tempo_acumulado += dt * self.multiplicador_velocidade
        while self.tempo_acumulado >= 1.0 / CONFIG.FPS:
            self.malha.atualizar()
            self.tempo_acumulado -= 1.0 / CONFIG.FPS
            if self.malha.metricas['tempo_simulacao'] % CONFIG.INTERVALO_METRICAS == 0:
                self._coletar_metricas()

    def renderizar(self) -> None:
        info_simulacao = {
            'velocidade': self.multiplicador_velocidade,
            'estado': 'Pausado' if self.pausado else 'Executando',
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

    def executar(self) -> None:
        if self.use_gui:
            self._executar_gui()
        else:
            self._executar_headless()
    
    def _executar_gui(self) -> None:
        """Execute simulation in GUI mode."""
        clock = pygame.time.Clock()
        print("Simulação de Tráfego Urbano iniciada!")
        print("Pressione F1 para ajuda com os controles.")
        while self.rodando:
            dt = clock.tick(CONFIG.FPS) / 1000.0
            self.processar_eventos()
            self.atualizar(dt)
            self.renderizar()
        print("\nSimulação encerrada.")
        pygame.quit()
    
    def _executar_headless(self) -> None:
        """Execute simulation in headless mode."""
        self._inicializar_headless()
        
        if self.verbose:
            print("Executando simulação...")

        progress_bar = tqdm(
            total=self.duracao_segundos,
            desc=f"Simulação {self.heuristica_atual.name}",
            unit="s",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}, {rate_fmt}]"
        )

        try:
            while True:
                tempo_atual = time.time()
                tempo_decorrido = tempo_atual - self.tempo_inicio

                if progress_bar:
                    progress_bar.n = int(tempo_decorrido)
                    progress_bar.refresh()

                if tempo_decorrido >= self.duracao_segundos:
                    break

                dt = 1.0 / self.fps
                self.tempo_acumulado += dt

                while self.tempo_acumulado >= 1.0 / CONFIG.FPS:
                    self.malha.atualizar()
                    self.tempo_acumulado -= 1.0 / CONFIG.FPS
                    if self.malha.metricas['tempo_simulacao'] % CONFIG.INTERVALO_METRICAS == 0:
                        self._coletar_metricas()

                time.sleep(0.001)

        finally:
            if progress_bar:
                progress_bar.close()

        self.tempo_fim = time.time()
        self._finalizar_headless()
    
    def _inicializar_headless(self) -> None:
        """Initialize headless simulation."""
        self.tempo_inicio = time.time()

        if self.verbose:
            print(f"Iniciando simulação headless com heurística: {self.heuristica_atual.name}")
            print(f"Duração: {self.duracao_segundos} segundos")
            print(f"Grade: {self.linhas}x{self.colunas}")
    
    def _finalizar_headless(self) -> None:
        """Finalize headless simulation and generate report."""
        duracao_real = self.tempo_fim - self.tempo_inicio

        if self.verbose:
            print(f"\nSimulação concluída em {duracao_real:.2f} segundos")

        estatisticas_finais = self.malha.obter_estatisticas()
        self.gerenciador_metricas.registrar_metricas(estatisticas_finais, self.heuristica_atual)
        self._gerar_relatorio_headless(duracao_real, estatisticas_finais)
    
    def _gerar_relatorio_headless(self, duracao_real: float, estatisticas_finais: dict):
        """Generate headless report using the same pattern as before."""
        if not self.nome_arquivo:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.nome_arquivo = f"relatorio_{self.heuristica_atual.name.lower()}_{timestamp}.json"

        # Use unified report generation
        caminho_completo = self._gerar_relatorio_unificado(
            estatisticas=estatisticas_finais,
            duracao_real=duracao_real,
            duracao_solicitada=self.duracao_segundos,
            tempo_inicio=datetime.fromtimestamp(self.tempo_inicio),
            tempo_fim=datetime.fromtimestamp(self.tempo_fim),
            nome_arquivo=self.nome_arquivo,
            modo='headless'
        )

        print(f"\nRELATÓRIO DE DESEMPENHO - {self.heuristica_atual.name}")
        print("=" * 50)
        print(f"Duração: {duracao_real:.2f}s (solicitado: {self.duracao_segundos}s)")
        print(f"Veículos processados: {estatisticas_finais['veiculos_concluidos']}")
        print(f"Tempo médio de viagem: {estatisticas_finais['tempo_viagem_medio']:.2f}s")
        print(f"Tempo médio parado: {estatisticas_finais['tempo_parado_medio']:.2f}s")
        print(f"Throughput/min: {estatisticas_finais.get('throughput_por_minuto', 0.0):.2f}")
        print(f"Backlog atual: {estatisticas_finais.get('backlog_total', 0)} | "
              f"máx: {estatisticas_finais.get('backlog_max', 0)} | "
              f"médio: {estatisticas_finais.get('backlog_medio', 0.0):.2f}")
        print(f"Backlog gerado: {estatisticas_finais.get('backlog_gerado_total', 0)} | "
              f"despachado: {estatisticas_finais.get('backlog_despachado_total', 0)}")
        print(f"Score: {self.gerenciador_metricas.calcular_score(self.heuristica_atual):.1f}")
        print(f"Relatório salvo: {caminho_completo}")
        print("=" * 50)

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
                'fps': CONFIG.FPS if modo == 'gui' else self.fps,
                'modo': modo
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


