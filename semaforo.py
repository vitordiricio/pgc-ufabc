"""
Módulo de semáforo com suporte a múltiplas heurísticas de controle.
Sistema com vias de mão única: Horizontal (Leste→Oeste) e Vertical (Norte→Sul)
"""
from typing import Tuple, Dict, Optional
from configuracao import CONFIG, EstadoSemaforo, Direcao, TipoHeuristica
from heuristica import criar_heuristica, Heuristica


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
        self.tipo_heuristica = heuristica
        self.heuristica: Heuristica = criar_heuristica(heuristica)
        self.semaforos: Dict[Tuple[int, int], Dict[Direcao, Semaforo]] = {}
        self.tempo_ciclo = 0
        self.estatisticas_globais = {
            'veiculos_total': 0,
            'tempo_espera_total': 0,
            'mudancas_estado': 0
        }
        
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
        if self.tipo_heuristica != TipoHeuristica.MANUAL:
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
        self.heuristica.tempo_ciclo = self.tempo_ciclo
        self.heuristica.atualizar(self.semaforos, densidade_por_cruzamento)
    
    
    def mudar_heuristica(self, nova_heuristica: TipoHeuristica) -> None:
        """Muda a heurística de controle."""
        self.tipo_heuristica = nova_heuristica
        self.heuristica = criar_heuristica(nova_heuristica)
        self.tempo_ciclo = 0
    
    def obter_info_heuristica(self) -> str:
        """Retorna informação sobre a heurística atual."""
        nomes = {
            TipoHeuristica.TEMPO_FIXO: "Tempo Fixo",
            TipoHeuristica.ADAPTATIVA_SIMPLES: "Adaptativa Simples",
            TipoHeuristica.ADAPTATIVA_DENSIDADE: "Adaptativa por Densidade",
            TipoHeuristica.WAVE_GREEN: "Onda Verde",
            TipoHeuristica.MANUAL: "Controle Manual",
            TipoHeuristica.LLM_HEURISTICA: "LLM Inteligente"
        }
        return nomes.get(self.tipo_heuristica, "Desconhecida")