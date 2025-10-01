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

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class GerenciadorMetricas:
    """Gerencia a coleta e análise de métricas da simulação."""

    def __init__(self):
        self.metricas_por_heuristica = {
            heuristica: {
                'tempo_viagem': [],
                'tempo_parado': [],
                'veiculos_processados': 0,
                'eficiencia': []
            } for heuristica in TipoHeuristica
        }

        self.sessao_atual = {
            'inicio': datetime.now(),
            'heuristica_atual': None,
            'dados_temporais': []
        }

    def calcular_score(self, heuristica: TipoHeuristica) -> float:
        m = self.metricas_por_heuristica[heuristica]
        if not m['tempo_viagem'] or not m['veiculos_processados']:
            return 0.0
        tm = sum(m['tempo_viagem']) / len(m['tempo_viagem'])
        tp = sum(m['tempo_parado']) / len(m['tempo_parado'])
        v = m['veiculos_processados']
        tm_norm = max(0, min(1, 1 - tm / 10))
        tp_norm = max(0, min(1, 1 - tp / 5))
        v_norm = max(0, min(1, v / 200))
        score = (0.5 * tm_norm + 0.3 * tp_norm + 0.2 * v_norm) * 100
        return score

    def registrar_metricas(self, estatisticas: Dict, heuristica: TipoHeuristica) -> None:
        if estatisticas['veiculos_concluidos'] > 0:
            metricas = self.metricas_por_heuristica[heuristica]
            metricas['tempo_viagem'].append(estatisticas['tempo_viagem_medio'])
            metricas['tempo_parado'].append(estatisticas['tempo_parado_medio'])
            metricas['veiculos_processados'] = estatisticas['veiculos_concluidos']
            if estatisticas['tempo_viagem_medio'] > 0:
                eficiencia = ((estatisticas['tempo_viagem_medio'] - estatisticas['tempo_parado_medio']) /
                              estatisticas['tempo_viagem_medio']) * 100
                metricas['eficiencia'].append(eficiencia)

    def obter_comparacao(self) -> Dict:
        comparacao = {}
        for heuristica, metricas in self.metricas_por_heuristica.items():
            if metricas['tempo_viagem']:
                comparacao[heuristica.name] = {
                    'tempo_viagem_medio': sum(metricas['tempo_viagem']) / len(metricas['tempo_viagem']),
                    'tempo_parado_medio': sum(metricas['tempo_parado']) / len(metricas['tempo_parado']),
                    'eficiencia_media': sum(metricas['eficiencia']) / len(metricas['eficiencia'])
                    if metricas['eficiencia'] else 0,
                    'veiculos_processados': metricas['veiculos_processados']
                }
        return comparacao

    def salvar_relatorio(self, nome_arquivo: str = None) -> str:
        if nome_arquivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"relatorio_simulacao_{timestamp}.json"

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
            'configuracoes': {
                'grade': f"{CONFIG.LINHAS_GRADE}x{CONFIG.COLUNAS_GRADE}",
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

    def __init__(self, linhas: int = CONFIG.LINHAS_GRADE, colunas: int = CONFIG.COLUNAS_GRADE):
        self.malha = MalhaViaria(linhas, colunas)
        self.renderizador = Renderizador()
        self.gerenciador_metricas = GerenciadorMetricas()

        self.rodando = True
        self.pausado = False
        self.mostrar_estatisticas = True

        self.multiplicador_velocidade = 1.0
        self.tempo_acumulado = 0.0

        self.heuristica_atual = CONFIG.HEURISTICA_ATIVA
        self.tempo_por_heuristica = {}
        self.inicio_heuristica = pygame.time.get_ticks()

        self.mensagem_temporaria = None
        self.tempo_mensagem = 0

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
        elif evento.key == pygame.K_1:
            self._mudar_heuristica(TipoHeuristica.VERTICAL_HORIZONTAL)
        elif evento.key == pygame.K_2:
            self._mudar_heuristica(TipoHeuristica.RANDOM_OPEN_CLOSE)
        elif evento.key == pygame.K_3:
            self._mudar_heuristica(TipoHeuristica.LLM_HEURISTICA)
        elif evento.key == pygame.K_4:
            self._mudar_heuristica(TipoHeuristica.MANUAL)
        elif evento.key == pygame.K_n and self.heuristica_atual == TipoHeuristica.MANUAL:
            self.malha.gerenciador_semaforos.avancar_manual()
            self._mostrar_mensagem("Manual: semáforos avançados")
        elif evento.key == pygame.K_s and (evento.mod & pygame.KMOD_CTRL):
            self._salvar_relatorio()

    def _mudar_heuristica(self, nova_heuristica: TipoHeuristica) -> None:
        if nova_heuristica != self.heuristica_atual:
            tempo_atual = pygame.time.get_ticks()
            tempo_decorrido = (tempo_atual - self.inicio_heuristica) / 1000
            if self.heuristica_atual not in self.tempo_por_heuristica:
                self.tempo_por_heuristica[self.heuristica_atual] = 0
            self.tempo_por_heuristica[self.heuristica_atual] += tempo_decorrido
            self.heuristica_atual = nova_heuristica
            self.malha.mudar_heuristica(nova_heuristica)
            self.inicio_heuristica = tempo_atual

            nomes = {
                TipoHeuristica.VERTICAL_HORIZONTAL: "Vertical/Horizontal",
                TipoHeuristica.RANDOM_OPEN_CLOSE: "Aleatório",
                TipoHeuristica.LLM_HEURISTICA: "LLM Inteligente",
                TipoHeuristica.MANUAL: "Manual"
            }
            nome_heuristica = nomes.get(nova_heuristica, "Desconhecida")
            self._mostrar_mensagem(f"Heurística: {nome_heuristica}")

    def _reiniciar(self) -> None:
        self._coletar_metricas()
        self.malha = MalhaViaria(CONFIG.LINHAS_GRADE, CONFIG.COLUNAS_GRADE)
        self.pausado = False
        self.multiplicador_velocidade = 1.0
        self.tempo_acumulado = 0.0
        self._mostrar_mensagem("Simulação Reiniciada")

    def _mostrar_mensagem(self, mensagem: str) -> None:
        self.mensagem_temporaria = mensagem
        self.tempo_mensagem = pygame.time.get_ticks()

    def _salvar_relatorio(self) -> None:
        try:
            caminho = self.gerenciador_metricas.salvar_relatorio()
            self._mostrar_mensagem(f"Relatório salvo: {os.path.basename(caminho)}")
        except Exception as e:
            self._mostrar_mensagem(f"Erro ao salvar: {str(e)}")

    def _finalizar_simulacao(self) -> None:
        self._coletar_metricas()
        print("\nSimulação finalizada!")
        print("Comparação de heurísticas:")
        comparacao = self.gerenciador_metricas.obter_comparacao()
        for heuristica, dados in comparacao.items():
            print(f"\n{heuristica}:")
            print(f"  - Tempo médio de viagem: {dados['tempo_viagem_medio']:.2f}s")
            print(f"  - Tempo médio parado: {dados['tempo_parado_medio']:.2f}s")
            print(f"  - Eficiência média: {dados['eficiencia_media']:.1f}%")
        self.rodando = False

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


class SimulacaoHeadless:
    """Simulação sem interface gráfica para análise de desempenho."""
    
    def __init__(self, heuristica: TipoHeuristica, duracao_segundos: int, 
                 nome_arquivo: str = None, verbose: bool = False):
        self.heuristica = heuristica
        self.duracao_segundos = duracao_segundos
        self.nome_arquivo = nome_arquivo
        self.verbose = verbose
        
        # Inicializa componentes
        self.malha = None
        self.gerenciador_metricas = GerenciadorMetricas()
        self.tempo_inicio = None
        self.tempo_fim = None
        
        # Configurações para simulação headless
        self.fps = 60  # FPS fixo para simulação
        self.tempo_acumulado = 0.0
        
    def inicializar(self):
        """Inicializa a simulação headless."""
        self.malha = MalhaViaria(CONFIG.LINHAS_GRADE, CONFIG.COLUNAS_GRADE)
        self.malha.mudar_heuristica(self.heuristica)
        self.tempo_inicio = time.time()
        
        if self.verbose:
            print(f"🚀 Iniciando simulação headless com heurística: {self.heuristica.name}")
            print(f"⏱️  Duração: {self.duracao_segundos} segundos")
            print(f"📊 Grade: {CONFIG.LINHAS_GRADE}x{CONFIG.COLUNAS_GRADE}")
    
    def executar(self):
        """Executa a simulação headless."""
        self.inicializar()
        
        if self.verbose:
            print("🔄 Executando simulação...")
        
        # Configura progress bar se tqdm estiver disponível
        if TQDM_AVAILABLE:
            progress_bar = tqdm(
                total=self.duracao_segundos,
                desc=f"Simulação {self.heuristica.name}",
                unit="s",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}, {rate_fmt}]"
            )
        else:
            progress_bar = None
        
        try:
            # Loop principal da simulação
            while True:
                tempo_atual = time.time()
                tempo_decorrido = tempo_atual - self.tempo_inicio
                
                # Atualiza progress bar
                if progress_bar:
                    progress_bar.n = int(tempo_decorrido)
                    progress_bar.refresh()
                
                # Verifica se atingiu o tempo limite
                if tempo_decorrido >= self.duracao_segundos:
                    break
                
                # Atualiza a simulação
                dt = 1.0 / self.fps
                self.tempo_acumulado += dt
                
                while self.tempo_acumulado >= 1.0 / CONFIG.FPS:
                    self.malha.atualizar()
                    self.tempo_acumulado -= 1.0 / CONFIG.FPS
                    
                    # Coleta métricas periodicamente
                    if self.malha.metricas['tempo_simulacao'] % CONFIG.INTERVALO_METRICAS == 0:
                        self._coletar_metricas()
                
                # Pequena pausa para não sobrecarregar o CPU
                time.sleep(0.001)
        
        finally:
            if progress_bar:
                progress_bar.close()
        
        self.tempo_fim = time.time()
        self._finalizar()
    
    def _coletar_metricas(self):
        """Coleta métricas da simulação."""
        estatisticas = self.malha.obter_estatisticas()
        self.gerenciador_metricas.registrar_metricas(estatisticas, self.heuristica)
        
        if self.verbose and estatisticas['veiculos_concluidos'] > 0:
            print(f"📈 Veículos concluídos: {estatisticas['veiculos_concluidos']}, "
                  f"Tempo médio: {estatisticas['tempo_viagem_medio']:.2f}s")
    
    def _finalizar(self):
        """Finaliza a simulação e gera relatório."""
        duracao_real = self.tempo_fim - self.tempo_inicio
        
        if self.verbose:
            print(f"\n✅ Simulação concluída em {duracao_real:.2f} segundos")
        
        # Coleta métricas finais
        estatisticas_finais = self.malha.obter_estatisticas()
        self.gerenciador_metricas.registrar_metricas(estatisticas_finais, self.heuristica)
        
        # Gera relatório
        self._gerar_relatorio(duracao_real, estatisticas_finais)
    
    def _gerar_relatorio(self, duracao_real: float, estatisticas_finais: dict):
        """Gera relatório detalhado da simulação."""
        # Nome do arquivo
        if not self.nome_arquivo:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.nome_arquivo = f"relatorio_{self.heuristica.name.lower()}_{timestamp}.json"
        
        # Dados do relatório
        relatorio = {
            'simulacao': {
                'heuristica': self.heuristica.name,
                'duracao_solicitada': self.duracao_segundos,
                'duracao_real': duracao_real,
                'inicio': datetime.fromtimestamp(self.tempo_inicio).isoformat(),
                'fim': datetime.fromtimestamp(self.tempo_fim).isoformat(),
                'grade': f"{CONFIG.LINHAS_GRADE}x{CONFIG.COLUNAS_GRADE}",
                'fps': self.fps
            },
            'metricas': {
                'veiculos_concluidos': estatisticas_finais['veiculos_concluidos'],
                'tempo_viagem_medio': estatisticas_finais['tempo_viagem_medio'],
                'tempo_parado_medio': estatisticas_finais['tempo_parado_medio'],
                'eficiencia_media': self._calcular_eficiencia(estatisticas_finais),
                'score_heuristica': self.gerenciador_metricas.calcular_score(self.heuristica)
            },
            'configuracao': {
                'taxa_geracao': CONFIG.TAXA_GERACAO_VEICULO,
                'velocidade_max': CONFIG.VELOCIDADE_MAX_VEICULO,
                'fps_simulacao': CONFIG.FPS,
                'intervalo_metricas': CONFIG.INTERVALO_METRICAS
            }
        }
        
        # Salva o relatório
        os.makedirs('relatorios', exist_ok=True)
        caminho_completo = os.path.join('relatorios', self.nome_arquivo)
        
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        # Exibe resumo
        print(f"\n📊 RELATÓRIO DE DESEMPENHO - {self.heuristica.name}")
        print("=" * 50)
        print(f"⏱️  Duração: {duracao_real:.2f}s (solicitado: {self.duracao_segundos}s)")
        print(f"🚗 Veículos processados: {estatisticas_finais['veiculos_concluidos']}")
        print(f"🕐 Tempo médio de viagem: {estatisticas_finais['tempo_viagem_medio']:.2f}s")
        print(f"⏸️  Tempo médio parado: {estatisticas_finais['tempo_parado_medio']:.2f}s")
        print(f"📈 Eficiência: {self._calcular_eficiencia(estatisticas_finais):.1f}%")
        print(f"⭐ Score da heurística: {self.gerenciador_metricas.calcular_score(self.heuristica):.1f}")
        print(f"💾 Relatório salvo: {caminho_completo}")
        print("=" * 50)
    
    def _calcular_eficiencia(self, estatisticas: dict) -> float:
        """Calcula a eficiência baseada no tempo de viagem e parado."""
        if estatisticas['tempo_viagem_medio'] > 0:
            return ((estatisticas['tempo_viagem_medio'] - estatisticas['tempo_parado_medio']) / 
                   estatisticas['tempo_viagem_medio']) * 100
        return 0.0
