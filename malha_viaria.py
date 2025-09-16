"""
Módulo de malha viária com sistema de rotas, matriz OD e pathfinding.
Implementa grafo de cruzamentos com algoritmos Dijkstra e A*.
"""
import heapq
import math
import random
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
from configuracao import CONFIG, Direcao


class TipoMovimento(Enum):
    """Tipos de movimento possíveis em um cruzamento."""
    RETA = "reta"
    ESQUERDA = "esquerda"
    DIREITA = "direita"


@dataclass
class Aresta:
    """Representa uma aresta no grafo da malha viária."""
    origem: Tuple[int, int]
    destino: Tuple[int, int]
    direcao: Direcao
    custo_base: float
    custo_atual: float
    bloqueada: bool = False
    movimento: TipoMovimento = TipoMovimento.RETA


@dataclass
class No:
    """Representa um nó (cruzamento) no grafo."""
    id: Tuple[int, int]
    posicao: Tuple[float, float]
    arestas_saida: List[Aresta] = None
    arestas_entrada: List[Aresta] = None
    
    def __post_init__(self):
        if self.arestas_saida is None:
            self.arestas_saida = []
        if self.arestas_entrada is None:
            self.arestas_entrada = []


class MatrizOD:
    """Matriz Origem-Destino para geração de rotas."""
    
    def __init__(self, linhas: int, colunas: int):
        """
        Inicializa a matriz OD.
        
        Args:
            linhas: Número de linhas de cruzamentos
            colunas: Número de colunas de cruzamentos
        """
        self.linhas = linhas
        self.colunas = colunas
        self.probabilidades = self._gerar_probabilidades_padrao()
    
    def _gerar_probabilidades_padrao(self) -> Dict[Tuple[Tuple[int, int], Tuple[int, int]], float]:
        """Gera probabilidades padrão para todos os pares origem-destino."""
        probabilidades = {}
        
        for origem_linha in range(self.linhas):
            for origem_col in range(self.colunas):
                for dest_linha in range(self.linhas):
                    for dest_col in range(self.colunas):
                        origem = (origem_linha, origem_col)
                        destino = (dest_linha, dest_col)
                        
                        if origem != destino:
                            # Probabilidade baseada na distância (mais próximo = mais provável)
                            distancia = math.sqrt((origem_linha - dest_linha)**2 + (origem_col - dest_col)**2)
                            prob_base = 1.0 / (1.0 + distancia * 0.5)
                            probabilidades[(origem, destino)] = prob_base
        
        # Normaliza as probabilidades
        total = sum(probabilidades.values())
        for chave in probabilidades:
            probabilidades[chave] /= total
        
        return probabilidades
    
    def obter_destino_aleatorio(self, origem: Tuple[int, int]) -> Tuple[int, int]:
        """
        Seleciona um destino aleatório baseado nas probabilidades.
        
        Args:
            origem: ID do cruzamento de origem
            
        Returns:
            ID do cruzamento de destino
        """
        # Filtra probabilidades para a origem específica
        probs_origem = {
            destino: prob for (orig, destino), prob in self.probabilidades.items()
            if orig == origem
        }
        
        if not probs_origem:
            # Fallback: destino aleatório
            dest_linha = random.randint(0, self.linhas - 1)
            dest_col = random.randint(0, self.colunas - 1)
            return (dest_linha, dest_col)
        
        # Seleção aleatória ponderada
        r = random.random()
        acumulado = 0.0
        
        for destino, prob in probs_origem.items():
            acumulado += prob
            if r <= acumulado:
                return destino
        
        # Fallback
        return list(probs_origem.keys())[0]
    
    def definir_probabilidade(self, origem: Tuple[int, int], destino: Tuple[int, int], probabilidade: float):
        """Define uma probabilidade específica para um par origem-destino."""
        self.probabilidades[(origem, destino)] = probabilidade


class Pathfinder:
    """Implementa algoritmos de pathfinding (Dijkstra e A*)."""
    
    def __init__(self, grafo: Dict[Tuple[int, int], No]):
        """
        Inicializa o pathfinder.
        
        Args:
            grafo: Dicionário de nós do grafo
        """
        self.grafo = grafo
    
    def dijkstra(self, origem: Tuple[int, int], destino: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Encontra o caminho mais curto usando algoritmo de Dijkstra.
        
        Args:
            origem: ID do nó de origem
            destino: ID do nó de destino
            
        Returns:
            Lista de IDs de nós do caminho (incluindo origem e destino)
        """
        if origem not in self.grafo or destino not in self.grafo:
            return []
        
        if origem == destino:
            return [origem]
        
        # Inicialização
        distancias = {no_id: float('inf') for no_id in self.grafo}
        predecessores = {no_id: None for no_id in self.grafo}
        visitados = set()
        
        distancias[origem] = 0.0
        fila_prioridade = [(0.0, origem)]
        
        while fila_prioridade:
            dist_atual, no_atual = heapq.heappop(fila_prioridade)
            
            if no_atual in visitados:
                continue
            
            visitados.add(no_atual)
            
            if no_atual == destino:
                break
            
            # Explora vizinhos
            for aresta in self.grafo[no_atual].arestas_saida:
                if aresta.bloqueada:
                    continue
                
                vizinho = aresta.destino
                if vizinho in visitados:
                    continue
                
                nova_distancia = dist_atual + aresta.custo_atual
                
                if nova_distancia < distancias[vizinho]:
                    distancias[vizinho] = nova_distancia
                    predecessores[vizinho] = no_atual
                    heapq.heappush(fila_prioridade, (nova_distancia, vizinho))
        
        # Reconstrói o caminho
        return self._reconstruir_caminho(predecessores, origem, destino)
    
    def a_star(self, origem: Tuple[int, int], destino: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Encontra o caminho mais curto usando algoritmo A*.
        
        Args:
            origem: ID do nó de origem
            destino: ID do nó de destino
            
        Returns:
            Lista de IDs de nós do caminho (incluindo origem e destino)
        """
        if origem not in self.grafo or destino not in self.grafo:
            return []
        
        if origem == destino:
            return [origem]
        
        # Inicialização
        g_score = {no_id: float('inf') for no_id in self.grafo}
        f_score = {no_id: float('inf') for no_id in self.grafo}
        predecessores = {no_id: None for no_id in self.grafo}
        
        g_score[origem] = 0.0
        f_score[origem] = self._heuristica(origem, destino)
        
        fila_aberta = [(f_score[origem], origem)]
        fila_aberta_set = {origem}
        fila_fechada = set()
        
        while fila_aberta:
            _, no_atual = heapq.heappop(fila_aberta)
            fila_aberta_set.discard(no_atual)
            
            if no_atual == destino:
                break
            
            fila_fechada.add(no_atual)
            
            # Explora vizinhos
            for aresta in self.grafo[no_atual].arestas_saida:
                if aresta.bloqueada:
                    continue
                
                vizinho = aresta.destino
                if vizinho in fila_fechada:
                    continue
                
                g_tentativa = g_score[no_atual] + aresta.custo_atual
                
                if g_tentativa < g_score[vizinho]:
                    predecessores[vizinho] = no_atual
                    g_score[vizinho] = g_tentativa
                    f_score[vizinho] = g_tentativa + self._heuristica(vizinho, destino)
                    
                    if vizinho not in fila_aberta_set:
                        heapq.heappush(fila_aberta, (f_score[vizinho], vizinho))
                        fila_aberta_set.add(vizinho)
        
        # Reconstrói o caminho
        return self._reconstruir_caminho(predecessores, origem, destino)
    
    def _heuristica(self, no_atual: Tuple[int, int], destino: Tuple[int, int]) -> float:
        """Calcula a heurística (distância euclidiana) para A*."""
        if no_atual not in self.grafo or destino not in self.grafo:
            return float('inf')
        
        pos_atual = self.grafo[no_atual].posicao
        pos_destino = self.grafo[destino].posicao
        
        return math.sqrt(
            (pos_atual[0] - pos_destino[0])**2 + 
            (pos_atual[1] - pos_destino[1])**2
        )
    
    def _reconstruir_caminho(self, predecessores: Dict, origem: Tuple[int, int], destino: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Reconstrói o caminho a partir dos predecessores."""
        if predecessores[destino] is None and origem != destino:
            return []  # Caminho não encontrado
        
        caminho = []
        no_atual = destino
        
        while no_atual is not None:
            caminho.append(no_atual)
            no_atual = predecessores[no_atual]
        
        caminho.reverse()
        return caminho


class MalhaViaria:
    """Gerencia a malha viária com sistema de rotas e pathfinding."""
    
    def __init__(self, linhas: int = CONFIG.LINHAS_GRADE, colunas: int = CONFIG.COLUNAS_GRADE):
        """
        Inicializa a malha viária.
        
        Args:
            linhas: Número de linhas de cruzamentos
            colunas: Número de colunas de cruzamentos
        """
        self.linhas = linhas
        self.colunas = colunas
        self.grafo: Dict[Tuple[int, int], No] = {}
        self.arestas: List[Aresta] = []
        self.matriz_od = MatrizOD(linhas, colunas)
        self.pathfinder = None
        
        # Inicializa o grafo
        self._construir_grafo()
        self.pathfinder = Pathfinder(self.grafo)
    
    def _construir_grafo(self):
        """Constrói o grafo da malha viária."""
        # Cria nós (cruzamentos)
        for linha in range(self.linhas):
            for coluna in range(self.colunas):
                id_cruzamento = (linha, coluna)
                x = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                y = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                
                self.grafo[id_cruzamento] = No(
                    id=id_cruzamento,
                    posicao=(x, y)
                )
        
        # Cria arestas (conexões entre cruzamentos)
        self._criar_arestas()
    
    def _criar_arestas(self):
        """Cria arestas entre cruzamentos adjacentes."""
        for linha in range(self.linhas):
            for coluna in range(self.colunas):
                origem = (linha, coluna)
                
                # Aresta para direita (Leste→Oeste)
                if coluna < self.colunas - 1:
                    destino = (linha, coluna + 1)
                    custo = CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                    
                    aresta = Aresta(
                        origem=origem,
                        destino=destino,
                        direcao=Direcao.LESTE,
                        custo_base=custo,
                        custo_atual=custo,
                        movimento=TipoMovimento.RETA
                    )
                    
                    self.grafo[origem].arestas_saida.append(aresta)
                    self.grafo[destino].arestas_entrada.append(aresta)
                    self.arestas.append(aresta)
                
                # Aresta para baixo (Norte→Sul)
                if linha < self.linhas - 1:
                    destino = (linha + 1, coluna)
                    custo = CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                    
                    aresta = Aresta(
                        origem=origem,
                        destino=destino,
                        direcao=Direcao.NORTE,
                        custo_base=custo,
                        custo_atual=custo,
                        movimento=TipoMovimento.RETA
                    )
                    
                    self.grafo[origem].arestas_saida.append(aresta)
                    self.grafo[destino].arestas_entrada.append(aresta)
                    self.arestas.append(aresta)
    
    def calcular_rota(self, origem: Tuple[int, int], destino: Tuple[int, int], algoritmo: str = "dijkstra") -> List[Tuple[int, int]]:
        """
        Calcula uma rota entre origem e destino.
        
        Args:
            origem: ID do cruzamento de origem
            destino: ID do cruzamento de destino
            algoritmo: "dijkstra" ou "a_star"
            
        Returns:
            Lista de IDs de cruzamentos da rota
        """
        if algoritmo == "dijkstra":
            return self.pathfinder.dijkstra(origem, destino)
        elif algoritmo == "a_star":
            return self.pathfinder.a_star(origem, destino)
        else:
            raise ValueError(f"Algoritmo não suportado: {algoritmo}")
    
    def obter_destino_aleatorio(self, origem: Tuple[int, int]) -> Tuple[int, int]:
        """
        Obtém um destino aleatório baseado na matriz OD.
        
        Args:
            origem: ID do cruzamento de origem
            
        Returns:
            ID do cruzamento de destino
        """
        return self.matriz_od.obter_destino_aleatorio(origem)
    
    def bloquear_aresta(self, origem: Tuple[int, int], destino: Tuple[int, int]):
        """
        Bloqueia uma aresta (simula incidente/obra).
        
        Args:
            origem: ID do cruzamento de origem
            destino: ID do cruzamento de destino
        """
        for aresta in self.arestas:
            if aresta.origem == origem and aresta.destino == destino:
                aresta.bloqueada = True
                aresta.custo_atual = float('inf')
                break
    
    def desbloquear_aresta(self, origem: Tuple[int, int], destino: Tuple[int, int]):
        """
        Desbloqueia uma aresta.
        
        Args:
            origem: ID do cruzamento de origem
            destino: ID do cruzamento de destino
        """
        for aresta in self.arestas:
            if aresta.origem == origem and aresta.destino == destino:
                aresta.bloqueada = False
                aresta.custo_atual = aresta.custo_base
                break
    
    def atualizar_custo_aresta(self, origem: Tuple[int, int], destino: Tuple[int, int], novo_custo: float):
        """
        Atualiza o custo de uma aresta (simula congestionamento).
        
        Args:
            origem: ID do cruzamento de origem
            destino: ID do cruzamento de destino
            novo_custo: Novo custo da aresta
        """
        for aresta in self.arestas:
            if aresta.origem == origem and aresta.destino == destino:
                aresta.custo_atual = novo_custo
                break
    
    def obter_arestas_adjacentes(self, no_id: Tuple[int, int]) -> List[Aresta]:
        """
        Obtém arestas adjacentes a um nó.
        
        Args:
            no_id: ID do nó
            
        Returns:
            Lista de arestas adjacentes
        """
        if no_id not in self.grafo:
            return []
        
        return self.grafo[no_id].arestas_saida
    
    def obter_posicao_cruzamento(self, no_id: Tuple[int, int]) -> Tuple[float, float]:
        """
        Obtém a posição de um cruzamento.
        
        Args:
            no_id: ID do cruzamento
            
        Returns:
            Posição (x, y) do cruzamento
        """
        if no_id not in self.grafo:
            return (0, 0)
        
        return self.grafo[no_id].posicao
    
    def definir_probabilidade_od(self, origem: Tuple[int, int], destino: Tuple[int, int], probabilidade: float):
        """
        Define uma probabilidade específica na matriz OD.
        
        Args:
            origem: ID do cruzamento de origem
            destino: ID do cruzamento de destino
            probabilidade: Probabilidade (0.0 a 1.0)
        """
        self.matriz_od.definir_probabilidade(origem, destino, probabilidade)
    
    def obter_estatisticas_grafo(self) -> Dict:
        """Retorna estatísticas do grafo."""
        total_nos = len(self.grafo)
        total_arestas = len(self.arestas)
        arestas_bloqueadas = sum(1 for a in self.arestas if a.bloqueada)
        
        return {
            'total_nos': total_nos,
            'total_arestas': total_arestas,
            'arestas_bloqueadas': arestas_bloqueadas,
            'densidade_grafo': total_arestas / total_nos if total_nos > 0 else 0
        }
