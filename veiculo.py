"""
Módulo de veículos para a simulação de malha viária com múltiplos cruzamentos.
Extensões:
- Duas faixas por via (mão única)
- Troca de faixa com checagens de segurança
- Conversão (virar 90°) no cruzamento
- Correção: base_x/base_y sempre definidos para evitar None em cálculos laterais
"""
import random
import math
from typing import Tuple, Optional, List
import pygame
from configuracao import CONFIG, Direcao, EstadoSemaforo
from semaforo import Semaforo


class Veiculo:
    """Representa um veículo na simulação com física e comportamento realista - MÃO ÚNICA."""

    # Contador estático para IDs únicos
    _contador_id = 0

    def __init__(
        self,
        direcao: Direcao,
        posicao: Tuple[float, float],
        id_cruzamento_origem: Tuple[int, int],
        faixa: int = 0
    ):
        """
        Inicializa um veículo.

        Args:
            direcao: Direção do veículo (apenas NORTE ou LESTE em mão única)
            posicao: Posição inicial (x, y) do veículo
            id_cruzamento_origem: ID do cruzamento onde o veículo foi gerado (linha, coluna)
            faixa: índice da faixa (0..NUM_FAIXAS_POR_SENTIDO-1)
        """
        # Valida direção - apenas direções permitidas
        if direcao not in CONFIG.DIRECOES_PERMITIDAS:
            raise ValueError(f"Direção {direcao} não permitida. Use apenas {CONFIG.DIRECOES_PERMITIDAS}")

        # ID único para o veículo
        Veiculo._contador_id += 1
        self.id = Veiculo._contador_id

        # Propriedades básicas
        self.direcao = direcao
        self.posicao = list(posicao)
        self.posicao_inicial = list(posicao)
        self.id_cruzamento_origem = id_cruzamento_origem
        self.id_cruzamento_atual = id_cruzamento_origem
        self.cor = random.choice(CONFIG.CORES_VEICULO)
        self.ativo = True

        # Dimensões
        self.largura = CONFIG.LARGURA_VEICULO
        self.altura = CONFIG.ALTURA_VEICULO

        # Física e movimento
        self.velocidade = 0.0
        self.velocidade_desejada = CONFIG.VELOCIDADE_VEICULO
        self.aceleracao_atual = 0.0

        # Estados
        self.parado = True
        self.no_cruzamento = False
        self.passou_semaforo = False
        self.aguardando_semaforo = False
        self.em_desaceleracao = False

        # Controle de semáforo
        self.semaforo_proximo = None
        self.ultimo_semaforo_processado = None
        self.distancia_semaforo = float('inf')
        self.pode_passar_amarelo = False

        # Controle de colisão
        self.veiculo_frente: Optional['Veiculo'] = None
        self.distancia_veiculo_frente = float('inf')

        # Métricas
        self.tempo_viagem = 0
        self.tempo_parado = 0
        self.paradas_totais = 0
        self.distancia_percorrida = 0.0

        # ===== Faixas / Conversão =====
        self.faixa = max(0, min(faixa, CONFIG.NUM_FAIXAS_POR_SENTIDO - 1))
        self.base_x: Optional[float] = None  # eixo-base lateral para NORTE (vertical)
        self.base_y: Optional[float] = None  # eixo-base lateral para LESTE (horizontal)

        # probabilidade de virar (converter) neste ciclo (decisão tomada ao criar)
        self.vai_virar: bool = random.random() < CONFIG.PROB_VIRAR
        self.ja_virou: bool = False

        # Inicializa eixos-base conforme cruzamento de origem (EVITA None)
        self._reancorar_eixo_base(self.id_cruzamento_origem)
        # Garante posição ancorada na faixa (lateral)
        self._ancorar_na_faixa()

        # Retângulo de colisão
        self._atualizar_rect()

    # -------------------- Geometria de faixa / âncoras --------------------

    def _offset_lateral(self, faixa_idx: Optional[int] = None) -> float:
        """Centro da faixa i dentro da rua (duas faixas por sentido)."""
        i = self.faixa if faixa_idx is None else faixa_idx
        return -CONFIG.LARGURA_RUA / 2 + (i + 0.5) * CONFIG.LARGURA_FAIXA

    def _centro_rua_para_cruzamento(self, cruz_id: Tuple[int, int]) -> Tuple[float, float]:
        """Retorna (x_centro_coluna, y_centro_linha) para o cruzamento id."""
        linha, coluna = cruz_id
        cx = CONFIG.POSICAO_INICIAL_X + coluna * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
        cy = CONFIG.POSICAO_INICIAL_Y + linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
        return cx, cy

    def _reancorar_eixo_base(self, cruz_id: Tuple[int, int]) -> None:
        """
        Define/atualiza base_x/base_y conforme a direção e o cruzamento atual.
        Isso evita None em cálculos laterais (usado em troca de faixa/curvas).
        """
        cx, cy = self._centro_rua_para_cruzamento(cruz_id)
        if self.direcao == Direcao.NORTE:
            # Via vertical usa base_x (x fixo + offset da faixa)
            self.base_x = cx
            if self.base_y is None:
                # Não é usado na vertical, mas evita None futuro
                self.base_y = cy
        elif self.direcao == Direcao.LESTE:
            # Via horizontal usa base_y (y fixo + offset da faixa)
            self.base_y = cy
            if self.base_x is None:
                self.base_x = cx

    def _ancorar_na_faixa(self) -> None:
        """Move o veículo para o centro da faixa atual no eixo lateral."""
        off = self._offset_lateral(self.faixa)
        if self.direcao == Direcao.NORTE:
            # Corrige X de acordo com base_x + offset da faixa
            self.posicao[0] = (self.base_x if self.base_x is not None else self.posicao[0]) + off
        elif self.direcao == Direcao.LESTE:
            # Corrige Y de acordo com base_y + offset da faixa
            self.posicao[1] = (self.base_y if self.base_y is not None else self.posicao[1]) + off

    def definir_faixa(self, nova_faixa: int) -> None:
        """Altera a faixa e reancora lateralmente."""
        self.faixa = max(0, min(nova_faixa, CONFIG.NUM_FAIXAS_POR_SENTIDO - 1))
        self._ancorar_na_faixa()

    # ---------------------------- Fluxo principal ----------------------------

    def _atualizar_rect(self) -> None:
        """Atualiza o retângulo de colisão do veículo."""
        if self.direcao == Direcao.NORTE:
            # Veículo vertical (Norte→Sul)
            self.rect = pygame.Rect(
                self.posicao[0] - self.largura // 2,
                self.posicao[1] - self.altura // 2,
                self.largura,
                self.altura
            )
        elif self.direcao == Direcao.LESTE:
            # Veículo horizontal (Leste→Oeste)
            self.rect = pygame.Rect(
                self.posicao[0] - self.altura // 2,
                self.posicao[1] - self.largura // 2,
                self.altura,
                self.largura
            )

    def resetar_controle_semaforo(self, novo_cruzamento_id: Optional[Tuple[int, int]] = None) -> None:
        """
        Reseta o controle de semáforo quando o veículo muda de cruzamento.
        Também reancora o eixo-base lateral para EVITAR None em cálculos de faixa.
        """
        if novo_cruzamento_id and novo_cruzamento_id != self.id_cruzamento_atual:
            self.id_cruzamento_atual = novo_cruzamento_id

        # Reset flags de semáforo
        self.passou_semaforo = False
        self.aguardando_semaforo = False
        self.pode_passar_amarelo = False
        self.semaforo_proximo = None
        self.distancia_semaforo = float('inf')

        # MUITO IMPORTANTE: reancorar eixo-base conforme direção + cruzamento atual
        self._reancorar_eixo_base(self.id_cruzamento_atual)
        # Mantém alinhamento lateral à faixa atual
        self._ancorar_na_faixa()

    def verificar_colisao_futura(self, todos_veiculos: List['Veiculo']) -> bool:
        """
        Verifica se haverá colisão se o veículo continuar se movendo.
        """
        # Calcula posição futura
        dx, dy = 0, 0
        if self.direcao == Direcao.NORTE:
            dy = self.velocidade + CONFIG.DISTANCIA_MIN_VEICULO / 2
        elif self.direcao == Direcao.LESTE:
            dx = self.velocidade + CONFIG.DISTANCIA_MIN_VEICULO / 2

        posicao_futura = [self.posicao[0] + dx, self.posicao[1] + dy]

        # Cria retângulo futuro
        if self.direcao == Direcao.NORTE:
            rect_futuro = pygame.Rect(
                posicao_futura[0] - self.largura // 2,
                posicao_futura[1] - self.altura // 2,
                self.largura,
                self.altura
            )
        else:
            rect_futuro = pygame.Rect(
                posicao_futura[0] - self.altura // 2,
                posicao_futura[1] - self.largura // 2,
                self.altura,
                self.largura
            )

        # Verifica colisão com outros veículos
        for outro in todos_veiculos:
            if outro.id == self.id or not outro.ativo:
                continue

            # Só verifica veículos na mesma via E mesma faixa
            if self.direcao != outro.direcao or self.faixa != outro.faixa:
                continue

            # Expande o retângulo do outro veículo para margem de segurança
            rect_outro_expandido = outro.rect.inflate(10, 10)

            if rect_futuro.colliderect(rect_outro_expandido):
                return True

        return False

    def processar_todos_veiculos(self, todos_veiculos: List['Veiculo']) -> None:
        """
        Processa interação com todos os veículos, não apenas os do cruzamento atual.
        Usa mesma FAIXA para car-following.
        """
        veiculo_mais_proximo = None
        distancia_minima = float('inf')

        for outro in todos_veiculos:
            if outro.id == self.id or not outro.ativo:
                continue

            # Verifica se estão na MESMA direção e FAIXA
            if self.direcao != outro.direcao or self.faixa != outro.faixa:
                continue

            # Verifica se o outro está à frente
            if self.direcao == Direcao.NORTE:
                if outro.posicao[1] > self.posicao[1]:  # Outro está à frente (mais para baixo)
                    distancia = outro.posicao[1] - self.posicao[1]
                    if distancia < distancia_minima:
                        distancia_minima = distancia
                        veiculo_mais_proximo = outro
            elif self.direcao == Direcao.LESTE:
                if outro.posicao[0] > self.posicao[0]:  # Outro está à frente (mais para direita)
                    distancia = outro.posicao[0] - self.posicao[0]
                    if distancia < distancia_minima:
                        distancia_minima = distancia
                        veiculo_mais_proximo = outro

        # Processa o veículo mais próximo à frente
        if veiculo_mais_proximo:
            self.veiculo_frente = veiculo_mais_proximo
            self.distancia_veiculo_frente = distancia_minima
            self.processar_veiculo_frente(veiculo_mais_proximo)
        else:
            self.veiculo_frente = None
            self.distancia_veiculo_frente = float('inf')
            # Se não há veículo à frente e não está aguardando semáforo, acelera
            if not self.aguardando_semaforo:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO

    def atualizar(self, dt: float = 1.0, todos_veiculos: List['Veiculo'] = None, malha=None) -> None:
        """
        Atualiza o estado do veículo.

        Args:
            dt: Delta time para cálculos de física
            todos_veiculos: Lista de todos os veículos para verificação de colisão
            malha: MalhaViaria para aplicar o fator de 'caos' (limite local de velocidade)
        """
        # métricas
        self.tempo_viagem += dt
        if self.velocidade < 0.1:
            self.tempo_parado += dt
            if not self.parado:
                self.paradas_totais += 1
            self.parado = True
        else:
            self.parado = False

        # TENTATIVA DE TROCA DE FAIXA (antes do passo de movimento), se aplicável
        if todos_veiculos:
            self.tentar_trocar_faixa(todos_veiculos)

        # aplica aceleração
        self.velocidade += self.aceleracao_atual * dt

        # limite de velocidade com fator local (CAOS)
        fator = malha.obter_fator_caos(self) if malha is not None else 1.0
        vmax_local = CONFIG.VELOCIDADE_MAX_VEICULO * fator
        self.velocidade = max(CONFIG.VELOCIDADE_MIN_VEICULO, min(vmax_local, self.velocidade))

        # colisão futura
        if todos_veiculos and self.velocidade > 0:
            if self.verificar_colisao_futura(todos_veiculos):
                self.velocidade = 0
                self.aceleracao_atual = 0
                self._atualizar_rect()
                return

        # movimento
        dx, dy = 0, 0
        if self.direcao == Direcao.NORTE:
            dy = self.velocidade
        elif self.direcao == Direcao.LESTE:
            dx = self.velocidade

        self.posicao[0] += dx
        self.posicao[1] += dy
        self.distancia_percorrida += math.sqrt(dx ** 2 + dy ** 2)

        self._atualizar_rect()

        # saída da tela
        margem = 100
        if (self.posicao[0] < -margem or
                self.posicao[0] > CONFIG.LARGURA_TELA + margem or
                self.posicao[1] < -margem or
                self.posicao[1] > CONFIG.ALTURA_TELA + margem):
            self.ativo = False

    # ------------------------- Reação a semáforos / líderes -------------------------

    def processar_semaforo(self, semaforo: Semaforo, posicao_parada: Tuple[float, float]) -> None:
        """
        Processa a reação do veículo ao semáforo.
        """
        if not semaforo:
            # Sem semáforo, acelera normalmente (se não houver veículo à frente)
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        # Verifica se é um novo semáforo
        if self.ultimo_semaforo_processado != semaforo:
            self.passou_semaforo = False
            self.ultimo_semaforo_processado = semaforo
            self.pode_passar_amarelo = False

        # Se já passou deste semáforo específico, ignora
        if self.passou_semaforo:
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        # Calcula distância até a linha de parada
        self.distancia_semaforo = self._calcular_distancia_ate_ponto(posicao_parada)

        # Se já passou da linha de parada, marca como passado
        if self._passou_da_linha(posicao_parada):
            self.passou_semaforo = True
            self.aguardando_semaforo = False
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        # Lógica baseada no estado do semáforo
        if semaforo.estado == EstadoSemaforo.VERDE:
            # Semáforo verde: acelera normalmente (se não houver veículo à frente)
            self.aguardando_semaforo = False
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO

        elif semaforo.estado == EstadoSemaforo.AMARELO:
            # Semáforo amarelo: decide se passa ou freia
            if self.pode_passar_amarelo:
                # Já tinha decidido passar, mantém
                self.aceleracao_atual = 0
            else:
                # Avalia se pode passar
                tempo_ate_linha = self.distancia_semaforo / max(self.velocidade, 0.1)

                # Só passa se estiver muito próximo E em velocidade suficiente
                if (tempo_ate_linha < 1.0 and
                    self.velocidade > CONFIG.VELOCIDADE_VEICULO * 0.7 and
                    self.distancia_semaforo < CONFIG.DISTANCIA_PARADA_SEMAFORO * 3):
                    # Perto demais para parar com segurança
                    self.pode_passar_amarelo = True
                    self.aceleracao_atual = 0
                else:
                    # Tem tempo para parar com segurança
                    self._aplicar_frenagem_para_parada(self.distancia_semaforo)
                    self.aguardando_semaforo = True

        elif semaforo.estado == EstadoSemaforo.VERMELHO:
            # Semáforo vermelho: SEMPRE para
            self.aguardando_semaforo = True
            self.pode_passar_amarelo = False

            if self.distancia_semaforo <= CONFIG.DISTANCIA_PARADA_SEMAFORO:
                # Muito próximo da linha, para imediatamente
                self.velocidade = 0.0
                self.aceleracao_atual = 0.0
            else:
                # Aplica frenagem para parar antes da linha
                self._aplicar_frenagem_para_parada(self.distancia_semaforo)

    def processar_veiculo_frente(self, veiculo_frente: 'Veiculo') -> None:
        """
        Processa a reação a um veículo à frente (mesma faixa).
        """
        if not veiculo_frente:
            return

        distancia = self._calcular_distancia_para_veiculo(veiculo_frente)

        # Força parada se muito próximo
        if distancia < CONFIG.DISTANCIA_MIN_VEICULO:
            self.velocidade = 0
            self.aceleracao_atual = 0
            return

        if distancia < CONFIG.DISTANCIA_REACAO:
            # Calcula velocidade segura baseada na distância
            velocidade_segura = self._calcular_velocidade_segura(distancia, veiculo_frente.velocidade)

            if self.velocidade > velocidade_segura:
                # Precisa frear
                if distancia < CONFIG.DISTANCIA_MIN_VEICULO * 1.5:
                    self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
                else:
                    self.aceleracao_atual = -CONFIG.DESACELERACAO_VEICULO
            elif self.velocidade < velocidade_segura * 0.9:
                # Pode acelerar um pouco
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO * 0.3
            else:
                # Manter velocidade
                self.aceleracao_atual = 0
        else:
            # Distância segura, pode acelerar se não estiver aguardando semáforo
            if not self.aguardando_semaforo:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO

    def _calcular_distancia_ate_ponto(self, ponto: Tuple[float, float]) -> float:
        """Calcula a distância até um ponto específico - MÃO ÚNICA."""
        if self.direcao == Direcao.NORTE:
            # Norte→Sul: distância é diferença em Y (positiva)
            return max(0, ponto[1] - self.posicao[1])
        elif self.direcao == Direcao.LESTE:
            # Leste→Oeste: distância é diferença em X (positiva)
            return max(0, ponto[0] - self.posicao[0])
        return float('inf')

    def _passou_da_linha(self, ponto: Tuple[float, float]) -> bool:
        """Verifica se o veículo já passou de um ponto - MÃO ÚNICA."""
        margem = 10
        if self.direcao == Direcao.NORTE:
            # Norte→Sul: passou se Y atual > Y do ponto
            return self.posicao[1] > ponto[1] + margem
        elif self.direcao == Direcao.LESTE:
            # Leste→Oeste: passou se X atual > X do ponto
            return self.posicao[0] > ponto[0] + margem
        return False

    def _calcular_distancia_para_veiculo(self, outro: 'Veiculo') -> float:
        """Calcula a distância até outro veículo (mesma direção e mesma faixa)."""
        if self.direcao != outro.direcao or self.faixa != outro.faixa:
            return float('inf')

        # Calcula distância centro a centro somente no eixo longitudinal
        dx = outro.posicao[0] - self.posicao[0]
        dy = outro.posicao[1] - self.posicao[1]

        if self.direcao == Direcao.NORTE:
            if dy > 0:  # Outro está à frente
                return max(0, dy - (self.altura + outro.altura) / 2)
        elif self.direcao == Direcao.LESTE:
            if dx > 0:  # Outro está à frente
                return max(0, dx - (self.altura + outro.altura) / 2)

        return float('inf')

    def _calcular_velocidade_segura(self, distancia: float, velocidade_lider: float) -> float:
        """Calcula a velocidade segura baseada na distância e velocidade do veículo à frente."""
        if distancia < CONFIG.DISTANCIA_MIN_VEICULO:
            return 0

        # Modelo de car-following simplificado
        tempo_reacao = 1.0  # 1 segundo
        distancia_segura = CONFIG.DISTANCIA_SEGURANCA + velocidade_lider * tempo_reacao

        if distancia < distancia_segura:
            fator = distancia / distancia_segura
            return velocidade_lider * fator

        return CONFIG.VELOCIDADE_VEICULO

    def _aplicar_frenagem_para_parada(self, distancia: float) -> None:
        """Aplica frenagem suave para parar em uma distância específica."""
        if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO:
            # Muito próximo, frenagem de emergência
            self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
            self.velocidade_desejada = 0
            # Força parada completa se muito próximo
            if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO / 2:
                self.velocidade = 0.0
        else:
            # Cálculo de desaceleração necessária: v² = v₀² + 2*a*d
            if self.velocidade > 0.1:
                desaceleracao_necessaria = (self.velocidade ** 2) / (2 * distancia)
                self.aceleracao_atual = -min(desaceleracao_necessaria, CONFIG.DESACELERACAO_VEICULO)
            else:
                self.aceleracao_atual = 0

    # ---------------------------- Troca de faixa ----------------------------

    def tentar_trocar_faixa(self, todos_veiculos: List['Veiculo']) -> None:
        """
        Tenta mudar de faixa com uma probabilidade pequena e sob condições seguras.
        """
        # Não tenta se só há uma faixa
        if CONFIG.NUM_FAIXAS_POR_SENTIDO < 2:
            return

        # Evita trocar dentro do miolo de cruzamentos (heurística simples):
        # como não temos referência direta, apenas evite quando velocidade é muito baixa
        if self.velocidade < 0.05:
            return

        prob = getattr(CONFIG, "PROB_TROCA_FAIXA", 0.02)
        if random.random() > prob:
            return

        # Escolhe faixa alvo (vizinha)
        candidatos = []
        if self.faixa - 1 >= 0:
            candidatos.append(self.faixa - 1)
        if self.faixa + 1 < CONFIG.NUM_FAIXAS_POR_SENTIDO:
            candidatos.append(self.faixa + 1)
        if not candidatos:
            return

        random.shuffle(candidatos)
        for nf in candidatos:
            if self._pode_mudar_para_faixa(nf, todos_veiculos):
                self.definir_faixa(nf)
                break

    def _pode_mudar_para_faixa(self, faixa_alvo: int, todos_veiculos: List['Veiculo']) -> bool:
        """
        Verifica se há espaço na faixa alvo (janela de segurança à frente e atrás).
        Usa base_x/base_y + offset da faixa alvo para calcular o eixo lateral.
        """
        # Garante eixos-base definidos
        if self.base_x is None or self.base_y is None:
            self._reancorar_eixo_base(self.id_cruzamento_atual)

        alvo_off = -CONFIG.LARGURA_RUA / 2 + (faixa_alvo + 0.5) * CONFIG.LARGURA_FAIXA
        if self.direcao == Direcao.NORTE:
            alvo_lateral = self.base_x + alvo_off
            # veículo ocupa [x - largura/2, x + largura/2]
            janela_lateral = (alvo_lateral - self.largura, alvo_lateral + self.largura)
            eixo_longo = 1  # y
        else:
            alvo_lateral = self.base_y + alvo_off
            janela_lateral = (alvo_lateral - self.largura, alvo_lateral + self.largura)
            eixo_longo = 0  # x

        # Distâncias mínimas à frente/atrás
        dist_a_frente = CONFIG.DISTANCIA_MIN_VEICULO * 1.2
        dist_atras = CONFIG.DISTANCIA_MIN_VEICULO * 0.8

        # Verifica conflitos com veículos na faixa alvo
        for outro in todos_veiculos:
            if not outro.ativo or outro.id == self.id:
                continue
            if outro.direcao != self.direcao:
                continue
            if outro.faixa != faixa_alvo:
                continue

            # Compatibilidade lateral (tolerância pequena)
            if self.direcao == Direcao.NORTE:
                # comparar X
                if not (janela_lateral[0] <= outro.posicao[0] <= janela_lateral[1]):
                    continue
                delta = outro.posicao[1] - self.posicao[1]
            else:
                # comparar Y
                if not (janela_lateral[0] <= outro.posicao[1] <= janela_lateral[1]):
                    continue
                delta = outro.posicao[0] - self.posicao[0]

            # Janela de segurança
            if -dist_atras < delta < dist_a_frente:
                return False

        return True

    # ---------------------------- Desenho ----------------------------

    def desenhar(self, tela: pygame.Surface) -> None:
        """Desenha o veículo na tela com visual."""
        # Cria superfície para o veículo
        if self.direcao == Direcao.NORTE:
            superficie = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
        else:  # Direcao.LESTE
            superficie = pygame.Surface((self.altura, self.largura), pygame.SRCALPHA)

        # Desenha o corpo do veículo
        pygame.draw.rect(superficie, self.cor, superficie.get_rect(), border_radius=4)

        # Adiciona detalhes (janelas)
        cor_janela = (200, 220, 255, 180)
        if self.direcao == Direcao.NORTE:
            # Janela frontal (parte de baixo - direção do movimento)
            pygame.draw.rect(
                superficie, cor_janela,
                (3, self.altura * 0.7, self.largura - 6, self.altura * 0.25),
                border_radius=2
            )
            # Janela traseira (parte de cima)
            pygame.draw.rect(
                superficie, cor_janela,
                (3, 3, self.largura - 6, self.altura * 0.3),
                border_radius=2
            )
        else:  # Direcao.LESTE
            # Janela frontal (parte direita - direção do movimento)
            pygame.draw.rect(
                superficie, cor_janela,
                (self.altura * 0.7, 3, self.altura * 0.25, self.largura - 6),
                border_radius=2
            )
            # Janela traseira (parte esquerda)
            pygame.draw.rect(
                superficie, cor_janela,
                (3, 3, self.altura * 0.3, self.largura - 6),
                border_radius=2
            )

        # Adiciona luzes de freio se estiver freando
        if self.aceleracao_atual < -0.1:
            cor_freio = (255, 100, 100)
            if self.direcao == Direcao.NORTE:
                # Luzes na parte de cima (traseira)
                pygame.draw.rect(superficie, cor_freio, (2, 1, 6, 3))
                pygame.draw.rect(superficie, cor_freio, (self.largura - 8, 1, 6, 3))
            elif self.direcao == Direcao.LESTE:
                # Luzes na parte esquerda (traseira)
                pygame.draw.rect(superficie, cor_freio, (1, 2, 3, 6))
                pygame.draw.rect(superficie, cor_freio, (1, self.largura - 8, 3, 6))

        # Adiciona faróis
        cor_farol = (255, 255, 200, 150)
        if self.direcao == Direcao.NORTE:
            # Faróis na frente (parte de baixo)
            pygame.draw.circle(superficie, cor_farol, (8, self.altura - 5), 3)
            pygame.draw.circle(superficie, cor_farol, (self.largura - 8, self.altura - 5), 3)
        elif self.direcao == Direcao.LESTE:
            # Faróis na frente (parte direita)
            pygame.draw.circle(superficie, cor_farol, (self.altura - 5, 8), 3)
            pygame.draw.circle(superficie, cor_farol, (self.altura - 5, self.largura - 8), 3)

        # Desenha na tela
        rect = superficie.get_rect(center=(int(self.posicao[0]), int(self.posicao[1])))
        tela.blit(superficie, rect)

        # Debug info
        if CONFIG.MOSTRAR_INFO_VEICULO:
            fonte = pygame.font.SysFont('Arial', 10)
            aguardando = ""
            if self.aguardando_semaforo:
                aguardando = "🔴"
            elif self.veiculo_frente and self.distancia_veiculo_frente < CONFIG.DISTANCIA_REACAO:
                aguardando = "🚗"

            info = f"V:{self.velocidade:.1f} ID:{self.id} F:{self.faixa}{' ↪' if self.vai_virar and not self.ja_virou else ''} {aguardando}"
            superficie_texto = fonte.render(info, True, CONFIG.BRANCO)
            tela.blit(superficie_texto, (self.posicao[0] - 28, self.posicao[1] - 28))
