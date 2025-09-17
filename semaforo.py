"""
Módulo de semáforo com suporte a múltiplas heurísticas de controle.
Sistema com vias de mão única: Horizontal (Leste→Oeste) e Vertical (Norte→Sul)
"""
from typing import Tuple, Dict, List, Optional
from enum import Enum
from configuracao import CONFIG, EstadoSemaforo, Direcao, TipoHeuristica


class Semaforo:
    """Representa um semáforo com controle inteligente para vias de mão única."""
    
    def __init__(self, posicao: Tuple[float, float], direcao: Direcao, id_cruzamento: Tuple[int, int]):
        """
        Inicializa um semáforo.
        
        Args:
            posicao: Posição (x, y) do semáforo
            direcao: Direção do tráfego que o semáforo controla (NORTE ou LESTE)
            id_cruzamento: ID do cruzamento ao qual pertence
        """
        self.posicao = posicao
        self.direcao = direcao
        self.id_cruzamento = id_cruzamento
        
        # Estado inicial - alterna entre direções para evitar conflitos
        if direcao == Direcao.NORTE:
            self.estado = EstadoSemaforo.VERDE
        else:  # Direcao.LESTE
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

        self._click_rect = None

    def contem_ponto(self, pos: Tuple[int, int]) -> bool:
        """Retorna True se o ponto do mouse está sobre este semáforo (usado no modo MANUAL)."""
        return self._click_rect is not None and self._click_rect.collidepoint(pos)

    def ciclo_manual(self) -> None:
        """Cicla estados manualmente: Verde -> Amarelo -> Vermelho -> Verde."""
        if self.estado == EstadoSemaforo.VERDE:
            self._mudar_para_estado(EstadoSemaforo.AMARELO)
        elif self.estado == EstadoSemaforo.AMARELO:
            self._mudar_para_estado(EstadoSemaforo.VERMELHO)
        else:  # VERMELHO
            self._mudar_para_estado(EstadoSemaforo.VERDE)

    
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
            # Não muda automaticamente - controlado pelo gerenciador
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
        """Retorna a posição onde os veículos devem parar - MÃO ÚNICA."""
        offset = CONFIG.DISTANCIA_PARADA_SEMAFORO
        
        if self.direcao == Direcao.NORTE:
            # Veículos vindo do norte param antes do cruzamento
            return (self.posicao[0], self.posicao[1] - offset)
        elif self.direcao == Direcao.LESTE:
            # Veículos vindo do leste param antes do cruzamento
            return (self.posicao[0] - offset, self.posicao[1])
        
        return self.posicao
    


class GerenciadorSemaforos:
    """Gerencia todos os semáforos com suporte a heurísticas - MÃO ÚNICA."""
    
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
        self._click_rect = None  # retângulo usado para clique

    def _semaforo_em_pos(self, pos: Tuple[int, int]) -> Optional[Semaforo]:
        """Retorna o primeiro semáforo sob o ponto do mouse (ou None)."""
        for sems in self.semaforos.values():
            for sem in sems.values():
                if sem.contem_ponto(pos):
                    return sem
        return None

    def clique_em(self, pos: Tuple[int, int]) -> Optional[Tuple[Tuple[int,int], Direcao, EstadoSemaforo]]:
        """
        Trata clique do usuário. Só age em modo MANUAL para não ser sobreescrito pela heurística.
        Retorna (id_cruzamento, direcao, novo_estado) em caso de sucesso.
        """
        if self.heuristica != TipoHeuristica.MANUAL:
            return None

        sem = self._semaforo_em_pos(pos)
        if not sem:
            return None

        # Cicla estado do semáforo clicado
        sem.ciclo_manual()

        # Se ficou VERDE, garanta que o outro da mesma interseção fique VERMELHO (evita verdes conflitantes)
        outro_dir = Direcao.LESTE if sem.direcao == Direcao.NORTE else Direcao.NORTE
        sems_cruz = self.semaforos.get(sem.id_cruzamento, {})
        outro = sems_cruz.get(outro_dir)
        if outro and sem.estado == EstadoSemaforo.VERDE:
            outro._mudar_para_estado(EstadoSemaforo.VERMELHO)

        return (sem.id_cruzamento, sem.direcao, sem.estado)

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
        """Atualização com tempos fixos e alternância simples - MÃO ÚNICA."""
        for id_cruzamento, semaforos_cruzamento in self.semaforos.items():
            # Atualiza cada semáforo
            for semaforo in semaforos_cruzamento.values():
                mudou = semaforo.atualizar()
                if mudou:
                    self.estatisticas_globais['mudancas_estado'] += 1
            
            # Verifica alternância simples entre Norte e Leste
            self._verificar_alternancia_mao_unica(semaforos_cruzamento)
    
    def _atualizar_adaptativa_simples(self, densidade: Dict) -> None:
        """Atualização adaptativa baseada em densidade simples - MÃO ÚNICA."""
        for id_cruzamento, semaforos_cruzamento in self.semaforos.items():
            densidade_cruzamento = densidade.get(id_cruzamento, {})
            
            # Calcula densidade para cada direção
            densidade_norte = densidade_cruzamento.get(Direcao.NORTE, 0)
            densidade_leste = densidade_cruzamento.get(Direcao.LESTE, 0)
            
            # Ajusta tempos baseado na densidade
            for direcao, semaforo in semaforos_cruzamento.items():
                if direcao == Direcao.NORTE:
                    if densidade_norte > densidade_leste * 1.5:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_ALTA)
                    else:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_MEDIA)
                elif direcao == Direcao.LESTE:
                    if densidade_leste > densidade_norte * 1.5:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_ALTA)
                    else:
                        semaforo.definir_tempo_verde(CONFIG.TEMPO_VERDE_DENSIDADE_MEDIA)
                
                semaforo.atualizar()
            
            self._verificar_alternancia_mao_unica(semaforos_cruzamento)
    
    def _atualizar_adaptativa_densidade(self, densidade: Dict) -> None:
        """Atualização adaptativa com análise detalhada de densidade - MÃO ÚNICA."""
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
            
            self._verificar_alternancia_mao_unica(semaforos_cruzamento)
        
        if config['tempo_desde_avaliacao'] >= config['intervalo_avaliacao']:
            config['tempo_desde_avaliacao'] = 0
    
    def _atualizar_wave_green(self) -> None:
        """Atualização com onda verde para fluxo contínuo - MÃO ÚNICA."""
        config = self.config_heuristica
        
        for id_cruzamento, semaforos_cruzamento in self.semaforos.items():
            # Calcula offset baseado na posição do cruzamento
            offset = id_cruzamento[1] * config['offset_por_cruzamento']
            
            # Determina fase atual considerando offset
            fase_ajustada = (self.tempo_ciclo + offset) % 480  # Ciclo completo de 8 segundos
            
            # Define estados baseado na fase - simplificado para mão única
            if fase_ajustada < 180:  # Primeiros 3 segundos - prioridade horizontal
                # Leste verde, Norte vermelho
                if Direcao.LESTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.LESTE].estado != EstadoSemaforo.VERDE:
                        semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.VERDE)
                if Direcao.NORTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.NORTE].estado != EstadoSemaforo.VERMELHO:
                        semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.VERMELHO)
            elif fase_ajustada < 240:  # 1 segundo amarelo
                if Direcao.LESTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.LESTE].estado == EstadoSemaforo.VERDE:
                        semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.AMARELO)
            elif fase_ajustada < 420:  # 3 segundos - prioridade vertical
                # Norte verde, Leste vermelho
                if Direcao.NORTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.NORTE].estado != EstadoSemaforo.VERDE:
                        semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.VERDE)
                if Direcao.LESTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.LESTE].estado != EstadoSemaforo.VERMELHO:
                        semaforos_cruzamento[Direcao.LESTE].forcar_mudanca(EstadoSemaforo.VERMELHO)
            else:  # Último segundo amarelo
                if Direcao.NORTE in semaforos_cruzamento:
                    if semaforos_cruzamento[Direcao.NORTE].estado == EstadoSemaforo.VERDE:
                        semaforos_cruzamento[Direcao.NORTE].forcar_mudanca(EstadoSemaforo.AMARELO)
            
            # Atualiza os semáforos
            for semaforo in semaforos_cruzamento.values():
                semaforo.atualizar()
    
    def _verificar_alternancia_mao_unica(self, semaforos: Dict[Direcao, Semaforo]) -> None:
        """Verifica e corrige a alternância entre semáforos - MÃO ÚNICA."""
        # Apenas duas direções: NORTE e LESTE
        semaforo_norte = semaforos.get(Direcao.NORTE)
        semaforo_leste = semaforos.get(Direcao.LESTE)
        
        if not semaforo_norte or not semaforo_leste:
            return
        
        # Se ambos estão vermelhos, libera o que esperou mais
        if (semaforo_norte.estado == EstadoSemaforo.VERMELHO and 
            semaforo_leste.estado == EstadoSemaforo.VERMELHO):
            
            if semaforo_norte.tempo_no_estado > semaforo_leste.tempo_no_estado:
                semaforo_norte.forcar_mudanca(EstadoSemaforo.VERDE)
            else:
                semaforo_leste.forcar_mudanca(EstadoSemaforo.VERDE)
        
        # Se um acabou de ficar vermelho, o outro deve ficar verde
        elif (semaforo_norte.estado == EstadoSemaforo.VERMELHO and 
              semaforo_norte.tempo_no_estado < 2):
            if semaforo_leste.estado == EstadoSemaforo.VERMELHO:
                semaforo_leste.forcar_mudanca(EstadoSemaforo.VERDE)
        elif (semaforo_leste.estado == EstadoSemaforo.VERMELHO and 
              semaforo_leste.tempo_no_estado < 2):
            if semaforo_norte.estado == EstadoSemaforo.VERMELHO:
                semaforo_norte.forcar_mudanca(EstadoSemaforo.VERDE)
    
    def _ajustar_tempos_por_densidade(self, semaforos: Dict[Direcao, Semaforo], densidade: Dict[Direcao, int]) -> None:
        """Ajusta os tempos dos semáforos baseado na densidade - MÃO ÚNICA."""
        for direcao, semaforo in semaforos.items():
            if direcao not in CONFIG.DIRECOES_PERMITIDAS:
                continue
                
            qtd_veiculos = densidade.get(direcao, 0)
            
            if qtd_veiculos <= CONFIG.LIMIAR_DENSIDADE_BAIXA:
                tempo_verde = CONFIG.TEMPO_VERDE_DENSIDADE_BAIXA
            elif qtd_veiculos <= CONFIG.LIMIAR_DENSIDADE_MEDIA:
                tempo_verde = CONFIG.TEMPO_VERDE_DENSIDADE_MEDIA
            else:
                tempo_verde = CONFIG.TEMPO_VERDE_DENSIDADE_ALTA
            
            semaforo.definir_tempo_verde(tempo_verde)
    
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