"""
Módulo de cruzamento para a simulação de tráfego com múltiplos cruzamentos.
"""
import random
from typing import List, Dict, Tuple, Optional
import pygame
from configuracao import CONFIG, Direcao
from veiculo import Veiculo
from semaforo import Semaforo, ControladorSemaforo


class Cruzamento:
    """Representa um cruzamento de tráfego."""
    
    def __init__(self, posicao: Tuple[int, int], id_cruzamento: Tuple[int, int]):
        """
        Inicializa o cruzamento com uma lista vazia de veículos e semáforos.
        
        Args:
            posicao: Posição (x, y) do centro do cruzamento na tela
            id_cruzamento: Identificador (linha, coluna) do cruzamento na grade
        """
        self.id = id_cruzamento  # Identificador na grade (linha, coluna)
        self.posicao = posicao  # Posição (x, y) do centro do cruzamento
        self.veiculos: List[Veiculo] = []
        self.centro_x, self.centro_y = posicao
        
        # Inicializar o controlador de semáforos
        self.controlador_semaforo = ControladorSemaforo(id_cruzamento)
        self._configurar_semaforos()
        
        # Calcular os limites do cruzamento
        self.largura_rua = CONFIG.LARGURA_RUA
        self.limites = self._calcular_limites_cruzamento()
        
        # Guarda as posições iniciais de cada direção para este cruzamento
        self.posicoes_geracao = self._calcular_posicoes_geracao()
        
        # Estatísticas de tráfego para este cruzamento
        self.estatisticas = {
            "veiculos_gerados": 0,
            "veiculos_removidos": 0,
            "veiculos_parados_semaforo": 0
        }
    
    def _configurar_semaforos(self) -> None:
        """Configura os semáforos para cada direção no cruzamento com posicionamento intuitivo."""
        metade_rua = CONFIG.LARGURA_RUA // 2
        
        # Criar semáforos para as duas direções (Norte e Leste) com posições mais intuitivas
        semaforos = {
            # Semáforo para a direção NORTE (posicionado após o cruzamento, para quem vem de cima)
            # Agora vai ficar na via vertical, após o cruzamento
            Direcao.NORTE: Semaforo(
                (self.centro_x, self.centro_y + metade_rua + 15),
                Direcao.NORTE
            ),
            # Semáforo para a direção LESTE (posicionado após o cruzamento, para quem vem da esquerda)
            # Agora vai ficar na via horizontal, após o cruzamento
            Direcao.LESTE: Semaforo(
                (self.centro_x + metade_rua + 15, self.centro_y),
                Direcao.LESTE
            )
        }
        
        # Adicionar os semáforos ao controlador
        for direcao, semaforo in semaforos.items():
            self.controlador_semaforo.adicionar_semaforo(direcao, semaforo)
    
    def _calcular_limites_cruzamento(self) -> Dict[str, int]:
        """
        Calcula os limites do cruzamento.
        
        Returns:
            Dict[str, int]: Dicionário com os limites do cruzamento
        """
        metade_rua = CONFIG.LARGURA_RUA // 2
        
        limites = {
            'esquerda': self.centro_x - metade_rua,
            'direita': self.centro_x + metade_rua,
            'topo': self.centro_y - metade_rua,
            'base': self.centro_y + metade_rua
        }
        
        return limites
    
    def _calcular_posicoes_geracao(self) -> Dict[Direcao, Tuple[int, int]]:
        """
        Calcula as posições iniciais para cada direção neste cruzamento.
        
        Returns:
            Dict[Direcao, Tuple[int, int]]: Mapa de direções para posições iniciais
        """
        metade_rua = CONFIG.LARGURA_RUA // 2
        
        # Posições iniciais para veículos com base na direção e localização do cruzamento
        posicoes = {}
        
        # Somente cruzamentos na primeira linha (topo) geram veículos do Norte
        if self.id[0] == 0 and CONFIG.PONTOS_SPAWN['TOPO']:
            # Norte (de cima para baixo) - veículos começam acima do cruzamento
            posicoes[Direcao.NORTE] = (self.centro_x, 0)
        
        # Somente cruzamentos na primeira coluna (esquerda) geram veículos do Leste
        if self.id[1] == 0 and CONFIG.PONTOS_SPAWN['ESQUERDA']:
            # Leste (da esquerda para direita) - veículos começam à esquerda do cruzamento
            posicoes[Direcao.LESTE] = (0, self.centro_y)
        
        return posicoes
    
    def atualizar(self, veiculos_por_via: Dict[Tuple[int, int], Dict[Direcao, List[Veiculo]]]) -> None:
        """
        Atualiza todos os semáforos, veículos e gera novos.
        
        Args:
            veiculos_por_via: Dicionário de veículos organizados por via e direção
        """
        # Atualiza os semáforos
        self.controlador_semaforo.atualizar()
        
        # Gera veículos se este cruzamento for um ponto de spawn
        self._gerar_veiculos()
        
        # Obtém veículos por direção para verificação de colisão no cruzamento atual
        id_cruzamento = self.id
        veiculos_por_direcao = {
            Direcao.NORTE: [],
            Direcao.LESTE: []
        }
        
        # Coletar veículos deste cruzamento
        if id_cruzamento in veiculos_por_via:
            for direcao in [Direcao.NORTE, Direcao.LESTE]:
                if direcao in veiculos_por_via[id_cruzamento]:
                    veiculos_por_direcao[direcao] = veiculos_por_via[id_cruzamento][direcao]
        
        # Ordena veículos para cada direção
        # Norte: ordenado por Y (maior Y significa mais ao sul/mais próximo do cruzamento)
        veiculos_norte = sorted(veiculos_por_direcao[Direcao.NORTE], key=lambda v: v.posicao[1])
        # Leste: ordenado por X (maior X significa mais a leste/mais próximo do cruzamento)
        veiculos_leste = sorted(veiculos_por_direcao[Direcao.LESTE], key=lambda v: v.posicao[0])
        
        # Atualiza veículos existentes
        contagem_parados = 0
        
        # Atualiza veículos na direção NORTE (de cima para baixo)
        for veiculo in veiculos_norte:
            veiculos_frente = self._obter_veiculos_frente(veiculo, veiculos_norte)
            
            # Obter o semáforo relevante para este veículo
            semaforo = self.controlador_semaforo.obter_semaforo(Direcao.NORTE)
            
            # Atualizar veículo com informações do semáforo e veículos à frente
            veiculo.atualizar(semaforo, veiculos_frente, self.limites)
            
            # Conta veículos parados
            if veiculo.parado:
                contagem_parados += 1
        
        # Atualiza veículos na direção LESTE (da esquerda para direita)
        for veiculo in veiculos_leste:
            veiculos_frente = self._obter_veiculos_frente(veiculo, veiculos_leste)
            
            # Obter o semáforo relevante para este veículo
            semaforo = self.controlador_semaforo.obter_semaforo(Direcao.LESTE)
            
            # Atualizar veículo com informações do semáforo e veículos à frente
            veiculo.atualizar(semaforo, veiculos_frente, self.limites)
            
            # Conta veículos parados
            if veiculo.parado:
                contagem_parados += 1
        
        # Atualiza estatísticas
        self.estatisticas["veiculos_parados_semaforo"] = contagem_parados
        
        # Remove veículos inativos
        veiculos_ativos = [v for v in self.veiculos if v.ativo]
        veiculos_removidos = len(self.veiculos) - len(veiculos_ativos)
        self.estatisticas["veiculos_removidos"] += veiculos_removidos
        self.veiculos = veiculos_ativos

    def _obter_veiculos_frente(self, veiculo: Veiculo, veiculos_mesma_direcao: List[Veiculo]) -> List[Veiculo]:
        """
        Obtém os veículos à frente deste veículo na mesma direção.
        
        Args:
            veiculo: O veículo de referência
            veiculos_mesma_direcao: Lista de veículos na mesma direção
        
        Returns:
            List[Veiculo]: Lista de veículos à frente
        """
        veiculos_frente = []
        
        for outro_veiculo in veiculos_mesma_direcao:
            if outro_veiculo == veiculo:
                continue
                
            if veiculo.direcao == Direcao.NORTE:
                # Para veículos indo para baixo, à frente = Y maior
                if (outro_veiculo.posicao[1] > veiculo.posicao[1] and 
                    abs(outro_veiculo.posicao[0] - veiculo.posicao[0]) < veiculo.largura):
                    veiculos_frente.append(outro_veiculo)
            elif veiculo.direcao == Direcao.LESTE:
                # Para veículos indo para direita, à frente = X maior
                if (outro_veiculo.posicao[0] > veiculo.posicao[0] and 
                    abs(outro_veiculo.posicao[1] - veiculo.posicao[1]) < veiculo.altura):
                    veiculos_frente.append(outro_veiculo)
                    
        return veiculos_frente
    
    def _gerar_veiculos(self) -> None:
        """Gera aleatoriamente novos veículos nas bordas relevantes para este cruzamento."""
        for direcao, posicao in self.posicoes_geracao.items():
            if random.random() < CONFIG.TAXA_GERACAO_VEICULO:
                # Verifica se há espaço suficiente
                if self._tem_espaco_para_novo_veiculo(direcao, posicao):
                    novo_veiculo = Veiculo(direcao, posicao, self.id)
                    self.veiculos.append(novo_veiculo)
                    self.estatisticas["veiculos_gerados"] += 1
    
    def _tem_espaco_para_novo_veiculo(self, direcao: Direcao, posicao: Tuple[int, int]) -> bool:
        """
        Verifica se há espaço suficiente para um novo veículo.
        
        Args:
            direcao: Direção do veículo a ser gerado
            posicao: Posição do veículo a ser gerado
            
        Returns:
            bool: True se há espaço, False caso contrário
        """
        distancia_minima = CONFIG.DISTANCIA_MIN_VEICULO
        
        for veiculo in self.veiculos:
            if veiculo.direcao != direcao:
                continue
                
            # Calcula a distância entre o veículo existente e a posição proposta
            if direcao == Direcao.NORTE:
                if abs(veiculo.posicao[0] - posicao[0]) < 10:  # Mesma faixa
                    distancia = abs(veiculo.posicao[1] - posicao[1])
                    if distancia < distancia_minima:
                        return False
            else:  # LESTE
                if abs(veiculo.posicao[1] - posicao[1]) < 10:  # Mesma faixa
                    distancia = abs(veiculo.posicao[0] - posicao[0])
                    if distancia < distancia_minima:
                        return False
        
        return True
    
    def desenhar(self, tela: pygame.Surface) -> None:
        """
        Desenha o cruzamento, semáforos e todos os veículos.
        
        Args:
            tela: Superfície Pygame para desenhar
        """
        # Os cruzamentos NÃO desenham as ruas, isso é feito pela malha
        # Apenas desenham os semáforos e linhas de parada
        
        # Desenha linhas de parada para os semáforos
        self._desenhar_linhas_parada(tela)
        
        # Desenha os semáforos
        self.controlador_semaforo.desenhar(tela)
        
        # Desenha informações de debug, se habilitado
        if CONFIG.MODO_DEBUG:
            self._desenhar_info_debug(tela)
    
    def _desenhar_linhas_parada(self, tela: pygame.Surface) -> None:
        """
        Desenha as linhas de parada para os semáforos.
        
        Args:
            tela: Superfície Pygame para desenhar
        """
        # Linha de parada para o semáforo norte (horizontal)
        pygame.draw.rect(
            tela,
            CONFIG.BRANCO,
            pygame.Rect(
                self.centro_x - CONFIG.LARGURA_RUA // 2,
                self.centro_y - 30,  # Um pouco antes do cruzamento (vindo de cima)
                CONFIG.LARGURA_RUA,
                3
            )
        )
        
        # Linha de parada para o semáforo leste (vertical)
        pygame.draw.rect(
            tela,
            CONFIG.BRANCO,
            pygame.Rect(
                self.centro_x - 30,  # Um pouco antes do cruzamento (vindo da esquerda)
                self.centro_y - CONFIG.LARGURA_RUA // 2,
                3,
                CONFIG.LARGURA_RUA
            )
        )
    
    def _desenhar_info_debug(self, tela: pygame.Surface) -> None:
        """
        Desenha informações de depuração sobre o cruzamento.
        
        Args:
            tela: Superfície Pygame para desenhar
        """
        fonte = pygame.font.SysFont('Arial', 12)
        
        # Identificador do cruzamento
        texto_id = f"Cruzamento {self.id[0]},{self.id[1]}"
        superficie = fonte.render(texto_id, True, CONFIG.BRANCO)
        tela.blit(superficie, (self.centro_x - 40, self.centro_y - 40))
        
        # Estado dos semáforos
        estados_semaforo = {
            "N": self.controlador_semaforo.obter_semaforo(Direcao.NORTE).estado.name[0],
            "L": self.controlador_semaforo.obter_semaforo(Direcao.LESTE).estado.name[0]
        }
        
        for i, (direcao, estado) in enumerate(estados_semaforo.items()):
            texto = f"{direcao}: {estado}"
            superficie = fonte.render(texto, True, CONFIG.BRANCO)
            tela.blit(superficie, (self.centro_x - 40 + i * 30, self.centro_y - 25))


class MalhaViaria:
    """Gerencia a grade de cruzamentos da simulação."""
    
    def __init__(self, linhas: int = CONFIG.LINHAS_GRADE, colunas: int = CONFIG.COLUNAS_GRADE):
        """
        Inicializa a malha viária.
        
        Args:
            linhas: Número de linhas na grade de cruzamentos
            colunas: Número de colunas na grade de cruzamentos
        """
        self.linhas = linhas
        self.colunas = colunas
        self.cruzamentos: Dict[Tuple[int, int], Cruzamento] = {}
        self.veiculos: List[Veiculo] = []
        self.espacamento = CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
        
        # Posição inicial da malha
        self.pos_inicial_x = CONFIG.POSICAO_INICIAL_X
        self.pos_inicial_y = CONFIG.POSICAO_INICIAL_Y
        
        # Criar a grade de cruzamentos
        self._criar_grade_cruzamentos()
        
        # Estatísticas globais
        self.estatisticas = {
            "veiculos_totais": 0,
            "veiculos_ativos": 0,
            "veiculos_concluidos": 0,
            "media_tempo_viagem": 0
        }
    
    def _criar_grade_cruzamentos(self) -> None:
        """Cria a grade de cruzamentos na malha viária."""
        for linha in range(self.linhas):
            for coluna in range(self.colunas):
                # Calcular a posição do cruzamento
                pos_x = self.pos_inicial_x + coluna * self.espacamento
                pos_y = self.pos_inicial_y + linha * self.espacamento
                
                # Criar o cruzamento
                id_cruzamento = (linha, coluna)
                self.cruzamentos[id_cruzamento] = Cruzamento((pos_x, pos_y), id_cruzamento)
    
    def adicionar_veiculo(self, veiculo: Veiculo) -> None:
        """
        Adiciona um veículo à malha viária.
        
        Args:
            veiculo: O veículo a ser adicionado
        """
        self.veiculos.append(veiculo)
        self.estatisticas["veiculos_totais"] += 1
    
    def _organizar_veiculos_por_via(self) -> Dict[Tuple[int, int], Dict[Direcao, List[Veiculo]]]:
        """
        Organiza os veículos por via e direção.
        
        Returns:
            Dict: Mapa de vias para direções para listas de veículos
        """
        veiculos_por_via = {}
        
        for veiculo in self.veiculos:
            id_via = veiculo.id_via
            direcao = veiculo.direcao
            
            # Inicializa a estrutura se necessário
            if id_via not in veiculos_por_via:
                veiculos_por_via[id_via] = {}
            if direcao not in veiculos_por_via[id_via]:
                veiculos_por_via[id_via][direcao] = []
            
            # Adiciona o veículo
            veiculos_por_via[id_via][direcao].append(veiculo)
        
        return veiculos_por_via
    
    def atualizar(self) -> None:
        """Atualiza todos os cruzamentos e veículos na malha."""
        # Organiza os veículos por via e direção
        veiculos_por_via = self._organizar_veiculos_por_via()
        
        # Atualiza todos os cruzamentos
        for cruzamento in self.cruzamentos.values():
            cruzamento.atualizar(veiculos_por_via)
            
            # Coleta novos veículos gerados pelos cruzamentos
            for veiculo in cruzamento.veiculos:
                if veiculo not in self.veiculos:
                    self.veiculos.append(veiculo)
            
            # Limpa a lista de veículos do cruzamento após processá-los
            cruzamento.veiculos = []
        
        # Remover veículos inativos da malha
        veiculos_removidos = len(self.veiculos) - len([v for v in self.veiculos if v.ativo])
        self.estatisticas["veiculos_concluidos"] += veiculos_removidos
        self.veiculos = [v for v in self.veiculos if v.ativo]
        
        # Atualiza estatísticas
        self.estatisticas["veiculos_ativos"] = len(self.veiculos)
    
    def desenhar(self, tela: pygame.Surface) -> None:
        """
        Desenha toda a malha viária.
        
        Args:
            tela: Superfície Pygame para desenhar
        """
        # Desenha as ruas horizontais e verticais
        self._desenhar_ruas(tela)
        
        # Desenha todos os cruzamentos
        for cruzamento in self.cruzamentos.values():
            cruzamento.desenhar(tela)
        
        # Desenha todos os veículos
        for veiculo in self.veiculos:
            veiculo.desenhar(tela)
        
        # Desenha estatísticas globais
        if CONFIG.MODO_DEBUG:
            self._desenhar_estatisticas(tela)
    
    def _desenhar_ruas(self, tela: pygame.Surface) -> None:
        """
        Desenha as ruas horizontais e verticais da malha.
        
        Args:
            tela: Superfície Pygame para desenhar
        """
        largura_rua = CONFIG.LARGURA_RUA
        
        # Para cada linha de cruzamentos, desenha uma rua horizontal
        for linha in range(self.linhas):
            y = self.pos_inicial_y + linha * self.espacamento
            pygame.draw.rect(
                tela,
                CONFIG.CINZA,
                pygame.Rect(
                    0,
                    y - largura_rua // 2,
                    CONFIG.LARGURA_TELA,
                    largura_rua
                )
            )
        
        # Para cada coluna de cruzamentos, desenha uma rua vertical
        for coluna in range(self.colunas):
            x = self.pos_inicial_x + coluna * self.espacamento
            pygame.draw.rect(
                tela,
                CONFIG.CINZA,
                pygame.Rect(
                    x - largura_rua // 2,
                    0,
                    largura_rua,
                    CONFIG.ALTURA_TELA
                )
            )
    
    def _desenhar_estatisticas(self, tela: pygame.Surface) -> None:
        """
        Desenha estatísticas globais na tela.
        
        Args:
            tela: Superfície Pygame para desenhar
        """
        fonte = pygame.font.SysFont('Arial', 16)
        
        textos = [
            f"Veículos ativos: {self.estatisticas['veiculos_ativos']}",
            f"Veículos totais: {self.estatisticas['veiculos_totais']}",
            f"Veículos concluídos: {self.estatisticas['veiculos_concluidos']}"
        ]
        
        for i, texto in enumerate(textos):
            superficie = fonte.render(texto, True, CONFIG.BRANCO)
            tela.blit(superficie, (10, 10 + i * 20))