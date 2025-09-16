"""
Módulo de cruzamento para a simulação de tráfego com múltiplos cruzamentos.
Sistema com vias de mão única: Horizontal (Leste→Oeste) e Vertical (Norte→Sul)
"""
import random
import math
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import pygame
from configuracao import CONFIG, Direcao, TipoHeuristica
from veiculo import Veiculo
from semaforo import Semaforo, GerenciadorSemaforos
from malha_viaria import TipoMovimento, MalhaViaria as MalhaViariaPathfinding
from sistema_faixas import LaneManager
from intersection_manager import IntersectionManager


@dataclass
class ReservaIntersecao:
    """Representa uma reserva de interseção."""
    veiculo_id: int
    movimento: TipoMovimento
    tempo_inicio: float
    tempo_fim: float
    bbox_trajetoria: pygame.Rect
    ativa: bool = True


class IntersectionManager:
    """Gerencia reservas de interseção para evitar colisões."""
    
    def __init__(self, cruzamento_id: Tuple[int, int], posicao: Tuple[float, float]):
        """
        Inicializa o gerenciador de interseção.
        
        Args:
            cruzamento_id: ID do cruzamento
            posicao: Posição do centro do cruzamento
        """
        self.cruzamento_id = cruzamento_id
        self.posicao = posicao
        self.reservas_ativas: List[ReservaIntersecao] = []
        self.mapa_conflitos = self._criar_mapa_conflitos()
        self.tempo_atual = 0.0
    
    def _criar_mapa_conflitos(self) -> Dict[Tuple[Direcao, TipoMovimento], Set[Tuple[Direcao, TipoMovimento]]]:
        """
        Cria mapa de conflitos para os 12 movimentos possíveis.
        Para mão única, temos apenas 2 direções x 3 movimentos = 6 movimentos.
        """
        conflitos = {}
        
        # Movimentos possíveis para mão única
        movimentos = [
            (Direcao.NORTE, TipoMovimento.RETA),
            (Direcao.NORTE, TipoMovimento.ESQUERDA),
            (Direcao.NORTE, TipoMovimento.DIREITA),
            (Direcao.LESTE, TipoMovimento.RETA),
            (Direcao.LESTE, TipoMovimento.ESQUERDA),
            (Direcao.LESTE, TipoMovimento.DIREITA)
        ]
        
        # Define conflitos baseados na geometria do cruzamento
        for movimento in movimentos:
            conflitos[movimento] = set()
            
            for outro_movimento in movimentos:
                if movimento != outro_movimento:
                    # Conflitos básicos: movimentos opostos e perpendiculares
                    if self._movimentos_conflitam(movimento, outro_movimento):
                        conflitos[movimento].add(outro_movimento)
        
        return conflitos
    
    def _movimentos_conflitam(self, mov1: Tuple[Direcao, TipoMovimento], mov2: Tuple[Direcao, TipoMovimento]) -> bool:
        """
        Verifica se dois movimentos conflitam.
        
        Args:
            mov1: Primeiro movimento (direção, tipo)
            mov2: Segundo movimento (direção, tipo)
            
        Returns:
            True se os movimentos conflitam
        """
        dir1, tipo1 = mov1
        dir2, tipo2 = mov2
        
        # Mesma direção: sempre conflita
        if dir1 == dir2:
            return True
        
        # Direções perpendiculares: verifica se há interseção
        if dir1 == Direcao.NORTE and dir2 == Direcao.LESTE:
            # Norte vs Leste: conflita se ambos vão reto ou se um vira
            return (tipo1 == TipoMovimento.RETA and tipo2 == TipoMovimento.RETA) or \
                   (tipo1 == TipoMovimento.DIREITA and tipo2 == TipoMovimento.ESQUERDA)
        
        if dir1 == Direcao.LESTE and dir2 == Direcao.NORTE:
            # Leste vs Norte: conflita se ambos vão reto ou se um vira
            return (tipo1 == TipoMovimento.RETA and tipo2 == TipoMovimento.RETA) or \
                   (tipo1 == TipoMovimento.ESQUERDA and tipo2 == TipoMovimento.DIREITA)
        
        return False
    
    def solicitar_reserva(self, veiculo_id: int, movimento: TipoMovimento, direcao: Direcao, 
                         tempo_inicio: float, bbox_trajetoria: pygame.Rect) -> bool:
        """
        Solicita uma reserva de interseção.
        
        Args:
            veiculo_id: ID do veículo
            movimento: Tipo de movimento
            direcao: Direção do veículo
            tempo_inicio: Tempo de início da reserva
            bbox_trajetoria: Bounding box da trajetória
            
        Returns:
            True se a reserva foi concedida
        """
        # Calcula tempo de fim baseado no tamanho da trajetória
        tempo_fim = tempo_inicio + CONFIG.DT_RESERVA
        
        # Verifica conflitos com reservas ativas
        movimento_chave = (direcao, movimento)
        conflitos = self.mapa_conflitos.get(movimento_chave, set())
        
        for reserva in self.reservas_ativas:
            if not reserva.ativa:
                continue
            
            # Verifica conflito temporal
            if self._tempos_conflitam(tempo_inicio, tempo_fim, reserva.tempo_inicio, reserva.tempo_fim):
                # Verifica conflito espacial
                if bbox_trajetoria.colliderect(reserva.bbox_trajetoria):
                    # Verifica conflito de movimento
                    reserva_movimento = self._obter_movimento_reserva(reserva)
                    if reserva_movimento in conflitos:
                        return False  # Conflito detectado
        
        # Cria nova reserva
        nova_reserva = ReservaIntersecao(
            veiculo_id=veiculo_id,
            movimento=movimento,
            tempo_inicio=tempo_inicio,
            tempo_fim=tempo_fim,
            bbox_trajetoria=bbox_trajetoria
        )
        
        self.reservas_ativas.append(nova_reserva)
        return True
    
    def _tempos_conflitam(self, inicio1: float, fim1: float, inicio2: float, fim2: float) -> bool:
        """Verifica se dois intervalos de tempo conflitam."""
        return not (fim1 <= inicio2 or fim2 <= inicio1)
    
    def _obter_movimento_reserva(self, reserva: ReservaIntersecao) -> Tuple[Direcao, TipoMovimento]:
        """Obtém o movimento de uma reserva (simplificado)."""
        # Em uma implementação completa, isso seria armazenado na reserva
        # Por simplicidade, assumimos que todas as reservas são retas
        return (Direcao.NORTE, reserva.movimento)  # Simplificado
    
    def liberar_reserva(self, veiculo_id: int):
        """
        Libera uma reserva de interseção.
        
        Args:
            veiculo_id: ID do veículo
        """
        for reserva in self.reservas_ativas:
            if reserva.veiculo_id == veiculo_id:
                reserva.ativa = False
                break
    
    def limpar_reservas_expiradas(self, tempo_atual: float):
        """
        Remove reservas expiradas.
        
        Args:
            tempo_atual: Tempo atual da simulação
        """
        self.reservas_ativas = [
            reserva for reserva in self.reservas_ativas
            if reserva.ativa and reserva.tempo_fim > tempo_atual
        ]
    
    def atualizar_tempo(self, tempo_atual: float):
        """
        Atualiza o tempo interno do gerenciador.
        
        Args:
            tempo_atual: Tempo atual da simulação
        """
        self.tempo_atual = tempo_atual
        self.limpar_reservas_expiradas(tempo_atual)
    
    def obter_reservas_ativas(self) -> List[ReservaIntersecao]:
        """Retorna lista de reservas ativas."""
        return [r for r in self.reservas_ativas if r.ativa]
    
    def verificar_conflito_imediato(self, movimento: TipoMovimento, direcao: Direcao, 
                                   bbox_trajetoria: pygame.Rect) -> bool:
        """
        Verifica se há conflito imediato sem criar reserva.
        
        Args:
            movimento: Tipo de movimento
            direcao: Direção do veículo
            bbox_trajetoria: Bounding box da trajetória
            
        Returns:
            True se há conflito imediato
        """
        movimento_chave = (direcao, movimento)
        conflitos = self.mapa_conflitos.get(movimento_chave, set())
        
        for reserva in self.reservas_ativas:
            if not reserva.ativa:
                continue
            
            if bbox_trajetoria.colliderect(reserva.bbox_trajetoria):
                reserva_movimento = self._obter_movimento_reserva(reserva)
                if reserva_movimento in conflitos:
                    return True
        
        return False


class Cruzamento:
    """Representa um cruzamento de tráfego com controle inteligente e vias de mão única."""

    def __init__(
        self,
        posicao: Tuple[float, float],
        id_cruzamento: Tuple[int, int],
        gerenciador_semaforos: GerenciadorSemaforos,
        malha_viaria: 'MalhaViaria'
    ):
        """
        Inicializa o cruzamento.

        Args:
            posicao: Posição (x, y) do centro do cruzamento
            id_cruzamento: Identificador (linha, coluna) do cruzamento
            gerenciador_semaforos: Gerenciador global de semáforos
            malha_viaria: Referência para a malha (usada para consultar o "caos")
        """
        self.id = id_cruzamento
        self.posicao = posicao
        self.centro_x, self.centro_y = posicao
        self.gerenciador_semaforos = gerenciador_semaforos
        self.malha = malha_viaria  # <<< referência à malha
        
        # IntersectionManager para controle de conflitos
        self.intersection_manager = IntersectionManager(id_cruzamento, posicao)

        # Veículos no cruzamento - APENAS DIREÇÕES PERMITIDAS
        self.veiculos_por_direcao: Dict[Direcao, List[Veiculo]] = {
            Direcao.NORTE: [],  # Norte→Sul
            Direcao.LESTE: []   # Leste→Oeste
        }

        # Configurações do cruzamento
        self.largura_rua = CONFIG.LARGURA_RUA
        self.limites = self._calcular_limites()

        # Configurar semáforos apenas para as direções permitidas
        self._configurar_semaforos()

        # Estatísticas
        self.estatisticas = {
            'veiculos_processados': 0,
            'tempo_espera_acumulado': 0,
            'densidade_atual': 0
        }

    def _calcular_limites(self) -> Dict[str, float]:
        """Calcula os limites físicos do cruzamento."""
        margem = self.largura_rua // 2
        return {
            'esquerda': self.centro_x - margem,
            'direita': self.centro_x + margem,
            'topo': self.centro_y - margem,
            'base': self.centro_y + margem
        }

    def _configurar_semaforos(self) -> None:
        """Configura os semáforos do cruzamento - apenas para direções permitidas."""
        offset = self.largura_rua // 2 + 30

        # Cria semáforos apenas para direções de mão única
        semaforos = {}

        # Semáforo para tráfego Norte→Sul (vindo de cima)
        semaforos[Direcao.NORTE] = Semaforo(
            (self.centro_x - offset, self.centro_y - offset),
            Direcao.NORTE, self.id
        )

        # Semáforo para tráfego Leste→Oeste (vindo da esquerda)
        semaforos[Direcao.LESTE] = Semaforo(
            (self.centro_x - offset, self.centro_y + offset),
            Direcao.LESTE, self.id
        )

        # Adiciona ao gerenciador
        for semaforo in semaforos.values():
            self.gerenciador_semaforos.adicionar_semaforo(semaforo)

    def pode_gerar_veiculo(self, direcao: Direcao) -> bool:
        """Verifica se pode gerar veículo em uma direção específica - MÃO ÚNICA."""
        # Só permite direções de mão única
        if direcao not in CONFIG.DIRECOES_PERMITIDAS:
            return False

        linha, coluna = self.id

        # Define onde cada direção pode gerar veículos
        pode_gerar = {
            # Norte: apenas no topo (linha 0), veículos vão para baixo
            Direcao.NORTE: linha == 0 and CONFIG.PONTOS_SPAWN['NORTE'],
            # Leste: apenas na esquerda (coluna 0), veículos vão para direita
            Direcao.LESTE: coluna == 0 and CONFIG.PONTOS_SPAWN['LESTE'],
            # Sul e Oeste desativados - mão única
            Direcao.SUL: False,
            Direcao.OESTE: False
        }

        return pode_gerar.get(direcao, False)

    def gerar_veiculos(self) -> List[Veiculo]:
        """Gera novos veículos nas bordas apropriadas - APENAS MÃO ÚNICA."""
        novos_veiculos = []

        # Apenas tenta gerar nas direções permitidas
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            if not self.pode_gerar_veiculo(direcao):
                continue

            if random.random() < CONFIG.TAXA_GERACAO_VEICULO:
                posicao = self._calcular_posicao_inicial(direcao)

                # Verifica se há espaço
                if self._tem_espaco_para_gerar(direcao, posicao):
                    veiculo = Veiculo(direcao, posicao, self.id)
                    
                    # Define rota para o veículo
                    if self.malha and self.malha.malha_pathfinding:
                        destino = self.malha.malha_pathfinding.obter_destino_aleatorio(self.id)
                        rota = self.malha.malha_pathfinding.calcular_rota(
                            self.id, destino, CONFIG.ALGORITMO_PATHFINDING
                        )
                        if rota:
                            veiculo.definir_rota(rota, self.malha.malha_pathfinding)
                    
                    # Define lane manager para o veículo
                    if self.malha and self.malha.lane_managers:
                        # Determina qual lane manager usar baseado na direção e posição
                        if direcao == Direcao.LESTE:
                            linha = self.id[0]
                            lane_manager = self.malha.lane_managers.get((linha, -1))
                        elif direcao == Direcao.NORTE:
                            coluna = self.id[1]
                            lane_manager = self.malha.lane_managers.get((-1, coluna))
                        else:
                            lane_manager = None
                        
                    if lane_manager:
                        veiculo.definir_lane_manager(lane_manager)
                    
                    # Atribui intersection manager
                    if self.malha and hasattr(self.malha, 'intersection_managers'):
                        intersection_manager = self.malha.intersection_managers.get(self.id)
                        if intersection_manager:
                            veiculo.definir_intersection_manager(intersection_manager)
                    
                    novos_veiculos.append(veiculo)
                    self.veiculos_por_direcao[direcao].append(veiculo)

        return novos_veiculos

    def _calcular_posicao_inicial(self, direcao: Direcao) -> Tuple[float, float]:
        """Calcula a posição inicial para um veículo - MÃO ÚNICA, sem escolha de faixa."""
        if direcao == Direcao.NORTE:
            # Spawn no topo, vai para baixo
            return (self.centro_x, -50)
        elif direcao == Direcao.LESTE:
            # Spawn na esquerda, vai para direita
            return (-50, self.centro_y)
        else:
            # Não deveria chegar aqui com mão única
            return (0, 0)

    def _tem_espaco_para_gerar(self, direcao: Direcao, posicao: Tuple[float, float]) -> bool:
        """Verifica se há espaço suficiente para gerar um novo veículo."""
        for veiculo in self.veiculos_por_direcao.get(direcao, []):
            dx = abs(veiculo.posicao[0] - posicao[0])
            dy = abs(veiculo.posicao[1] - posicao[1])

            if direcao == Direcao.NORTE:
                if dy < CONFIG.DISTANCIA_MIN_VEICULO * 2:
                    return False
            elif direcao == Direcao.LESTE:
                if dx < CONFIG.DISTANCIA_MIN_VEICULO * 2:
                    return False

        return True

    def _determinar_cruzamento_veiculo(self, veiculo: Veiculo) -> Tuple[int, int]:
        """
        Determina qual cruzamento o veículo está mais próximo.

        Args:
            veiculo: Veículo a verificar

        Returns:
            ID do cruzamento mais próximo
        """
        # Calcula em qual cruzamento o veículo está baseado em sua posição
        coluna = int((veiculo.posicao[0] - CONFIG.POSICAO_INICIAL_X + CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS / 2) /
                    CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
        linha = int((veiculo.posicao[1] - CONFIG.POSICAO_INICIAL_Y + CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS / 2) /
                   CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)

        # Limita aos valores válidos
        coluna = max(0, min(coluna, CONFIG.COLUNAS_GRADE - 1))
        linha = max(0, min(linha, CONFIG.LINHAS_GRADE - 1))

        return (linha, coluna)

    def atualizar_veiculos(self, todos_veiculos: List[Veiculo]) -> None:
        """Atualiza o estado dos veículos no cruzamento - CORRIGIDO."""
        # Limpa listas antigas
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            self.veiculos_por_direcao[direcao] = []

        # Reorganiza veículos por direção e proximidade
        veiculos_proximos = []
        for veiculo in todos_veiculos:
            if veiculo.direcao in CONFIG.DIRECOES_PERMITIDAS and self._veiculo_proximo_ao_cruzamento(veiculo):
                # Verifica se o veículo mudou de cruzamento
                cruzamento_atual = self._determinar_cruzamento_veiculo(veiculo)
                if cruzamento_atual == self.id:
                    # Reset do controle de semáforo se mudou de cruzamento
                    veiculo.resetar_controle_semaforo(self.id)
                    self.veiculos_por_direcao[veiculo.direcao].append(veiculo)
                    veiculos_proximos.append(veiculo)

        # Processa cada direção permitida
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            veiculos = self.veiculos_por_direcao.get(direcao, [])
            if not veiculos:
                continue

            # CORRIGIDO: Ordena veículos por posição absoluta na via
            veiculos_ordenados = self._ordenar_veiculos_por_posicao(veiculos, direcao)

            # Obtém semáforo da direção
            semaforos = self.gerenciador_semaforos.semaforos.get(self.id, {})
            semaforo = semaforos.get(direcao)

            # Processa cada veículo
            for i, veiculo in enumerate(veiculos_ordenados):
                # IMPORTANTE: Processa interação com TODOS os veículos, não apenas os do cruzamento
                veiculo.processar_todos_veiculos(todos_veiculos)

                # Sistema de reservas de interseção
                if self._veiculo_proximo_ao_cruzamento(veiculo):
                    # Verifica se precisa solicitar reserva
                    if not veiculo.estado_reserva and veiculo.proximo_no:
                        # Solicita reserva de interseção
                        reserva_concedida = veiculo.solicitar_reserva_intersecao()
                        if not reserva_concedida:
                            # Reserva negada: para o veículo
                            veiculo.velocidade = 0
                            veiculo.aceleracao_atual = 0
                            continue

                # Processa semáforo se estiver antes da linha
                if semaforo:
                    posicao_parada = semaforo.obter_posicao_parada()

                    # Verifica se o veículo está antes da linha de parada
                    if self._veiculo_antes_da_linha(veiculo, posicao_parada):
                        veiculo.processar_semaforo(semaforo, posicao_parada)

                # Atualiza posição com verificação de colisão
                # >>> agora passamos a malha para aplicar o "caos" local de velocidade
                veiculo.atualizar(1.0, todos_veiculos, self.malha)

                # Libera reserva se saiu do cruzamento
                if veiculo.estado_reserva and not self._veiculo_proximo_ao_cruzamento(veiculo):
                    veiculo.liberar_reserva_intersecao(self)

                # Atualiza estatísticas
                if veiculo.parado and veiculo.aguardando_semaforo:
                    self.estatisticas['tempo_espera_acumulado'] += 1

        # Atualiza densidade
        self.estatisticas['densidade_atual'] = sum(
            len(veiculos) for direcao, veiculos in self.veiculos_por_direcao.items()
            if direcao in CONFIG.DIRECOES_PERMITIDAS
        )
        
        # Atualiza IntersectionManager
        self.intersection_manager.atualizar_tempo(self.malha.metricas['tempo_simulacao'] / CONFIG.FPS)

    def _veiculo_antes_da_linha(self, veiculo: Veiculo, posicao_parada: Tuple[float, float]) -> bool:
        """
        Verifica se o veículo está antes da linha de parada.

        Args:
            veiculo: Veículo a verificar
            posicao_parada: Posição da linha de parada

        Returns:
            True se o veículo está antes da linha
        """
        margem = CONFIG.DISTANCIA_DETECCAO_SEMAFORO

        if veiculo.direcao == Direcao.NORTE:
            # Norte→Sul: está antes se Y do veículo < Y da linha + margem
            return veiculo.posicao[1] < posicao_parada[1] + margem
        elif veiculo.direcao == Direcao.LESTE:
            # Leste→Oeste: está antes se X do veículo < X da linha + margem
            return veiculo.posicao[0] < posicao_parada[0] + margem

        return False

    def _veiculo_proximo_ao_cruzamento(self, veiculo: Veiculo) -> bool:
        """Verifica se um veículo está próximo o suficiente do cruzamento."""
        distancia_limite = CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS * 0.7

        dx = abs(veiculo.posicao[0] - self.centro_x)
        dy = abs(veiculo.posicao[1] - self.centro_y)

        return dx < distancia_limite or dy < distancia_limite

    def _ordenar_veiculos_por_posicao(self, veiculos: List[Veiculo], direcao: Direcao) -> List[Veiculo]:
        """
        CORRIGIDO: Ordena veículos por posição absoluta na via.
        O primeiro da lista é o que está mais à frente (mais perto do destino).
        """
        if direcao == Direcao.NORTE:
            # Norte→Sul: o mais à frente tem MAIOR Y (está mais para baixo)
            return sorted(veiculos, key=lambda v: v.posicao[1], reverse=True)
        elif direcao == Direcao.LESTE:
            # Leste→Oeste: o mais à frente tem MAIOR X (está mais para direita)
            return sorted(veiculos, key=lambda v: v.posicao[0], reverse=True)

        return veiculos

    def solicitar_reserva_intersecao(self, veiculo_id: int, movimento: TipoMovimento, 
                                   direcao: Direcao, bbox_trajetoria: pygame.Rect) -> bool:
        """
        Solicita reserva de interseção para um veículo.
        
        Args:
            veiculo_id: ID do veículo
            movimento: Tipo de movimento
            direcao: Direção do veículo
            bbox_trajetoria: Bounding box da trajetória
            
        Returns:
            True se a reserva foi concedida
        """
        tempo_atual = self.malha.metricas['tempo_simulacao'] / CONFIG.FPS
        return self.intersection_manager.solicitar_reserva(
            veiculo_id, movimento, direcao, tempo_atual, bbox_trajetoria
        )
    
    def liberar_reserva_intersecao(self, veiculo_id: int):
        """
        Libera reserva de interseção de um veículo.
        
        Args:
            veiculo_id: ID do veículo
        """
        self.intersection_manager.liberar_reserva(veiculo_id)
    
    def verificar_conflito_intersecao(self, movimento: TipoMovimento, direcao: Direcao, 
                                    bbox_trajetoria: pygame.Rect) -> bool:
        """
        Verifica se há conflito imediato na interseção.
        
        Args:
            movimento: Tipo de movimento
            direcao: Direção do veículo
            bbox_trajetoria: Bounding box da trajetória
            
        Returns:
            True se há conflito
        """
        return self.intersection_manager.verificar_conflito_imediato(
            movimento, direcao, bbox_trajetoria
        )
    
    def obter_reservas_ativas(self) -> List[ReservaIntersecao]:
        """Retorna lista de reservas ativas da interseção."""
        return self.intersection_manager.obter_reservas_ativas()

    def obter_densidade_por_direcao(self) -> Dict[Direcao, int]:
        """Retorna a densidade de veículos por direção."""
        return {
            direcao: len(self.veiculos_por_direcao.get(direcao, []))
            for direcao in CONFIG.DIRECOES_PERMITIDAS
        }

    def desenhar(self, tela: pygame.Surface) -> None:
        """Desenha o cruzamento e seus elementos."""
        # Desenha área do cruzamento
        area_cruzamento = pygame.Rect(
            self.limites['esquerda'],
            self.limites['topo'],
            self.largura_rua,
            self.largura_rua
        )
        pygame.draw.rect(tela, CONFIG.CINZA, area_cruzamento)

        # Desenha linhas de parada apenas para direções permitidas
        self._desenhar_linhas_parada(tela)

        # Desenha semáforos
        semaforos = self.gerenciador_semaforos.semaforos.get(self.id, {})
        for semaforo in semaforos.values():
            semaforo.desenhar(tela)

        # Desenha informações debug
        if CONFIG.MOSTRAR_INFO_VEICULO:
            self._desenhar_info_debug(tela)

    def _desenhar_linhas_parada(self, tela: pygame.Surface) -> None:
        """Desenha as linhas de parada apenas para direções de mão única."""
        cor_linha = CONFIG.BRANCO
        largura_linha = 3

        # Linha Norte (horizontal, antes do cruzamento vindo de cima)
        pygame.draw.line(tela,
                        cor_linha,
                        (self.limites['esquerda'], self.limites['topo'] - 20),
                        (self.limites['direita'], self.limites['topo'] - 20),
                        largura_linha)

        # Linha Leste (vertical, antes do cruzamento vindo da esquerda)
        pygame.draw.line(tela,
                        cor_linha,
                        (self.limites['esquerda'] - 20, self.limites['topo']),
                        (self.limites['esquerda'] - 20, self.limites['base']),
                        largura_linha)

    def _desenhar_info_debug(self, tela: pygame.Surface) -> None:
        """Desenha informações de debug."""
        fonte = pygame.font.SysFont('Arial', 12)
        texto = f"C({self.id[0]},{self.id[1]}) D:{self.estatisticas['densidade_atual']}"
        superficie = fonte.render(texto, True, CONFIG.BRANCO)
        tela.blit(superficie, (self.centro_x - 30, self.centro_y - 10))


class MalhaViaria:
    """Gerencia toda a malha viária com múltiplos cruzamentos e vias de mão única."""

    def __init__(self, linhas: int = CONFIG.LINHAS_GRADE, colunas: int = CONFIG.COLUNAS_GRADE):
        """
        Inicializa a malha viária.

        Args:
            linhas: Número de linhas de cruzamentos
            colunas: Número de colunas de cruzamentos
        """
        self.linhas = linhas
        self.colunas = colunas
        self.veiculos: List[Veiculo] = []
        self.cruzamentos: Dict[Tuple[int, int], Cruzamento] = {}

        # Gerenciador de semáforos
        self.gerenciador_semaforos = GerenciadorSemaforos(CONFIG.HEURISTICA_ATIVA)

        # Sistema de pathfinding
        self.malha_pathfinding = MalhaViariaPathfinding(linhas, colunas)

        # Sistema de faixas
        self.lane_managers: Dict[Tuple[int, int], LaneManager] = {}
        self.intersection_managers: Dict[Tuple[int, int], IntersectionManager] = {}
        self._inicializar_lane_managers()
        self._inicializar_intersection_managers()

        # Efeito "caos" por via/trecho
        self._inicializar_caos()  # <<< inicializa mapas de caos

        # Criar cruzamentos
        self._criar_cruzamentos()

        # Métricas
        self.metricas = {
            'tempo_simulacao': 0,
            'veiculos_total': 0,
            'veiculos_concluidos': 0,
            'tempo_viagem_total': 0,
            'tempo_parado_total': 0
        }
    
    def _inicializar_lane_managers(self):
        """Inicializa os gerenciadores de faixas para cada via."""
        # Cria lane managers para vias horizontais
        for linha in range(self.linhas):
            y = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            self.lane_managers[(linha, -1)] = LaneManager(Direcao.LESTE, y, CONFIG.NUM_FAIXAS)
        
        # Cria lane managers para vias verticais
        for coluna in range(self.colunas):
            x = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            self.lane_managers[(-1, coluna)] = LaneManager(Direcao.NORTE, x, CONFIG.NUM_FAIXAS)
    
    def _inicializar_intersection_managers(self):
        """Inicializa os intersection managers para cada cruzamento."""
        for linha in range(self.linhas):
            for coluna in range(self.colunas):
                x = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                y = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                self.intersection_managers[(linha, coluna)] = IntersectionManager(
                    (linha, coluna), (x, y)
                )

    # -------------------
    # EFEITO CAOS - ruas
    # -------------------
    def _inicializar_caos(self) -> None:
        """Cria os vetores de caos por via (horizontal/vertical) segmentados ao longo da tela."""
        seg = CONFIG.CHAOS_TAMANHO_SEGMENTO
        self._caos_seg_h = math.ceil(CONFIG.LARGURA_TELA / seg) + 1
        self._caos_seg_v = math.ceil(CONFIG.ALTURA_TELA / seg) + 1

        # Cada linha horizontal tem um vetor de segmentos ao longo do X
        self.caos_horizontal: Dict[int, List[float]] = {
            linha: [1.0] * self._caos_seg_h for linha in range(self.linhas)
        }
        # Cada coluna vertical tem um vetor de segmentos ao longo do Y
        self.caos_vertical: Dict[int, List[float]] = {
            coluna: [1.0] * self._caos_seg_v for coluna in range(self.colunas)
        }

    def atualizar_caos(self) -> None:
        """Aleatoriza fatores ocasionalmente por segmento."""
        if not CONFIG.CHAOS_ATIVO:
            return
        p = CONFIG.CHAOS_PROB_MUTACAO
        fmin, fmax = CONFIG.CHAOS_FATOR_MIN, CONFIG.CHAOS_FATOR_MAX

        # horizontais
        for linha in range(self.linhas):
            v = self.caos_horizontal[linha]
            for i in range(len(v)):
                if random.random() < p:
                    v[i] = random.uniform(fmin, fmax)

        # verticais
        for coluna in range(self.colunas):
            v = self.caos_vertical[coluna]
            for i in range(len(v)):
                if random.random() < p:
                    v[i] = random.uniform(fmin, fmax)

    def obter_fator_caos(self, veiculo: Veiculo) -> float:
        """Retorna o fator de caos (multiplicador de velocidade máx local) para a posição do veículo."""
        if not CONFIG.CHAOS_ATIVO:
            return 1.0

        seg = CONFIG.CHAOS_TAMANHO_SEGMENTO

        if veiculo.direcao == Direcao.LESTE:
            # via horizontal: achar linha (índice da rua horizontal) e o segmento X
            linha_mais_prox = max(0, min(
                self.linhas - 1,
                round((veiculo.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
            ))
            seg_x = max(0, min(self._caos_seg_h - 1, int(veiculo.posicao[0] // seg)))
            return self.caos_horizontal[linha_mais_prox][seg_x]

        elif veiculo.direcao == Direcao.NORTE:
            # via vertical: achar coluna (índice da rua vertical) e o segmento Y
            coluna_mais_prox = max(0, min(
                self.colunas - 1,
                round((veiculo.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
            ))
            seg_y = max(0, min(self._caos_seg_v - 1, int(veiculo.posicao[1] // seg)))
            return self.caos_vertical[coluna_mais_prox][seg_y]

        return 1.0

    def _criar_cruzamentos(self) -> None:
        """Cria a grade de cruzamentos."""
        for linha in range(self.linhas):
            for coluna in range(self.colunas):
                x = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                y = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS

                id_cruzamento = (linha, coluna)
                self.cruzamentos[id_cruzamento] = Cruzamento(
                    (x, y), id_cruzamento, self.gerenciador_semaforos, self  # <<< passa self (malha)
                )

    def atualizar(self) -> None:
        """Atualiza toda a malha viária - CORRIGIDO com detecção global."""
        self.metricas['tempo_simulacao'] += 1

        # Atualiza "caos" das vias
        self.atualizar_caos()

        # Atualiza lane managers
        for lane_manager in self.lane_managers.values():
            lane_manager.atualizar_posicoes_veiculos()
        
        # Atualiza intersection managers
        for intersection_manager in self.intersection_managers.values():
            intersection_manager.atualizar_tempo(self.metricas['tempo_simulacao'])

        # Gera novos veículos
        for cruzamento in self.cruzamentos.values():
            novos_veiculos = cruzamento.gerar_veiculos()
            self.veiculos.extend(novos_veiculos)
            self.metricas['veiculos_total'] += len(novos_veiculos)

        # IMPORTANTE: Ordena TODOS os veículos globalmente por direção e posição
        veiculos_por_via = self._organizar_veiculos_por_via()

        # Atualiza veículos em cada cruzamento, passando a lista completa
        for cruzamento in self.cruzamentos.values():
            cruzamento.atualizar_veiculos(self.veiculos)

        # Coleta densidade para heurísticas
        densidade_por_cruzamento = {}
        for id_cruzamento, cruzamento in self.cruzamentos.items():
            densidade_por_cruzamento[id_cruzamento] = cruzamento.obter_densidade_por_direcao()

        # Atualiza semáforos com base na heurística
        self.gerenciador_semaforos.atualizar(densidade_por_cruzamento)

        # Remove veículos inativos e coleta métricas
        veiculos_ativos = []
        for veiculo in self.veiculos:
            if veiculo.ativo:
                veiculos_ativos.append(veiculo)
            else:
                # Veículo completou trajeto
                self.metricas['veiculos_concluidos'] += 1
                self.metricas['tempo_viagem_total'] += veiculo.tempo_viagem
                self.metricas['tempo_parado_total'] += veiculo.tempo_parado

        self.veiculos = veiculos_ativos

    def _organizar_veiculos_por_via(self) -> Dict[Tuple[Direcao, int], List[Veiculo]]:
        """
        Organiza todos os veículos por via (direção e posição da via).
        Retorna um dicionário onde a chave é (direção, índice_da_via).
        """
        veiculos_por_via = {}

        for veiculo in self.veiculos:
            if veiculo.direcao == Direcao.NORTE:
                # Via vertical - agrupa por X
                via_x = round(veiculo.posicao[0] / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
                chave = (Direcao.NORTE, via_x)
            elif veiculo.direcao == Direcao.LESTE:
                # Via horizontal - agrupa por Y
                via_y = round(veiculo.posicao[1] / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
                chave = (Direcao.LESTE, via_y)
            else:
                continue

            if chave not in veiculos_por_via:
                veiculos_por_via[chave] = []
            veiculos_por_via[chave].append(veiculo)

        # Ordena veículos em cada via por posição
        for chave, veiculos in veiculos_por_via.items():
            direcao = chave[0]
            if direcao == Direcao.NORTE:
                # Ordena por Y (maior Y = mais à frente)
                veiculos.sort(key=lambda v: v.posicao[1], reverse=True)
            elif direcao == Direcao.LESTE:
                # Ordena por X (maior X = mais à frente)
                veiculos.sort(key=lambda v: v.posicao[0], reverse=True)

        return veiculos_por_via

    def mudar_heuristica(self, nova_heuristica: TipoHeuristica) -> None:
        """Muda a heurística de controle de semáforos."""
        self.gerenciador_semaforos.mudar_heuristica(nova_heuristica)

    def obter_estatisticas(self) -> Dict[str, any]:
        """Retorna estatísticas consolidadas."""
        veiculos_ativos = len(self.veiculos)

        # Calcula médias
        tempo_viagem_medio = 0
        tempo_parado_medio = 0

        if self.metricas['veiculos_concluidos'] > 0:
            tempo_viagem_medio = self.metricas['tempo_viagem_total'] / self.metricas['veiculos_concluidos'] / CONFIG.FPS
            tempo_parado_medio = self.metricas['tempo_parado_total'] / self.metricas['veiculos_concluidos'] / CONFIG.FPS

        return {
            'veiculos_ativos': veiculos_ativos,
            'veiculos_total': self.metricas['veiculos_total'],
            'veiculos_concluidos': self.metricas['veiculos_concluidos'],
            'tempo_viagem_medio': tempo_viagem_medio,
            'tempo_parado_medio': tempo_parado_medio,
            'heuristica': self.gerenciador_semaforos.obter_info_heuristica(),
            'tempo_simulacao': self.metricas['tempo_simulacao'] / CONFIG.FPS,
            'estatisticas_grafo': self.malha_pathfinding.obter_estatisticas_grafo()
        }
    
    def bloquear_aresta(self, origem: Tuple[int, int], destino: Tuple[int, int]):
        """
        Bloqueia uma aresta (simula incidente/obra).
        
        Args:
            origem: ID do cruzamento de origem
            destino: ID do cruzamento de destino
        """
        self.malha_pathfinding.bloquear_aresta(origem, destino)
    
    def desbloquear_aresta(self, origem: Tuple[int, int], destino: Tuple[int, int]):
        """
        Desbloqueia uma aresta.
        
        Args:
            origem: ID do cruzamento de origem
            destino: ID do cruzamento de destino
        """
        self.malha_pathfinding.desbloquear_aresta(origem, destino)
    
    def atualizar_custo_aresta(self, origem: Tuple[int, int], destino: Tuple[int, int], novo_custo: float):
        """
        Atualiza o custo de uma aresta (simula congestionamento).
        
        Args:
            origem: ID do cruzamento de origem
            destino: ID do cruzamento de destino
            novo_custo: Novo custo da aresta
        """
        self.malha_pathfinding.atualizar_custo_aresta(origem, destino, novo_custo)

    def desenhar(self, tela: pygame.Surface) -> None:
        """Desenha toda a malha viária."""
        # Desenha as ruas
        self._desenhar_ruas(tela)

        # Desenha os cruzamentos
        for cruzamento in self.cruzamentos.values():
            cruzamento.desenhar(tela)

        # Desenha os veículos
        for veiculo in self.veiculos:
            veiculo.desenhar(tela)
        
        # Desenha reservas de interseção (debug)
        for intersection_manager in self.intersection_managers.values():
            intersection_manager.desenhar_reservas(tela)

    def _desenhar_ruas(self, tela: pygame.Surface) -> None:
        """Desenha as ruas da malha com múltiplas faixas (e overlay opcional do CAOS)."""
        # Desenha ruas horizontais (Leste→Oeste)
        for linha in range(self.linhas):
            y = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS

            # Fundo da rua
            pygame.draw.rect(tela, CONFIG.CINZA_ESCURO,
                           (0, y - CONFIG.LARGURA_RUA // 2,
                            CONFIG.LARGURA_TELA, CONFIG.LARGURA_RUA))
            
            # Desenha faixas
            self._desenhar_faixas_horizontais(tela, y)

            # Desenha indicadores de direção
            self._desenhar_setas_horizontais(tela, y, Direcao.LESTE)

            # Bordas da rua (sem linha central)
            pygame.draw.line(tela, CONFIG.BRANCO,
                           (0, y - CONFIG.LARGURA_RUA // 2),
                           (CONFIG.LARGURA_TELA, y - CONFIG.LARGURA_RUA // 2), 2)
            pygame.draw.line(tela, CONFIG.BRANCO,
                           (0, y + CONFIG.LARGURA_RUA // 2),
                           (CONFIG.LARGURA_TELA, y + CONFIG.LARGURA_RUA // 2), 2)

            # Overlay do "caos" (opcional)
            if CONFIG.CHAOS_MOSTRAR:
                seg = CONFIG.CHAOS_TAMANHO_SEGMENTO
                y_top = y - CONFIG.LARGURA_RUA // 2
                vetor = self.caos_horizontal[linha]
                for i, fator in enumerate(vetor):
                    x0 = i * seg
                    w = seg if x0 + seg <= CONFIG.LARGURA_TELA else CONFIG.LARGURA_TELA - x0
                    if w <= 0:
                        continue
                    surf = pygame.Surface((w, CONFIG.LARGURA_RUA), pygame.SRCALPHA)
                    # vermelho suave se <1; verde suave se >1
                    if fator < 1.0:
                        cor = (255, 80, 80, int((1.0 - fator) * 80))
                    else:
                        cor = (80, 255, 80, int((fator - 1.0) * 80))
                    surf.fill(cor)
                    tela.blit(surf, (x0, y_top))

        # Desenha ruas verticais (Norte→Sul)
        for coluna in range(self.colunas):
            x = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS

            # Fundo da rua
            pygame.draw.rect(tela, CONFIG.CINZA_ESCURO,
                           (x - CONFIG.LARGURA_RUA // 2, 0,
                            CONFIG.LARGURA_RUA, CONFIG.ALTURA_TELA))
            
            # Desenha faixas
            self._desenhar_faixas_verticais(tela, x)

            # Desenha indicadores de direção
            self._desenhar_setas_verticais(tela, x, Direcao.NORTE)

            # Bordas da rua (sem linha central)
            pygame.draw.line(tela, CONFIG.BRANCO,
                           (x - CONFIG.LARGURA_RUA // 2, 0),
                           (x - CONFIG.LARGURA_RUA // 2, CONFIG.ALTURA_TELA), 2)
            pygame.draw.line(tela, CONFIG.BRANCO,
                           (x + CONFIG.LARGURA_RUA // 2, 0),
                           (x + CONFIG.LARGURA_RUA // 2, CONFIG.ALTURA_TELA), 2)

            # Overlay do "caos" (opcional)
            if CONFIG.CHAOS_MOSTRAR:
                seg = CONFIG.CHAOS_TAMANHO_SEGMENTO
                x_left = x - CONFIG.LARGURA_RUA // 2
                vetor = self.caos_vertical[coluna]
                for j, fator in enumerate(vetor):
                    y0 = j * seg
                    h = seg if y0 + seg <= CONFIG.ALTURA_TELA else CONFIG.ALTURA_TELA - y0
                    if h <= 0:
                        continue
                    surf = pygame.Surface((CONFIG.LARGURA_RUA, h), pygame.SRCALPHA)
                    if fator < 1.0:
                        cor = (255, 80, 80, int((1.0 - fator) * 80))
                    else:
                        cor = (80, 255, 80, int((fator - 1.0) * 80))
                    surf.fill(cor)
                    tela.blit(surf, (x_left, y0))

    def _desenhar_setas_horizontais(self, tela: pygame.Surface, y: float, direcao: Direcao) -> None:
        """Desenha setas indicando a direção do fluxo horizontal."""
        if not CONFIG.MOSTRAR_DIRECAO_FLUXO:
            return

        # Desenha setas a cada intervalo
        intervalo = 100
        tamanho_seta = 15

        for x in range(50, CONFIG.LARGURA_TELA, intervalo):
            # Evita desenhar setas nos cruzamentos
            perto_de_cruzamento = False
            for coluna in range(self.colunas):
                x_cruzamento = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                if abs(x - x_cruzamento) < CONFIG.LARGURA_RUA:
                    perto_de_cruzamento = True
                    break

            if not perto_de_cruzamento:
                # Desenha seta para direita (Leste→Oeste)
                pontos = [
                    (x - tamanho_seta, y - 5),
                    (x - tamanho_seta, y + 5),
                    (x, y)
                ]
                pygame.draw.polygon(tela, CONFIG.AMARELO, pontos)

    def _desenhar_setas_verticais(self, tela: pygame.Surface, x: float, direcao: Direcao) -> None:
        """Desenha setas indicando a direção do fluxo vertical."""
        if not CONFIG.MOSTRAR_DIRECAO_FLUXO:
            return

        # Desenha setas a cada intervalo
        intervalo = 100
        tamanho_seta = 15

        for y in range(50, CONFIG.ALTURA_TELA, intervalo):
            # Evita desenhar setas nos cruzamentos
            perto_de_cruzamento = False
            for linha in range(self.linhas):
                y_cruzamento = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                if abs(y - y_cruzamento) < CONFIG.LARGURA_RUA:
                    perto_de_cruzamento = True
                    break

            if not perto_de_cruzamento:
                # Desenha seta para baixo (Norte→Sul)
                pontos = [
                    (x - 5, y - tamanho_seta),
                    (x + 5, y - tamanho_seta),
                    (x, y)
                ]
                pygame.draw.polygon(tela, CONFIG.AMARELO, pontos)
    
    def _desenhar_faixas_horizontais(self, tela: pygame.Surface, y: float) -> None:
        """Desenha as faixas de uma rua horizontal."""
        if not CONFIG.MOSTRAR_GRID:
            return
        
        # Desenha linhas divisórias das faixas
        cor_linha = CONFIG.CINZA_CLARO
        largura_linha = 1
        
        for i in range(1, CONFIG.NUM_FAIXAS):
            x_faixa = CONFIG.POSICAO_INICIAL_X + i * CONFIG.LARGURA_FAIXA
            pygame.draw.line(tela, cor_linha,
                           (0, y - CONFIG.LARGURA_RUA // 2 + i * CONFIG.LARGURA_FAIXA),
                           (CONFIG.LARGURA_TELA, y - CONFIG.LARGURA_RUA // 2 + i * CONFIG.LARGURA_FAIXA),
                           largura_linha)
    
    def _desenhar_faixas_verticais(self, tela: pygame.Surface, x: float) -> None:
        """Desenha as faixas de uma rua vertical."""
        if not CONFIG.MOSTRAR_GRID:
            return
        
        # Desenha linhas divisórias das faixas
        cor_linha = CONFIG.CINZA_CLARO
        largura_linha = 1
        
        for i in range(1, CONFIG.NUM_FAIXAS):
            y_faixa = CONFIG.POSICAO_INICIAL_Y + i * CONFIG.LARGURA_FAIXA
            pygame.draw.line(tela, cor_linha,
                           (x - CONFIG.LARGURA_RUA // 2 + i * CONFIG.LARGURA_FAIXA, 0),
                           (x - CONFIG.LARGURA_RUA // 2 + i * CONFIG.LARGURA_FAIXA, CONFIG.ALTURA_TELA),
                           largura_linha)
