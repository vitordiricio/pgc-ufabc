"""
Módulo de cruzamento para a simulação de tráfego com múltiplos cruzamentos.
Sistema com vias de mão única: Horizontal (Leste→Oeste) e Vertical (Norte→Sul)
"""
import random
from typing import List, Dict, Tuple
import pygame
from configuracao import CONFIG, Direcao, TipoHeuristica
from veiculo import Veiculo
from semaforo import Semaforo, GerenciadorSemaforos


class Cruzamento:
    """Representa um cruzamento de tráfego com controle inteligente e vias de mão única."""
    
    def __init__(self, posicao: Tuple[float, float], id_cruzamento: Tuple[int, int], 
                 gerenciador_semaforos: GerenciadorSemaforos):
        """
        Inicializa o cruzamento.
        
        Args:
            posicao: Posição (x, y) do centro do cruzamento
            id_cruzamento: Identificador (linha, coluna) do cruzamento
            gerenciador_semaforos: Gerenciador global de semáforos
        """
        self.id = id_cruzamento
        self.posicao = posicao
        self.centro_x, self.centro_y = posicao
        self.gerenciador_semaforos = gerenciador_semaforos
        
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
        max_linha = CONFIG.LINHAS_GRADE - 1
        max_coluna = CONFIG.COLUNAS_GRADE - 1
        
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
                    novos_veiculos.append(veiculo)
                    self.veiculos_por_direcao[direcao].append(veiculo)
        
        return novos_veiculos
    
    def _calcular_posicao_inicial(self, direcao: Direcao) -> Tuple[float, float]:
        """Calcula a posição inicial para um veículo - MÃO ÚNICA, sem escolha de faixa."""
        # Posição centralizada na via (sem offset de faixa)
        
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
    
    def atualizar_veiculos(self, todos_veiculos: List[Veiculo]) -> None:
        """Atualiza o estado dos veículos no cruzamento."""
        # Limpa listas antigas
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            self.veiculos_por_direcao[direcao] = []
        
        # Reorganiza veículos por direção e proximidade
        for veiculo in todos_veiculos:
            if veiculo.direcao in CONFIG.DIRECOES_PERMITIDAS and self._veiculo_proximo_ao_cruzamento(veiculo):
                self.veiculos_por_direcao[veiculo.direcao].append(veiculo)
        
        # Processa cada direção permitida
        for direcao in CONFIG.DIRECOES_PERMITIDAS:
            veiculos = self.veiculos_por_direcao.get(direcao, [])
            if not veiculos:
                continue
            
            # Ordena veículos por proximidade ao cruzamento
            veiculos_ordenados = self._ordenar_veiculos_por_proximidade(veiculos, direcao)
            
            # Obtém semáforo da direção
            semaforos = self.gerenciador_semaforos.semaforos.get(self.id, {})
            semaforo = semaforos.get(direcao)
            
            # Processa cada veículo
            for i, veiculo in enumerate(veiculos_ordenados):
                # Identifica veículo à frente
                veiculo_frente = veiculos_ordenados[i-1] if i > 0 else None
                
                # Processa semáforo
                if semaforo and not veiculo.passou_semaforo:
                    posicao_parada = semaforo.obter_posicao_parada()
                    veiculo.processar_semaforo(semaforo, posicao_parada)
                
                # Processa veículo à frente
                if veiculo_frente:
                    veiculo.processar_veiculo_frente(veiculo_frente)
                
                # Atualiza posição
                veiculo.atualizar()
                
                # Atualiza estatísticas
                if veiculo.parado and veiculo.aguardando_semaforo:
                    self.estatisticas['tempo_espera_acumulado'] += 1
        
        # Atualiza densidade
        self.estatisticas['densidade_atual'] = sum(
            len(veiculos) for direcao, veiculos in self.veiculos_por_direcao.items()
            if direcao in CONFIG.DIRECOES_PERMITIDAS
        )
    
    def _veiculo_proximo_ao_cruzamento(self, veiculo: Veiculo) -> bool:
        """Verifica se um veículo está próximo o suficiente do cruzamento."""
        distancia_limite = CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS * 0.7
        
        dx = abs(veiculo.posicao[0] - self.centro_x)
        dy = abs(veiculo.posicao[1] - self.centro_y)
        
        return dx < distancia_limite or dy < distancia_limite
    
    def _ordenar_veiculos_por_proximidade(self, veiculos: List[Veiculo], direcao: Direcao) -> List[Veiculo]:
        """Ordena veículos por proximidade ao cruzamento."""
        if direcao == Direcao.NORTE:
            # Quanto maior Y, mais próximo (vem de cima)
            return sorted(veiculos, key=lambda v: -v.posicao[1])
        elif direcao == Direcao.LESTE:
            # Quanto maior X, mais próximo (vem da esquerda)
            return sorted(veiculos, key=lambda v: -v.posicao[0])
        
        return veiculos
    
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
    
    def _criar_cruzamentos(self) -> None:
        """Cria a grade de cruzamentos."""
        for linha in range(self.linhas):
            for coluna in range(self.colunas):
                x = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                y = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
                
                id_cruzamento = (linha, coluna)
                self.cruzamentos[id_cruzamento] = Cruzamento(
                    (x, y), id_cruzamento, self.gerenciador_semaforos
                )
    
    def atualizar(self) -> None:
        """Atualiza toda a malha viária."""
        self.metricas['tempo_simulacao'] += 1
        
        # Gera novos veículos
        for cruzamento in self.cruzamentos.values():
            novos_veiculos = cruzamento.gerar_veiculos()
            self.veiculos.extend(novos_veiculos)
            self.metricas['veiculos_total'] += len(novos_veiculos)
        
        # Atualiza veículos em cada cruzamento
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
            'tempo_simulacao': self.metricas['tempo_simulacao'] / CONFIG.FPS
        }
    
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
    
    def _desenhar_ruas(self, tela: pygame.Surface) -> None:
        """Desenha as ruas da malha com mão única."""
        # Desenha ruas horizontais (Leste→Oeste)
        for linha in range(self.linhas):
            y = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            
            # Fundo da rua
            pygame.draw.rect(tela, CONFIG.CINZA_ESCURO,
                           (0, y - CONFIG.LARGURA_RUA // 2, 
                            CONFIG.LARGURA_TELA, CONFIG.LARGURA_RUA))
            
            # Desenha indicadores de direção
            self._desenhar_setas_horizontais(tela, y, Direcao.LESTE)
            
            # Bordas da rua (sem linha central)
            pygame.draw.line(tela, CONFIG.BRANCO,
                           (0, y - CONFIG.LARGURA_RUA // 2),
                           (CONFIG.LARGURA_TELA, y - CONFIG.LARGURA_RUA // 2), 2)
            pygame.draw.line(tela, CONFIG.BRANCO,
                           (0, y + CONFIG.LARGURA_RUA // 2),
                           (CONFIG.LARGURA_TELA, y + CONFIG.LARGURA_RUA // 2), 2)
        
        # Desenha ruas verticais (Norte→Sul)
        for coluna in range(self.colunas):
            x = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            
            # Fundo da rua
            pygame.draw.rect(tela, CONFIG.CINZA_ESCURO,
                           (x - CONFIG.LARGURA_RUA // 2, 0,
                            CONFIG.LARGURA_RUA, CONFIG.ALTURA_TELA))
            
            # Desenha indicadores de direção
            self._desenhar_setas_verticais(tela, x, Direcao.NORTE)
            
            # Bordas da rua (sem linha central)
            pygame.draw.line(tela, CONFIG.BRANCO,
                           (x - CONFIG.LARGURA_RUA // 2, 0),
                           (x - CONFIG.LARGURA_RUA // 2, CONFIG.ALTURA_TELA), 2)
            pygame.draw.line(tela, CONFIG.BRANCO,
                           (x + CONFIG.LARGURA_RUA // 2, 0),
                           (x + CONFIG.LARGURA_RUA // 2, CONFIG.ALTURA_TELA), 2)
    
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