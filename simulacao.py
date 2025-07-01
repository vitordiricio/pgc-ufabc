"""
Módulo principal de simulação com suporte a múltiplas heurísticas e análise de desempenho.
"""
import pygame
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from configuracao import CONFIG, TipoHeuristica
from cruzamento import MalhaViaria
from renderizador import Renderizador


class GerenciadorMetricas:
    """Gerencia a coleta e análise de métricas da simulação."""
    
    def __init__(self):
        """Inicializa o gerenciador de métricas."""
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
    
    def registrar_metricas(self, estatisticas: Dict, heuristica: TipoHeuristica) -> None:
        """Registra métricas para análise posterior."""
        if estatisticas['veiculos_concluidos'] > 0:
            metricas = self.metricas_por_heuristica[heuristica]
            
            metricas['tempo_viagem'].append(estatisticas['tempo_viagem_medio'])
            metricas['tempo_parado'].append(estatisticas['tempo_parado_medio'])
            metricas['veiculos_processados'] = estatisticas['veiculos_concluidos']
            
            # Calcula eficiência
            if estatisticas['tempo_viagem_medio'] > 0:
                eficiencia = ((estatisticas['tempo_viagem_medio'] - estatisticas['tempo_parado_medio']) / 
                            estatisticas['tempo_viagem_medio']) * 100
                metricas['eficiencia'].append(eficiencia)
    
    def obter_comparacao(self) -> Dict:
        """Retorna comparação entre heurísticas."""
        comparacao = {}
        
        for heuristica, metricas in self.metricas_por_heuristica.items():
            if metricas['tempo_viagem']:
                comparacao[heuristica.name] = {
                    'tempo_viagem_medio': sum(metricas['tempo_viagem']) / len(metricas['tempo_viagem']),
                    'tempo_parado_medio': sum(metricas['tempo_parado']) / len(metricas['tempo_parado']),
                    'eficiencia_media': sum(metricas['eficiencia']) / len(metricas['eficiencia']) if metricas['eficiencia'] else 0,
                    'veiculos_processados': metricas['veiculos_processados']
                }
        
        return comparacao
    
    def salvar_relatorio(self, nome_arquivo: str = None) -> str:
        """Salva relatório de métricas em arquivo."""
        if nome_arquivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"relatorio_simulacao_{timestamp}.json"
        
        relatorio = {
            'sessao': {
                'inicio': self.sessao_atual['inicio'].isoformat(),
                'fim': datetime.now().isoformat(),
                'duracao_minutos': (datetime.now() - self.sessao_atual['inicio']).seconds / 60
            },
            'comparacao_heuristicas': self.obter_comparacao(),
            'configuracoes': {
                'grade': f"{CONFIG.LINHAS_GRADE}x{CONFIG.COLUNAS_GRADE}",
                'taxa_geracao': CONFIG.TAXA_GERACAO_VEICULO,
                'velocidade_max': CONFIG.VELOCIDADE_MAX_VEICULO
            }
        }
        
        # Criar diretório se não existir
        os.makedirs('relatorios', exist_ok=True)
        caminho_completo = os.path.join('relatorios', nome_arquivo)
        
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        return caminho_completo


class Simulacao:
    """Classe principal que coordena toda a simulação de tráfego."""
    
    def __init__(self, linhas: int = CONFIG.LINHAS_GRADE, colunas: int = CONFIG.COLUNAS_GRADE):
        """
        Inicializa a simulação.
        
        Args:
            linhas: Número de linhas de cruzamentos
            colunas: Número de colunas de cruzamentos
        """
        self.malha = MalhaViaria(linhas, colunas)
        self.renderizador = Renderizador()
        self.gerenciador_metricas = GerenciadorMetricas()
        
        # Estados da simulação
        self.rodando = True
        self.pausado = False
        self.mostrar_estatisticas = True
        
        # Controle de velocidade
        self.multiplicador_velocidade = 1.0
        self.tempo_acumulado = 0.0
        
        # Controle de heurísticas
        self.heuristica_atual = CONFIG.HEURISTICA_ATIVA
        self.tempo_por_heuristica = {}
        self.inicio_heuristica = pygame.time.get_ticks()
        
        # Mensagens temporárias
        self.mensagem_temporaria = None
        self.tempo_mensagem = 0
    
    def processar_eventos(self) -> None:
        """Processa eventos de entrada do usuário."""
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            elif evento.type == pygame.KEYDOWN:
                self._processar_tecla(evento)
    
    def _processar_tecla(self, evento: pygame.event.Event) -> None:
        """Processa eventos de teclado."""
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
            
        # Mudança de heurística
        elif evento.key == pygame.K_1:
            self._mudar_heuristica(TipoHeuristica.TEMPO_FIXO)
        elif evento.key == pygame.K_2:
            self._mudar_heuristica(TipoHeuristica.ADAPTATIVA_SIMPLES)
        elif evento.key == pygame.K_3:
            self._mudar_heuristica(TipoHeuristica.ADAPTATIVA_DENSIDADE)
        elif evento.key == pygame.K_4:
            self._mudar_heuristica(TipoHeuristica.WAVE_GREEN)
        
        # Salvar relatório
        elif evento.key == pygame.K_s and evento.mod & pygame.KMOD_CTRL:
            self._salvar_relatorio()
    
    def _mudar_heuristica(self, nova_heuristica: TipoHeuristica) -> None:
        """Muda a heurística de controle."""
        if nova_heuristica != self.heuristica_atual:
            # Registra tempo da heurística anterior
            tempo_atual = pygame.time.get_ticks()
            tempo_decorrido = (tempo_atual - self.inicio_heuristica) / 1000
            
            if self.heuristica_atual not in self.tempo_por_heuristica:
                self.tempo_por_heuristica[self.heuristica_atual] = 0
            self.tempo_por_heuristica[self.heuristica_atual] += tempo_decorrido
            
            # Muda para nova heurística
            self.heuristica_atual = nova_heuristica
            self.malha.mudar_heuristica(nova_heuristica)
            self.inicio_heuristica = tempo_atual
            
            nome_heuristica = {
                TipoHeuristica.TEMPO_FIXO: "Tempo Fixo",
                TipoHeuristica.ADAPTATIVA_SIMPLES: "Adaptativa Simples",
                TipoHeuristica.ADAPTATIVA_DENSIDADE: "Adaptativa por Densidade",
                TipoHeuristica.WAVE_GREEN: "Onda Verde"
            }[nova_heuristica]
            
            self._mostrar_mensagem(f"Heurística: {nome_heuristica}")
    
    def _reiniciar(self) -> None:
        """Reinicia a simulação."""
        # Salva métricas antes de reiniciar
        self._coletar_metricas()
        
        # Reinicia componentes
        self.malha = MalhaViaria(CONFIG.LINHAS_GRADE, CONFIG.COLUNAS_GRADE)
        self.pausado = False
        self.multiplicador_velocidade = 1.0
        self.tempo_acumulado = 0.0
        
        self._mostrar_mensagem("Simulação Reiniciada")
    
    def _mostrar_mensagem(self, mensagem: str) -> None:
        """Mostra uma mensagem temporária."""
        self.mensagem_temporaria = mensagem
        self.tempo_mensagem = pygame.time.get_ticks()
    
    def _salvar_relatorio(self) -> None:
        """Salva relatório de métricas."""
        try:
            caminho = self.gerenciador_metricas.salvar_relatorio()
            self._mostrar_mensagem(f"Relatório salvo: {os.path.basename(caminho)}")
        except Exception as e:
            self._mostrar_mensagem(f"Erro ao salvar: {str(e)}")
    
    def _finalizar_simulacao(self) -> None:
        """Finaliza a simulação e salva métricas."""
        self._coletar_metricas()
        
        # Pergunta se deseja salvar relatório
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
        """Coleta métricas atuais."""
        estatisticas = self.malha.obter_estatisticas()
        self.gerenciador_metricas.registrar_metricas(estatisticas, self.heuristica_atual)
    
    def atualizar(self, dt: float) -> None:
        """
        Atualiza a simulação.
        
        Args:
            dt: Delta time em segundos
        """
        if self.pausado:
            return
        
        # Aplica multiplicador de velocidade
        self.tempo_acumulado += dt * self.multiplicador_velocidade
        
        # Atualiza a simulação em passos discretos
        while self.tempo_acumulado >= 1.0 / CONFIG.FPS:
            self.malha.atualizar()
            self.tempo_acumulado -= 1.0 / CONFIG.FPS
            
            # Coleta métricas periodicamente
            if self.malha.metricas['tempo_simulacao'] % CONFIG.INTERVALO_METRICAS == 0:
                self._coletar_metricas()
    
    def renderizar(self) -> None:
        """Renderiza a simulação."""
        # Prepara informações para renderização
        info_simulacao = {
            'velocidade': self.multiplicador_velocidade,
            'estado': 'Pausado' if self.pausado else 'Executando',
            'fps': self.renderizador.obter_fps()
        }
        
        # Renderiza a malha
        self.renderizador.renderizar(self.malha, info_simulacao)
        
        # Renderiza mensagem temporária se houver
        if self.mensagem_temporaria:
            tempo_decorrido = pygame.time.get_ticks() - self.tempo_mensagem
            if tempo_decorrido < 2000:  # Mostra por 2 segundos
                self.renderizador.desenhar_mensagem(self.mensagem_temporaria)
            else:
                self.mensagem_temporaria = None
    
    def executar(self) -> None:
        """Loop principal da simulação."""
        clock = pygame.time.Clock()
        
        print("Simulação de Tráfego Urbano iniciada!")
        print("Pressione F1 para ajuda com os controles.")
        
        while self.rodando:
            dt = clock.tick(CONFIG.FPS) / 1000.0  # Delta time em segundos
            
            self.processar_eventos()
            self.atualizar(dt)
            self.renderizar()
        
        print("\nSimulação encerrada.")
        pygame.quit()