"""
Módulo de veículos para a simulação de malha viária com múltiplos cruzamentos.
Sistema com vias de mão única: Horizontal (Leste→Oeste) e Vertical (Norte→Sul)
"""
import random
import math
from typing import Tuple, Optional, List
import pygame
from configuracao import CONFIG, Direcao, EstadoSemaforo
from semaforo import Semaforo


class Veiculo:
    """Representa um veículo na simulação com física e comportamento realista - MÃO ÚNICA."""

    _contador_id = 0

    def __init__(self, direcao: Direcao, posicao: Tuple[float, float], id_cruzamento_origem: Tuple[int, int]):
        if direcao not in CONFIG.DIRECOES_PERMITIDAS:
            raise ValueError(f"Direção {direcao} não permitida. Use apenas {CONFIG.DIRECOES_PERMITIDAS}")

        Veiculo._contador_id += 1
        self.id = Veiculo._contador_id

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

        # Física
        self.velocidade = 0.0
        self.velocidade_desejada = CONFIG.VELOCIDADE_VEICULO
        self.aceleracao_atual = 0.0

        # Estados
        self.parado = True
        self.no_cruzamento = False
        self.passou_semaforo = False
        self.aguardando_semaforo = False
        self.em_desaceleracao = False

        # Semáforo
        self.semaforo_proximo = None
        self.ultimo_semaforo_processado = None
        self.distancia_semaforo = float('inf')
        self.pode_passar_amarelo = False

        # Car-following
        self.veiculo_frente = None
        self.distancia_veiculo_frente = float('inf')

        # Lanes
        self.indice_faixa: int = getattr(self, "indice_faixa", 0)
        self._leader_cache = None
        self._follower_cache = None
        self._lane_cooldown_frames = 0  # cooldown MOBIL-lite

        # Métricas
        self.tempo_viagem = 0
        self.tempo_parado = 0
        self.paradas_totais = 0
        self.distancia_percorrida = 0.0

        self._atualizar_rect()

    # ------------- helpers de faixa -------------
    def _garantir_campos_lane(self):
        if not hasattr(self, "indice_faixa"):
            self.indice_faixa = 0
        self.indice_faixa = max(0, min(self.indice_faixa, CONFIG.FAIXAS_POR_VIA - 1))

    def _via_idx(self) -> int:
        if self.direcao == Direcao.LESTE:
            idx = round((self.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_VERTICAL)
            return max(0, min(idx, CONFIG.LINHAS_GRADE - 1))
        else:
            idx = round((self.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_HORIZONTAL)
            return max(0, min(idx, CONFIG.COLUNAS_GRADE - 1))

    def _lane_center_coord(self, direcao: Direcao, faixa: int) -> float:
        faixa = max(0, min(faixa, CONFIG.FAIXAS_POR_VIA - 1))
        if direcao == Direcao.LESTE:
            y_road = CONFIG.POSICAO_INICIAL_Y + self._via_idx() * CONFIG.ESPACAMENTO_VERTICAL
            return y_road - CONFIG.LARGURA_RUA / 2 + (faixa + 0.5) * CONFIG.LARGURA_FAIXA
        else:
            x_road = CONFIG.POSICAO_INICIAL_X + self._via_idx() * CONFIG.ESPACAMENTO_HORIZONTAL
            return x_road - CONFIG.LARGURA_RUA / 2 + (faixa + 0.5) * CONFIG.LARGURA_FAIXA

    def _mesma_via_mesma_faixa(self, outro: 'Veiculo', faixa: int) -> bool:
        if self.direcao != outro.direcao:
            return False
        if getattr(outro, "indice_faixa", 0) != faixa:
            return False
        return self._via_idx() == outro._via_idx()

    # ------------- retângulo de colisão -------------
    def _atualizar_rect(self) -> None:
        if self.direcao == Direcao.NORTE:
            self.rect = pygame.Rect(
                self.posicao[0] - self.largura // 2,
                self.posicao[1] - self.altura // 2,
                self.largura,
                self.altura
            )
        else:
            self.rect = pygame.Rect(
                self.posicao[0] - self.altura // 2,
                self.posicao[1] - self.largura // 2,
                self.altura,
                self.largura
            )

    def resetar_controle_semaforo(self, novo_cruzamento_id: Optional[Tuple[int, int]] = None) -> None:
        if novo_cruzamento_id and novo_cruzamento_id != self.id_cruzamento_atual:
            self.id_cruzamento_atual = novo_cruzamento_id
            self.passou_semaforo = False
            self.aguardando_semaforo = False
            self.pode_passar_amarelo = False
            self.semaforo_proximo = None
            self.distancia_semaforo = float('inf')

    # ------------- colisão futura -------------
    def verificar_colisao_futura(self, todos_veiculos: List['Veiculo']) -> bool:
        # OTIMIZAÇÃO: Checa apenas o veículo da frente já identificado (O(1))
        # em vez de iterar sobre todos os veículos (O(N))
        if not self.veiculo_frente or not self.veiculo_frente.ativo:
            return False

        dx, dy = 0, 0
        if self.direcao == Direcao.NORTE:
            dy = self.velocidade + CONFIG.DISTANCIA_MIN_VEICULO / 2
        else:
            dx = self.velocidade + CONFIG.DISTANCIA_MIN_VEICULO / 2
        
        posicao_futura = [self.posicao[0] + dx, self.posicao[1] + dy]

        if self.direcao == Direcao.NORTE:
            rect_futuro = pygame.Rect(
                posicao_futura[0] - self.largura // 2,
                posicao_futura[1] - self.altura // 2,
                self.largura, self.altura
            )
        else:
            rect_futuro = pygame.Rect(
                posicao_futura[0] - self.altura // 2,
                posicao_futura[1] - self.largura // 2,
                self.altura, self.largura
            )

        rect_outro_expandido = self.veiculo_frente.rect.inflate(10, 10)
        return rect_futuro.colliderect(rect_outro_expandido)

    # ------------- car-following + MOBIL-lite -------------
    def processar_todos_veiculos(self, todos_veiculos: List['Veiculo']) -> None:
        """
        Usa caches (líder/seguidor por faixa) quando presentes (O(1));
        fallback O(N) apenas se necessário. Aplica decisão de mudança de faixa
        (MOBIL-lite com gap acceptance) apenas quando há ganho de velocidade.
        """
        self._garantir_campos_lane()

        leader = getattr(self, "_leader_cache", None)
        if leader is not None and leader.ativo and self._mesma_via_mesma_faixa(leader, self.indice_faixa):
            self.veiculo_frente = leader
            self.distancia_veiculo_frente = self._calcular_distancia_para_veiculo(leader)
            self.processar_veiculo_frente(leader)
        else:
            # fallback simples (mesma via e mesma faixa)
            veiculo_mais_prox = None
            distancia_min = float('inf')
            for outro in todos_veiculos:
                if outro.id == self.id or not outro.ativo:
                    continue
                if self.direcao != outro.direcao or not self._mesma_via_mesma_faixa(outro, self.indice_faixa):
                    continue
                if self.direcao == Direcao.NORTE and outro.posicao[1] > self.posicao[1]:
                    d = outro.posicao[1] - self.posicao[1]
                elif self.direcao == Direcao.LESTE and outro.posicao[0] > self.posicao[0]:
                    d = outro.posicao[0] - self.posicao[0]
                else:
                    continue
                if d < distancia_min:
                    distancia_min, veiculo_mais_prox = d, outro
            if veiculo_mais_prox:
                self.veiculo_frente = veiculo_mais_prox
                self.distancia_veiculo_frente = distancia_min
                self.processar_veiculo_frente(veiculo_mais_prox)
            else:
                self.veiculo_frente = None
                self.distancia_veiculo_frente = float('inf')
                if not self.aguardando_semaforo:
                    self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO * 0.3

        # ---- MOBIL-lite: tentativa de mudança de faixa (se houver ganho) ----
        if self._lane_cooldown_frames > 0:
            return  # ainda em cooldown

        # condição de “benefício”: estamos limitados pelo líder e relativamente perto
        limitado_por_lider = (
            self.veiculo_frente is not None and
            self.distancia_veiculo_frente < CONFIG.DISTANCIA_REACAO and
            (self.veiculo_frente.velocidade + 1e-3) < (self.velocidade_desejada * 0.9)
        )
        if not limitado_por_lider:
            return

        # penalidade: perto do próximo cruzamento → não trocar
        if self._distancia_ate_proximo_cruzamento() < max(80, 3 * CONFIG.LARGURA_FAIXA):
            return

        # avalia faixas vizinhas (ordem: melhor “abrir” por fora)
        candidatos = []
        if self.indice_faixa + 1 < CONFIG.FAIXAS_POR_VIA:
            candidatos.append(self.indice_faixa + 1)
        if self.indice_faixa - 1 >= 0:
            candidatos.append(self.indice_faixa - 1)

        for alvo in candidatos:
            if self.pode_mudar_faixa(alvo, todos_veiculos):
                # aplica troca “instantânea” (simples e barato)
                self.indice_faixa = alvo
                self._lane_cooldown_frames = int(0.75 * CONFIG.FPS)  # ~0.75s
                # “teleporta” para o centro da faixa (lateral)
                if self.direcao == Direcao.LESTE:
                    self.posicao[1] = self._lane_center_coord(Direcao.LESTE, self.indice_faixa)
                else:
                    self.posicao[0] = self._lane_center_coord(Direcao.NORTE, self.indice_faixa)
                break

    def pode_mudar_faixa(self, faixa_alvo: int, todos_veiculos: List['Veiculo']) -> bool:
        """Gap acceptance simplificado: checa líder e seguidor da faixa alvo e ganho esperado."""
        faixa_alvo = max(0, min(faixa_alvo, CONFIG.FAIXAS_POR_VIA - 1))

        # encontra líder e seguidor na faixa alvo (mesma via)
        leader_alvo = None
        follower_alvo = None
        d_leader = float('inf')
        d_follower = float('inf')

        for outro in todos_veiculos:
            if not outro.ativo or outro.id == self.id:
                continue
            if self.direcao != outro.direcao or not self._mesma_via_mesma_faixa(outro, faixa_alvo):
                continue

            if self.direcao == Direcao.NORTE:
                delta = outro.posicao[1] - self.posicao[1]
                if delta > 0:
                    if delta < d_leader:
                        d_leader, leader_alvo = delta, outro
                else:
                    if -delta < d_follower:
                        d_follower, follower_alvo = -delta, outro
            else:
                delta = outro.posicao[0] - self.posicao[0]
                if delta > 0:
                    if delta < d_leader:
                        d_leader, leader_alvo = delta, outro
                else:
                    if -delta < d_follower:
                        d_follower, follower_alvo = -delta, outro

        # gaps mínimos
        if d_leader < CONFIG.DISTANCIA_SEGURANCA:
            return False
        if d_follower < CONFIG.DISTANCIA_SEGURANCA:
            return False

        # ganho esperado: se na faixa atual há líder lento, e na alvo não (ou é mais rápido)
        v_lider_atual = self.veiculo_frente.velocidade if self.veiculo_frente else self.velocidade_desejada
        v_lider_alvo = leader_alvo.velocidade if leader_alvo else self.velocidade_desejada

        ganho = v_lider_alvo - v_lider_atual
        return ganho > 0.05  # precisa haver ganho mínimo

    def _distancia_ate_proximo_cruzamento(self) -> float:
        """Distância longitudinal até o próximo cruzamento à frente (aprox.)."""
        if self.direcao == Direcao.LESTE:
            # próximo X de cruzamento na mesma linha
            via_y_idx = self._via_idx()
            y_road = CONFIG.POSICAO_INICIAL_Y + via_y_idx * CONFIG.ESPACAMENTO_VERTICAL
            # próximos X: centro de cada coluna
            x = self.posicao[0]
            melhor = float('inf')
            for c in range(CONFIG.COLUNAS_GRADE):
                x_c = CONFIG.POSICAO_INICIAL_X + c * CONFIG.ESPACAMENTO_HORIZONTAL
                if x_c >= x:
                    melhor = min(melhor, x_c - x)
            return melhor if melhor != float('inf') else 9999.0
        else:
            # próximo Y de cruzamento na mesma coluna
            via_x_idx = self._via_idx()
            x_road = CONFIG.POSICAO_INICIAL_X + via_x_idx * CONFIG.ESPACAMENTO_HORIZONTAL
            y = self.posicao[1]
            melhor = float('inf')
            for l in range(CONFIG.LINHAS_GRADE):
                y_l = CONFIG.POSICAO_INICIAL_Y + l * CONFIG.ESPACAMENTO_VERTICAL
                if y_l >= y:
                    melhor = min(melhor, y_l - y)
            return melhor if melhor != float('inf') else 9999.0

    # ------------- atualização -------------
    def atualizar(self, dt: float = 1.0, todos_veiculos: List['Veiculo'] = None, malha=None) -> None:
        # métricas
        self.tempo_viagem += dt
        if self.velocidade < 0.1:
            self.tempo_parado += dt
            if not self.parado:
                self.paradas_totais += 1
            self.parado = True
        else:
            self.parado = False

        # cooldown de troca de faixa
        if self._lane_cooldown_frames > 0:
            self._lane_cooldown_frames -= 1

        # aceleração
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
            # corrige lateral para o centro da faixa
            self.posicao[0] = self._lane_center_coord(Direcao.NORTE, self.indice_faixa)
        else:
            dx = self.velocidade
            self.posicao[1] = self._lane_center_coord(Direcao.LESTE, self.indice_faixa)

        self.posicao[0] += dx
        self.posicao[1] += dy
        self.distancia_percorrida += math.sqrt(dx ** 2 + dy ** 2)

        self._atualizar_rect()

        # saída da tela (margem um pouco maior para evitar sumiços prematuros)
        margem = 150
        if (self.posicao[0] < -margem or
                self.posicao[0] > CONFIG.LARGURA_TELA + margem or
                self.posicao[1] < -margem or
                self.posicao[1] > CONFIG.ALTURA_TELA + margem):
            self.ativo = False

    # ------------- semáforo e car-following -------------
    def processar_semaforo(self, semaforo: Semaforo, posicao_parada: Tuple[float, float]) -> None:
        if not semaforo:
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        if self.ultimo_semaforo_processado != semaforo:
            self.passou_semaforo = False
            self.ultimo_semaforo_processado = semaforo
            self.pode_passar_amarelo = False

        if self.passou_semaforo:
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        self.distancia_semaforo = self._calcular_distancia_ate_ponto(posicao_parada)

        if self._passou_da_linha(posicao_parada):
            self.passou_semaforo = True
            self.aguardando_semaforo = False
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        if semaforo.estado == EstadoSemaforo.VERDE:
            self.aguardando_semaforo = False
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO

        elif semaforo.estado == EstadoSemaforo.AMARELO:
            if self.pode_passar_amarelo:
                self.aceleracao_atual = 0
            else:
                tempo_ate_linha = self.distancia_semaforo / max(self.velocidade, 0.1)
                if (tempo_ate_linha < 1.0 and
                        self.velocidade > CONFIG.VELOCIDADE_VEICULO * 0.7 and
                        self.distancia_semaforo < CONFIG.DISTANCIA_PARADA_SEMAFORO * 3):
                    self.pode_passar_amarelo = True
                    self.aceleracao_atual = 0
                else:
                    self._aplicar_frenagem_para_parada(self.distancia_semaforo)
                    self.aguardando_semaforo = True

        elif semaforo.estado == EstadoSemaforo.VERMELHO:
            self.aguardando_semaforo = True
            self.pode_passar_amarelo = False
            if self.distancia_semaforo <= CONFIG.DISTANCIA_PARADA_SEMAFORO:
                self.velocidade = 0.0
                self.aceleracao_atual = 0.0
            else:
                self._aplicar_frenagem_para_parada(self.distancia_semaforo)

    def processar_veiculo_frente(self, veiculo_frente: 'Veiculo') -> None:
        if not veiculo_frente:
            return
        distancia = self._calcular_distancia_para_veiculo(veiculo_frente)
        if distancia < CONFIG.DISTANCIA_MIN_VEICULO:
            self.velocidade = 0
            self.aceleracao_atual = 0
            return

        if distancia < CONFIG.DISTANCIA_REACAO:
            velocidade_segura = self._calcular_velocidade_segura(distancia, veiculo_frente.velocidade)
            if self.velocidade > velocidade_segura:
                if distancia < CONFIG.DISTANCIA_MIN_VEICULO * 1.5:
                    self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
                else:
                    self.aceleracao_atual = -CONFIG.DESACELERACAO_VEICULO
            elif self.velocidade < velocidade_segura * 0.9:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO * 0.3
            else:
                self.aceleracao_atual = 0
        else:
            if not self.aguardando_semaforo:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO

    # ------------- utilidades -------------
    def _calcular_distancia_ate_ponto(self, ponto: Tuple[float, float]) -> float:
        if self.direcao == Direcao.NORTE:
            return max(0, ponto[1] - self.posicao[1])
        elif self.direcao == Direcao.LESTE:
            return max(0, ponto[0] - self.posicao[0])
        return float('inf')

    def _passou_da_linha(self, ponto: Tuple[float, float]) -> bool:
        margem = 5
        if self.direcao == Direcao.NORTE:
            return self.posicao[1] > ponto[1] + margem
        elif self.direcao == Direcao.LESTE:
            return self.posicao[0] > ponto[0] + margem
        return False

    def _calcular_distancia_para_veiculo(self, outro: 'Veiculo') -> float:
        if self.direcao != outro.direcao:
            return float('inf')
        if not self._mesma_via_mesma_faixa(outro, self.indice_faixa):
            return float('inf')
        dx = outro.posicao[0] - self.posicao[0]
        dy = outro.posicao[1] - self.posicao[1]
        if self.direcao == Direcao.NORTE and dy > 0:
            return max(0, dy - (self.altura + outro.altura) / 2)
        elif self.direcao == Direcao.LESTE and dx > 0:
            return max(0, dx - (self.altura + outro.altura) / 2)
        return float('inf')

    def _calcular_velocidade_segura(self, distancia: float, velocidade_lider: float) -> float:
        if distancia < CONFIG.DISTANCIA_MIN_VEICULO:
            return 0
        tempo_reacao = 1.0
        distancia_segura = CONFIG.DISTANCIA_SEGURANCA + velocidade_lider * tempo_reacao
        if distancia < distancia_segura:
            fator = distancia / distancia_segura
            return velocidade_lider * fator
        return CONFIG.VELOCIDADE_VEICULO

    def _aplicar_frenagem_para_parada(self, distancia: float) -> None:
        if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO:
            self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
            self.velocidade_desejada = 0
            if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO / 2:
                self.velocidade = 0.0
        else:
            if self.velocidade > 0.1 and distancia > 0:
                desaceleracao_necessaria = (self.velocidade ** 2) / (2 * distancia)
                self.aceleracao_atual = -min(desaceleracao_necessaria, CONFIG.DESACELERACAO_VEICULO)
            else:
                self.aceleracao_atual = 0
