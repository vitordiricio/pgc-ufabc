"""
Módulo de semáforo com suporte a múltiplas heurísticas de controle.
"""
from typing import Tuple, Dict, List, Optional
from enum import Enum
import pygame
from configuracao import CONFIG, EstadoSemaforo, Direcao, TipoHeuristica


class Semaforo:
    """Representa um semáforo com controle inteligente."""
    
    def __init__(self, posicao: Tuple[float, float], direcao: Direcao, id_cruzamento: Tuple[int, int]):
        """
        Inicializa um semáforo.
        
        Args:
            posicao: Posição (x, y) do semáforo
            direcao: Direção do tráfego que o semáforo controla
            id_cruzamento: ID do cruzamento ao qual pertence
        """
        self.posicao = posicao
        self.direcao = direcao
        self.id_cruzamento = id_cruzamento
        
        # Estado inicial baseado na direção para evitar conflitos
        if direcao in [Direcao.NORTE, Direcao.SUL]:
            self.estado = EstadoSemaforo.VERDE
        else:
            self.estado = EstadoSemaforo.VERMELHO
        
        self.tempo_no_estado = 0
        self.tempo_maximo_estado = CONFIG.TEMPO_SEMAFORO_PADRAO[self.estado]
        
        # Estatísticas para heurísticas
        self.veiculos_esperando = 0
        self.tempo_total_espera = 0
        self.veiculos_passaram = 0
        
        # Controle de mudança de estado
        self.mudanca_forcada = False
        self.proximo_estado = None
    
    def atualizar(self, dt: float = 1.0) -> bool:
        """
        Atualiza o estado do semáforo.
        
        Args:
            dt: Delta time
            
        Returns:
            bool: True se houve mudança de estado
        """
        self.tempo_no_estado += dt
        
        # Verifica se deve mudar de estado
        mudou_estado = False
        
        if self.mudanca_forcada and self.proximo_estado:
            self._mudar_para_estado(self.proximo_estado)
            self.mudanca_forcada = False
            self.proximo_estado = None
            mudou_estado = True
        elif self.tempo_no_estado >= self.tempo_maximo_estado:
            self._avancar_estado()
            mudou_estado = True
        
        return mudou_estado
    
    def _avancar_estado(self) -> None:
        """Avança para o próximo estado na sequência."""
        if self.estado == EstadoSemaforo.VERDE:
            self._mudar_para_estado(EstadoSemaforo.AMARELO)
        elif self.estado == EstadoSemaforo.AMARELO:
            self._mudar_para_estado(EstadoSemaforo.VERMELHO)
        elif self.estado == EstadoSemaforo.VERMELHO:
            # Não muda automaticamente para verde - isso é controlado pelo gerenciador
            pass
    
    def _mudar_para_estado(self, novo_estado: EstadoSemaforo) -> None:
        """Muda para um novo estado."""
        self.estado = novo_estado
        self.tempo_no_estado = 0
        self.tempo_maximo_estado = CONFIG.TEMPO_SEMAFORO_PADRAO[novo_estado]
        
        # Reset estatísticas quando fica verde
        if novo_estado == EstadoSemaforo.VERDE:
            self.veiculos_esperando = 0
            self.tempo_total_espera = 0
    
    def forcar_mudanca(self, novo_estado: EstadoSemaforo) -> None:
        """Força a mudança para um estado específico."""
        self.proximo_estado = novo_estado
        self.mudanca_forcada = True
    
    def definir_tempo_verde(self, tempo: int) -> None:
        """Define o tempo de duração do sinal verde."""
        if self.estado == EstadoSemaforo.VERDE:
            self.tempo_maximo_estado = tempo
    
    def obter_posicao_parada(self) -> Tuple[float, float]:
        """Retorna a posição onde os veículos devem parar."""
        offset = CONFIG.DISTANCIA_PARADA_SEMAFORO
        
        if self.direcao == Direcao.NORTE:
            return (self.posicao[0], self.posicao[1] - offset)
        elif self.direcao == Direcao.SUL:
            return (self.posicao[0], self.posicao[1] + offset)
        elif self.direcao == Direcao.LESTE:
            return (self.posicao[0] - offset, self.posicao[1])
        elif self.direcao == Direcao.OESTE:
            return (self.posicao[0] + offset, self.posicao[1])
    
    def desenhar(self, tela: pygame.Surface) -> None:
        """Desenha o semáforo na tela com visual aprimorado."""
        # Dimensões da caixa do semáforo
        largura = CONFIG.TAMANHO_SEMAFORO * 3 + CONFIG.ESPACAMENTO_SEMAFORO * 2
        altura = CONFIG.TAMANHO_SEMAFORO + 8
        
        # Posição da caixa
        if self.direcao in [Direcao.NORTE, Direcao.SUL]:
            rect_caixa = pygame.Rect(
                self.posicao[0] - largura // 2,
                self.posicao[1] - altura // 2,
                largura, altura
            )
        else:
            rect_caixa = pygame.Rect(
                self.posicao[0] - altura // 2,
                self.posicao[1] - largura // 2,
                altura, largura
            )
        
        # Desenha a caixa do semáforo
        pygame.draw.rect(tela, CONFIG.PRETO, rect_caixa, border_radius=4)
        pygame.draw.rect(tela, CONFIG.CINZA_ESCURO, rect_caixa, 2, border_radius=4)
        
        # Cores das luzes
        cores = {
            EstadoSemaforo.VERMELHO: CONFIG.VERMELHO if self.estado == EstadoSemaforo.VERMELHO else (60, 20, 20),
            EstadoSemaforo.AMARELO: CONFIG.AMARELO if self.estado == EstadoSemaforo.AMARELO else (60, 60, 20),
            EstadoSemaforo.VERDE: CONFIG.VERDE if self.estado == EstadoSemaforo.VERDE else (20, 60, 20)
        }
        
        # Desenha as luzes
        raio = CONFIG.TAMANHO_SEMAFORO // 2 - 1
        
        if self.direcao in [Direcao.NORTE, Direcao.SUL]:
            # Semáforo horizontal
            x_base = rect_caixa.x + CONFIG.TAMANHO_SEMAFORO // 2 + 4
            y_centro = rect_caixa.centery
            
            for i, (estado, cor) in enumerate(cores.items()):
                x = x_base + i * (CONFIG.TAMANHO_SEMAFORO + CONFIG.ESPACAMENTO_SEMAFORO)
                pygame.draw.circle(tela, cor, (x, y_centro), raio)
                
                # Adiciona brilho se a luz estiver ativa
                if self.estado == estado:
                    pygame.draw.circle(tela, cor, (x, y_centro), raio - 2, 2)
        else:
            # Semáforo vertical
            x_centro = rect_caixa.centerx
            y_base = rect_caixa.y + CONFIG.TAMANHO_SEMAFORO // 2 + 4
            
            for i, (estado, cor) in enumerate(cores.items()):
                y = y_base + i * (CONFIG.TAMANHO_SEMAFORO + CONFIG.ESPACAMENTO_SEMAFORO)
                pygame.draw.circle(tela, cor, (x_centro, y), raio)
                
                # Adiciona brilho se a luz estiver ativa
                if self.estado == estado:
                    pygame.draw.circle(tela, cor, (x_centro, y), raio - 2, 2)


class GerenciadorSemaforos:
    """Gerencia todos os semáforos com suporte a heurísticas."""
    
    def __init__(self, heuristica: TipoHeuristica = TipoHeuristica.TEMPO_FIXO):
        """
        Inicializa o gerenciador.
        
        Args:
            heuristica: Tipo de heurística a ser utilizada
        """
        self.heuristica = heuristica
        self.semaforos: Dict[Tuple[int, int], Dict[Direcao, Semaforo]] = {}
        self.tempo_ciclo = 0
        self.estatisticas_globais = {
            'veiculos_total': 0,
            'tempo_espera_total': 0,
            'mudancas_estado': 0
        }
        
        # Configurações específicas por heurística
        self.config_heuristica = self._inicializar_config_heuristica()
    
    def _inicializar_config_heuristica(self) -> Dict:
        """Inicializa configurações específicas para cada heurística."""
        if self.heuristica == TipoHeuristica.WAVE_GREEN:
            return {
                'offset_por_cruzamento': 60,  # 1 segundo de offset entre cruzamentos
                'direcao_onda': Direcao.LESTE  # Direção prioritária da onda verde
            }
        elif self.heuristica == TipoHeuristica.ADAPTATIVA_DENSIDADE:
            return {
                'intervalo_avaliacao': 120,  # Avalia densidade a cada 2 segundos
                'tempo_desde_avaliacao': 0
            }
        return {}
    
    def adicionar_semaforo(self, semaforo: Semaforo) -> None:
        """Adiciona um semáforo ao gerenciador."""
        id_cruzamento = semaforo.id_cruzamento
        if id_cruzamento not in self.semaforos:
            self.semaforos[id_cruzamento] = {}
        self.semaforos[id_cruzamento][semaforo.direcao] = semaforo

    def avancar_manual(self) -> None:
        """
        Avança IMEDIATAMENTE o estado de todos os semáforos:
        Verde → Amarelo → Vermelho → Verde.
        """
        for semaforos_cruzamento in self.semaforos.values():
            for sem in semaforos_cruzamento.values():
                if sem.estado == EstadoSemaforo.VERDE:
                    sem._mudar_para_estado(EstadoSemaforo.AMARELO)
                elif sem.estado == EstadoSemaforo.AMARELO:
                    sem._mudar_para_estado(EstadoSemaforo.VERMELHO)
                elif sem.estado == EstadoSemaforo.VERMELHO:
                    sem._mudar_para_estado(EstadoSemaforo.VERDE)

    
    def atualizar(self, densidade_por_cruzamento: Dict[Tuple[int, int], Dict[Direcao, int]]) -> None:
        """
        Atualiza todos os semáforos baseado na heurística ativa.
        
        Args:
            densidade_por_cruzamento: Número de veículos por direção em cada cruzamento
        """
        self.tempo_ciclo += 1
        
        if self.heuristica == TipoHeuristica.TEMPO_FIXO:
            self._atualizar_tempo_fixo()
        elif self.heuristica == TipoHeuristica.ADAPTATIVA_SIMPLES:
            self._atualizar_adaptativa_simples(densidade_por_cruzamento)
        elif self.heuristica == TipoHeuristica.ADAPTATIVA_DENSIDADE:
            self._atualizar_adaptativa_densidade(densidade_por_cruzamento)
        elif self.heuristica == TipoHeuristica.WAVE_GREEN:
            self._atualizar_wave_green()
    
    def _atualizar_tempo_fixo(self) -> None:
        """Atualização com tempos fixos e alternância simples."""
        for id_cruzamento, semaforos_cruzamento in self.semaforos.items():
            # Atualiza cada semáforo
            for semaforo in semaforos_cruzamento.values():
                mudou = semaforo.atualizar()
                if mudou:
                    self.estatisticas_globais['mudancas_estado'] += 1
            
            # Verifica se precisa alternar (quando um fica vermelho, o outro fica verde)
            self._verificar_alternancia(semaforos_cruzamento)
    
    def _atualizar_adaptativa_simples(self, densidade: Dict) -> None:
        """Atualização adaptativa baseada em densidade simples."""
        for id_cruzamento, semaforos_cruzamento in self.semaforos.items():
            densidade_cruzamento = densidade.get(id_cruzamento, {})
            
            # Calcula qual direção tem mais veículos
            densidade_ns = densidade_cruzamento.get(Direcao.NORTE, 0) + densidade_cruzamento.get(Direcao.SUL, 0)
            densidade_lo = densidade_cruzamento.get(Direcao.LESTE, 0) + densidade_cruzamento.get(Direcao.OESTE, 0)
            
            # Ajusta tempos baseado na densidade
            for direcao, semaforo in semaforos_cruzamento.items():
                if direcao in [Direcao.NORTE, Direcao.SUL]:
                    if densidade_ns > densidade_lo * 1.5:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_ALTA)
                    else:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_MEDIA)
                else:
                    if densidade_lo > densidade_ns * 1.5:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_ALTA)
                    else:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_MEDIA)
                
                semaforo.atualizar()
            
            self._verificar_alternancia(semaforos_cruzamento)
    
    def _atualizar_adaptativa_densidade(self, densidade: Dict) -> None:
        """Atualização adaptativa com análise detalhada de densidade."""
        config = self.config_heuristica
        config['tempo_desde_avaliacao'] += 1
        
        for id_cruzamento, semaforos_cruzamento in self.semaforos.items():
            # Atualiza normalmente
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()
            
            # Avalia densidade periodicamente
            if config['tempo_desde_avaliacao'] >= config['intervalo_avaliacao']:
                densidade_cruzamento = densidade.get(id_cruzamento, {})
                self._ajustar_tempos_por_densidade(semaforos_cruzamento, densidade_cruzamento)
            
            self._verificar_alternancia(semaforos_cruzamento)
        
        if config['tempo_desde_avaliacao'] >= config['intervalo_avaliacao']:
            config['tempo_desde_avaliacao'] = 0
    
    def _atualizar_wave_green(self) -> None:
        """Atualização com onda verde para fluxo contínuo."""
        config = self.config_heuristica
        
        for id_cruzamento, semaforos_cruzamento in self.semaforos.items():
            # Calcula offset baseado na posição do cruzamento
            offset = id_cruzamento[1] * config['offset_por_cruzamento']
            
            # Determina fase atual considerando offset
            fase_ajustada = (self.tempo_ciclo + offset) % 480  # Ciclo completo de 8 segundos
            
            # Define estados baseado na fase
            if fase_ajustada < 180:  # Primeiros 3 segundos
                # Direção prioritária verde
                for direcao, semaforo in semaforos_cruzamento.items():
                    if direcao == config['direcao_onda'] or direcao == self._direcao_oposta(config['direcao_onda']):
                        if semaforo.estado != EstadoSemaforo.VERDE:
                            semaforo.forcar_mudanca(EstadoSemaforo.VERDE)
                    else:
                        if semaforo.estado != EstadoSemaforo.VERMELHO:
                            semaforo.forcar_mudanca(EstadoSemaforo.VERMELHO)
            elif fase_ajustada < 240:  # 1 segundo amarelo
                for direcao, semaforo in semaforos_cruzamento.items():
                    if direcao == config['direcao_onda'] or direcao == self._direcao_oposta(config['direcao_onda']):
                        if semaforo.estado == EstadoSemaforo.VERDE:
                            semaforo.forcar_mudanca(EstadoSemaforo.AMARELO)
            elif fase_ajustada < 420:  # 3 segundos para direção perpendicular
                for direcao, semaforo in semaforos_cruzamento.items():
                    if direcao in [Direcao.NORTE, Direcao.SUL]:
                        if semaforo.estado != EstadoSemaforo.VERDE:
                            semaforo.forcar_mudanca(EstadoSemaforo.VERDE)
                    else:
                        if semaforo.estado != EstadoSemaforo.VERMELHO:
                            semaforo.forcar_mudanca(EstadoSemaforo.VERMELHO)
            else:  # Último segundo amarelo
                for direcao, semaforo in semaforos_cruzamento.items():
                    if direcao in [Direcao.NORTE, Direcao.SUL]:
                        if semaforo.estado == EstadoSemaforo.VERDE:
                            semaforo.forcar_mudanca(EstadoSemaforo.AMARELO)
            
            # Atualiza os semáforos
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()
    
    def _verificar_alternancia(self, semaforos: Dict[Direcao, Semaforo]) -> None:
        """Verifica e corrige a alternância entre semáforos perpendiculares."""
        # Agrupa por eixo
        semaforos_ns = [s for d, s in semaforos.items() if d in [Direcao.NORTE, Direcao.SUL]]
        semaforos_lo = [s for d, s in semaforos.items() if d in [Direcao.LESTE, Direcao.OESTE]]
        
        # Verifica se algum eixo acabou de ficar vermelho
        ns_todos_vermelhos = all(s.estado == EstadoSemaforo.VERMELHO for s in semaforos_ns)
        lo_todos_vermelhos = all(s.estado == EstadoSemaforo.VERMELHO for s in semaforos_lo)
        
        # Se um eixo está todo vermelho e o outro também, libera o que esperou mais
        if ns_todos_vermelhos and lo_todos_vermelhos:
            tempo_espera_ns = sum(s.tempo_no_estado for s in semaforos_ns)
            tempo_espera_lo = sum(s.tempo_no_estado for s in semaforos_lo)
            
            if tempo_espera_ns > tempo_espera_lo:
                for s in semaforos_ns:
                    s.forcar_mudanca(EstadoSemaforo.VERDE)
            else:
                for s in semaforos_lo:
                    s.forcar_mudanca(EstadoSemaforo.VERDE)
        
        # Se um eixo acabou de ficar todo vermelho, o outro deve ficar verde
        elif ns_todos_vermelhos and any(s.tempo_no_estado < 2 for s in semaforos_ns):
            for s in semaforos_lo:
                if s.estado == EstadoSemaforo.VERMELHO:
                    s.forcar_mudanca(EstadoSemaforo.VERDE)
        elif lo_todos_vermelhos and any(s.tempo_no_estado < 2 for s in semaforos_lo):
            for s in semaforos_ns:
                if s.estado == EstadoSemaforo.VERMELHO:
                    s.forcar_mudanca(EstadoSemaforo.VERDE)
    
    def _ajustar_tempos_por_densidade(self, semaforos: Dict[Direcao, Semaforo], densidade: Dict[Direcao, int]) -> None:
        """Ajusta os tempos dos semáforos baseado na densidade."""
        for direcao, semaforo in semaforos.items():
            qtd_veiculos = densidade.get(direcao, 0)
            
            if qtd_veiculos <= CONFIG.LIMIAR_DENSIDADE_BAIXA:
                tempo_verde = CONFIG.TEMPO_VERDE_DENSIDADE_BAIXA
            elif qtd_veiculos <= CONFIG.LIMIAR_DENSIDADE_MEDIA:
                tempo_verde = CONFIG.TEMPO_VERDE_DENSIDADE_MEDIA
            else:
                tempo_verde = CONFIG.TEMPO_VERDE_DENSIDADE_ALTA
            
            semaforo.definir_tempo_verde(tempo_verde)
    
    def _direcao_oposta(self, direcao: Direcao) -> Direcao:
        """Retorna a direção oposta."""
        opostos = {
            Direcao.NORTE: Direcao.SUL,
            Direcao.SUL: Direcao.NORTE,
            Direcao.LESTE: Direcao.OESTE,
            Direcao.OESTE: Direcao.LESTE
        }
        return opostos[direcao]
    
    def mudar_heuristica(self, nova_heuristica: TipoHeuristica) -> None:
        """Muda a heurística de controle."""
        self.heuristica = nova_heuristica
        self.config_heuristica = self._inicializar_config_heuristica()
        self.tempo_ciclo = 0
    
    def obter_info_heuristica(self) -> str:
        """Retorna informação sobre a heurística atual."""
        nomes = {
            TipoHeuristica.TEMPO_FIXO: "Tempo Fixo",
            TipoHeuristica.ADAPTATIVA_SIMPLES: "Adaptativa Simples",
            TipoHeuristica.ADAPTATIVA_DENSIDADE: "Adaptativa por Densidade",
            TipoHeuristica.WAVE_GREEN: "Onda Verde",
            TipoHeuristica.MANUAL: "Controle Manual"
        }
        return nomes.get(self.heuristica, "Desconhecida")