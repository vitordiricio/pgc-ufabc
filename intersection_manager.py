"""
Módulo de gerenciamento de interseções com reservas de conflitos por movimentos.
Sistema genérico com matriz 12x12 de conflitos e API de reservas.
"""
import math
import pygame
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
from configuracao import CONFIG, Direcao
from malha_viaria import TipoMovimento


@dataclass
class ZonaConflito:
    """Representa uma zona de conflito (polígono) entre dois movimentos."""
    movimento1: Tuple[Direcao, TipoMovimento]
    movimento2: Tuple[Direcao, TipoMovimento]
    poligono: List[Tuple[float, float]]  # Lista de pontos do polígono
    centro: Tuple[float, float]
    raio: float


@dataclass
class ReservaIntersecao:
    """Representa uma reserva de interseção."""
    veiculo_id: int
    movimento: Tuple[Direcao, TipoMovimento]
    tempo_inicio: float
    tempo_fim: float
    bbox_trajetoria: pygame.Rect
    zonas_ocupadas: List[ZonaConflito]
    ativa: bool = True
    prioridade: int = 0  # 0=normal, 1=ônibus, 2=emergência


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
        self.zonas_conflito = self._criar_zonas_conflito()
        self.tempo_atual = 0.0
        self.semaforo_verde = True  # Estado do semáforo
        self.margem_epsilon = 0.5  # Margem de segurança em metros
        
    def _criar_mapa_conflitos(self) -> Dict[Tuple[Direcao, TipoMovimento], Set[Tuple[Direcao, TipoMovimento]]]:
        """
        Cria matriz 12x12 de conflitos para os 12 movimentos possíveis.
        Para mão única, temos 2 direções x 3 movimentos = 6 movimentos.
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
        
        # Inicializa mapa de conflitos
        for movimento in movimentos:
            conflitos[movimento] = set()
            
            for outro_movimento in movimentos:
                if movimento != outro_movimento:
                    if self._movimentos_conflitam(movimento, outro_movimento):
                        conflitos[movimento].add(outro_movimento)
        
        return conflitos
    
    def _movimentos_conflitam(self, mov1: Tuple[Direcao, TipoMovimento], mov2: Tuple[Direcao, TipoMovimento]) -> bool:
        """
        Verifica se dois movimentos conflitam baseado na geometria do cruzamento.
        
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
        
        # Direções perpendiculares: verifica interseção de trajetórias
        if dir1 == Direcao.NORTE and dir2 == Direcao.LESTE:
            # Norte vs Leste
            return self._conflito_norte_leste(tipo1, tipo2)
        
        if dir1 == Direcao.LESTE and dir2 == Direcao.NORTE:
            # Leste vs Norte
            return self._conflito_leste_norte(tipo1, tipo2)
        
        return False
    
    def _conflito_norte_leste(self, tipo_norte: TipoMovimento, tipo_leste: TipoMovimento) -> bool:
        """Verifica conflito entre movimento Norte e Leste."""
        # Norte reto vs Leste reto: conflita no centro
        if tipo_norte == TipoMovimento.RETA and tipo_leste == TipoMovimento.RETA:
            return True
        
        # Norte direita vs Leste esquerda: conflita no centro
        if tipo_norte == TipoMovimento.DIREITA and tipo_leste == TipoMovimento.ESQUERDA:
            return True
        
        # Norte esquerda vs Leste direita: conflita no centro
        if tipo_norte == TipoMovimento.ESQUERDA and tipo_leste == TipoMovimento.DIREITA:
            return True
        
        return False
    
    def _conflito_leste_norte(self, tipo_leste: TipoMovimento, tipo_norte: TipoMovimento) -> bool:
        """Verifica conflito entre movimento Leste e Norte."""
        return self._conflito_norte_leste(tipo_norte, tipo_leste)
    
    def _criar_zonas_conflito(self) -> List[ZonaConflito]:
        """Cria zonas de conflito (polígonos) para cada par de movimentos conflitantes."""
        zonas = []
        x, y = self.posicao
        raio_zona = CONFIG.LARGURA_RUA / 2 + self.margem_epsilon
        
        # Zona central (conflito entre todos os movimentos retos)
        zona_central = ZonaConflito(
            movimento1=(Direcao.NORTE, TipoMovimento.RETA),
            movimento2=(Direcao.LESTE, TipoMovimento.RETA),
            poligono=[
                (x - raio_zona, y - raio_zona),
                (x + raio_zona, y - raio_zona),
                (x + raio_zona, y + raio_zona),
                (x - raio_zona, y + raio_zona)
            ],
            centro=(x, y),
            raio=raio_zona
        )
        zonas.append(zona_central)
        
        # Zonas de conversão (esquerda/direita)
        # Norte esquerda vs Leste direita
        zona_ne_ld = ZonaConflito(
            movimento1=(Direcao.NORTE, TipoMovimento.ESQUERDA),
            movimento2=(Direcao.LESTE, TipoMovimento.DIREITA),
            poligono=[
                (x - raio_zona, y - raio_zona),
                (x, y - raio_zona),
                (x, y),
                (x - raio_zona, y)
            ],
            centro=(x - raio_zona/2, y - raio_zona/2),
            raio=raio_zona/2
        )
        zonas.append(zona_ne_ld)
        
        # Norte direita vs Leste esquerda
        zona_nd_le = ZonaConflito(
            movimento1=(Direcao.NORTE, TipoMovimento.DIREITA),
            movimento2=(Direcao.LESTE, TipoMovimento.ESQUERDA),
            poligono=[
                (x, y - raio_zona),
                (x + raio_zona, y - raio_zona),
                (x + raio_zona, y),
                (x, y)
            ],
            centro=(x + raio_zona/2, y - raio_zona/2),
            raio=raio_zona/2
        )
        zonas.append(zona_nd_le)
        
        return zonas
    
    def can_request(self, movimento: Tuple[Direcao, TipoMovimento], janela_t: Tuple[float, float], 
                   traj: pygame.Rect) -> bool:
        """
        Verifica se uma reserva pode ser concedida.
        
        Args:
            movimento: Movimento solicitado (direção, tipo)
            janela_t: Janela temporal (t0, t1)
            traj: Bounding box da trajetória
            
        Returns:
            True se a reserva pode ser concedida
        """
        t0, t1 = janela_t
        
        # Verifica semáforo
        if not self.semaforo_verde:
            return False
        
        # Verifica conflitos com reservas ativas
        conflitos = self.mapa_conflitos.get(movimento, set())
        
        for reserva in self.reservas_ativas:
            if not reserva.ativa:
                continue
            
            # Verifica conflito temporal
            if self._tempos_conflitam(t0, t1, reserva.tempo_inicio, reserva.tempo_fim):
                # Verifica conflito espacial
                if traj.colliderect(reserva.bbox_trajetoria):
                    # Verifica conflito de movimento
                    if reserva.movimento in conflitos:
                        return False  # Conflito detectado
        
        return True
    
    def request(self, veiculo_id: int, movimento: Tuple[Direcao, TipoMovimento], 
                t0: float, t1: float, bbox_traj: pygame.Rect, prioridade: int = 0) -> bool:
        """
        Solicita uma reserva de interseção.
        
        Args:
            veiculo_id: ID do veículo
            movimento: Movimento solicitado
            t0: Tempo de início
            t1: Tempo de fim
            bbox_traj: Bounding box da trajetória
            prioridade: Prioridade do veículo (0=normal, 1=ônibus, 2=emergência)
            
        Returns:
            True se a reserva foi concedida
        """
        # Verifica se pode solicitar
        if not self.can_request(movimento, (t0, t1), bbox_traj):
            return False
        
        # Encontra zonas de conflito ocupadas
        zonas_ocupadas = self._encontrar_zonas_conflito(movimento, bbox_traj)
        
        # Cria nova reserva
        nova_reserva = ReservaIntersecao(
            veiculo_id=veiculo_id,
            movimento=movimento,
            tempo_inicio=t0,
            tempo_fim=t1,
            bbox_trajetoria=bbox_traj,
            zonas_ocupadas=zonas_ocupadas,
            prioridade=prioridade
        )
        
        # Adiciona reserva
        self.reservas_ativas.append(nova_reserva)
        
        # Log da reserva
        print(f"RESERVA CONCEDIDA: Veículo {veiculo_id} - {movimento[0].name} {movimento[1].value} - {t0:.1f}s a {t1:.1f}s")
        
        return True
    
    def release(self, veiculo_id: int) -> bool:
        """
        Libera uma reserva de interseção.
        
        Args:
            veiculo_id: ID do veículo
            
        Returns:
            True se a reserva foi liberada
        """
        for reserva in self.reservas_ativas:
            if reserva.veiculo_id == veiculo_id and reserva.ativa:
                reserva.ativa = False
                print(f"RESERVA LIBERADA: Veículo {veiculo_id} - {reserva.movimento[0].name} {reserva.movimento[1].value}")
                return True
        
        return False
    
    def _encontrar_zonas_conflito(self, movimento: Tuple[Direcao, TipoMovimento], 
                                 bbox: pygame.Rect) -> List[ZonaConflito]:
        """Encontra zonas de conflito ocupadas por um movimento."""
        zonas_ocupadas = []
        
        for zona in self.zonas_conflito:
            if (zona.movimento1 == movimento or zona.movimento2 == movimento):
                # Verifica se o bounding box intersecta com a zona
                if self._bbox_intersecta_zona(bbox, zona):
                    zonas_ocupadas.append(zona)
        
        return zonas_ocupadas
    
    def _bbox_intersecta_zona(self, bbox: pygame.Rect, zona: ZonaConflito) -> bool:
        """Verifica se um bounding box intersecta com uma zona de conflito."""
        # Verifica interseção com círculo (aproximação)
        centro_x, centro_y = zona.centro
        bbox_centro_x = bbox.centerx
        bbox_centro_y = bbox.centery
        
        distancia = math.sqrt((bbox_centro_x - centro_x)**2 + (bbox_centro_y - centro_y)**2)
        
        return distancia <= (zona.raio + max(bbox.width, bbox.height) / 2)
    
    def _tempos_conflitam(self, t0_1: float, t1_1: float, t0_2: float, t1_2: float) -> bool:
        """Verifica se dois intervalos temporais conflitam."""
        return not (t1_1 <= t0_2 or t1_2 <= t0_1)
    
    def atualizar_tempo(self, tempo: float) -> None:
        """Atualiza o tempo atual e remove reservas expiradas."""
        self.tempo_atual = tempo
        
        # Remove reservas expiradas
        self.reservas_ativas = [r for r in self.reservas_ativas if r.tempo_fim > tempo or r.ativa]
    
    def definir_semaforo(self, verde: bool) -> None:
        """Define o estado do semáforo."""
        self.semaforo_verde = verde
    
    def verificar_entrada_sem_reserva(self, veiculo_id: int) -> bool:
        """
        Verifica se um veículo está tentando entrar sem reserva.
        
        Args:
            veiculo_id: ID do veículo
            
        Returns:
            True se deve bloquear o veículo
        """
        # Verifica se há reserva ativa para este veículo
        for reserva in self.reservas_ativas:
            if reserva.veiculo_id == veiculo_id and reserva.ativa:
                return False  # Tem reserva, pode prosseguir
        
        return True  # Sem reserva, deve bloquear
    
    def desenhar_reservas(self, tela: pygame.Surface) -> None:
        """Desenha reservas ativas e zonas ocupadas para debug."""
        if not CONFIG.MOSTRAR_DEBUG_INTERSECAO:
            return
        
        # Desenha zonas de conflito
        for zona in self.zonas_conflito:
            pygame.draw.circle(tela, (255, 255, 0, 50), 
                             (int(zona.centro[0]), int(zona.centro[1])), 
                             int(zona.raio), 2)
        
        # Desenha reservas ativas
        for reserva in self.reservas_ativas:
            if reserva.ativa:
                # Cor baseada na prioridade
                if reserva.prioridade == 2:  # Emergência
                    cor = (255, 0, 0, 100)
                elif reserva.prioridade == 1:  # Ônibus
                    cor = (0, 255, 0, 100)
                else:  # Normal
                    cor = (0, 0, 255, 100)
                
                # Desenha bounding box da reserva
                pygame.draw.rect(tela, cor, reserva.bbox_trajetoria, 2)
                
                # Desenha zonas ocupadas
                for zona in reserva.zonas_ocupadas:
                    pygame.draw.circle(tela, (255, 0, 255, 100), 
                                     (int(zona.centro[0]), int(zona.centro[1])), 
                                     int(zona.raio), 3)
