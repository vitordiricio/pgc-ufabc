import random
import math
from typing import Tuple, Optional, List, Dict
import pygame
from configuracao import CONFIG, Direcao, EstadoSemaforo
from semaforo import Semaforo


class Veiculo:
    """Representa um veículo com suporte a viradas em cruzamentos (N→L esquerda, L→N direita)."""

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

        self.largura = CONFIG.LARGURA_VEICULO
        self.altura = CONFIG.ALTURA_VEICULO

        self.velocidade = 0.0
        self.velocidade_desejada = CONFIG.VELOCIDADE_VEICULO
        self.aceleracao_atual = 0.0

        self.parado = True
        self.no_cruzamento = False
        self.passou_semaforo = False
        self.aguardando_semaforo = False
        self.em_desaceleracao = False

        # Semáforo
        self.semaforo_proximo: Optional[Semaforo] = None
        self.ultimo_semaforo_processado: Optional[Semaforo] = None
        self.distancia_semaforo: float = float('inf')
        self.pode_passar_amarelo: bool = False

        # Colisão / car-following
        self.veiculo_frente: Optional['Veiculo'] = None
        self.distancia_veiculo_frente: float = float('inf')

        # Métricas
        self.tempo_viagem = 0
        self.tempo_parado = 0
        self.paradas_totais = 0
        self.distancia_percorrida = 0.0

        # ------------ VIRADAS ------------
        # Próxima decisão de movimento na interseção (None = seguir reto)
        self.proxima_mudanca: Optional[Direcao] = None
        # Estado interno de curva (quarter-arc)
        self.em_curva: bool = False
        self.curva_t: float = 0.0
        self.curva_raio: float = CONFIG.RAIO_CURVA
        self.curva_origem: Optional[Direcao] = None
        self.curva_destino: Optional[Direcao] = None
        self.curva_centro: Optional[Tuple[float, float]] = None

        self._atualizar_rect()

    def _atualizar_rect(self) -> None:
        if self.direcao == Direcao.NORTE:
            self.rect = pygame.Rect(
                self.posicao[0] - self.largura // 2,
                self.posicao[1] - self.altura // 2,
                self.largura,
                self.altura
            )
        elif self.direcao == Direcao.LESTE:
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
            # Ao entrar num novo cruzamento, limpa decisão passada (permitindo novas viradas)
            self.proxima_mudanca = None

    # ----------------- DECISÃO DE VIRADA -----------------
    def _decidir_mudanca(self) -> None:
        """Define a próxima manobra (reta/virar) ao aproximar da linha de parada."""
        if not CONFIG.HABILITAR_VIRADAS or self.proxima_mudanca is not None:
            return
        if self.direcao == Direcao.NORTE:
            # N pode: seguir N (reto) ou virar N→L (esquerda)
            if random.random() < CONFIG.PROB_VIRAR_NORTE_PARA_LESTE:
                self.proxima_mudanca = Direcao.LESTE
            else:
                self.proxima_mudanca = Direcao.NORTE
        elif self.direcao == Direcao.LESTE:
            # L pode: seguir L (reto) ou virar L→N (direita)
            if random.random() < CONFIG.PROB_VIRAR_LESTE_PARA_NORTE:
                self.proxima_mudanca = Direcao.NORTE
            else:
                self.proxima_mudanca = Direcao.LESTE

    def _virada_permitida(self, semaforos_cruz: Dict[Direcao, Semaforo]) -> bool:
        """Regras de prioridade para iniciar a curva ao entrar no cruzamento."""
        if self.proxima_mudanca is None or self.proxima_mudanca == self.direcao:
            return True  # seguir reto não tem restrição extra

        # N→L (esquerda) — protegida por padrão (LESTE deve estar vermelho)
        if self.direcao == Direcao.NORTE and self.proxima_mudanca == Direcao.LESTE:
            sem_leste = semaforos_cruz.get(Direcao.LESTE)
            if CONFIG.ESQUERDA_NORTE_PROTEGIDA:
                return (sem_leste is not None) and (sem_leste.estado == EstadoSemaforo.VERMELHO)
            else:
                # Modo "permissivo" simplificado: evita quando LESTE está VERDE
                return (sem_leste is None) or (sem_leste.estado != EstadoSemaforo.VERDE)

        # L→N (direita) — permitido quando LESTE (abordagem atual) está verde (já garantido pela lógica)
        if self.direcao == Direcao.LESTE and self.proxima_mudanca == Direcao.NORTE:
            return True

        return True

    def _iniciar_curva(self, centro_cruz: Tuple[float, float]) -> None:
        """Inicializa parâmetros do arco de 1/4 de círculo para a virada."""
        if self.proxima_mudanca is None or self.proxima_mudanca == self.direcao:
            return
        cx, cy = centro_cruz
        r = self.curva_raio
        self.curva_t = 0.0
        self.em_curva = True
        self.curva_origem = self.direcao
        self.curva_destino = self.proxima_mudanca

        # Ajusta posição de entrada no arco para evitar 'saltos' grandes
        # N→L (esquerda): entra por cima do centro e sai à direita do centro
        if self.direcao == Direcao.NORTE and self.proxima_mudanca == Direcao.LESTE:
            self.curva_centro = (cx + r, cy - r)
            # colar na entrada do arco
            self.posicao[0] = cx
            self.posicao[1] = cy - r
        # L→N (direita): entra pela esquerda do centro e sai por baixo do centro
        elif self.direcao == Direcao.LESTE and self.proxima_mudanca == Direcao.NORTE:
            self.curva_centro = (cx - r, cy + r)
            self.posicao[0] = cx - r
            self.posicao[1] = cy

        # durante a curva, mantemos velocidade atual e anulamos aceleração
        self.aceleracao_atual = 0.0
        self._atualizar_rect()

    def _atualizar_curva(self, dt: float) -> None:
        """Avança a curva com base na velocidade atual, em um arco de 90°."""
        if not self.em_curva or self.curva_centro is None or self.curva_destino is None:
            return

        r = self.curva_raio
        comprimento = (math.pi / 2.0) * r
        # delta em 't' proporcional à distância percorrida no quadro
        delta_t = 0.0
        if comprimento > 0:
            delta_t = (self.velocidade * dt) / comprimento

        self.curva_t = min(1.0, self.curva_t + delta_t)
        t = self.curva_t  # 0..1
        theta = t * (math.pi / 2.0)

        cx, cy = self.curva_centro

        if self.curva_origem == Direcao.NORTE and self.curva_destino == Direcao.LESTE:
            # Parametrização:
            # inicia em (cx - r, cy?) — usamos forma que gera pontos contínuos
            x = cx - r * math.cos(theta)
            y = cy + r * math.sin(theta)
            self.posicao[0] = x
            self.posicao[1] = y

        elif self.curva_origem == Direcao.LESTE and self.curva_destino == Direcao.NORTE:
            # centro (cx, cy), inicia em (cx, cy - r) "rotacionado" adequadamente
            x = cx + r * math.sin(theta)
            y = cy - r * math.cos(theta)
            self.posicao[0] = x
            self.posicao[1] = y

        self._atualizar_rect()

        if self.curva_t >= 1.0:
            # Curva concluída: ajusta direção e limpa estado
            self.direcao = self.curva_destino
            self.em_curva = False
            self.curva_origem = None
            self.curva_destino = None
            self.curva_centro = None
            # Após a curva, pode voltar a acelerar suavemente
            self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO * 0.5
            self._atualizar_rect()

    # ----------------- COLISÃO / FOLLOWING -----------------
    def verificar_colisao_futura(self, todos_veiculos: List['Veiculo']) -> bool:
        # Se está em curva, negligenciamos previsão de colisão com base retangular simples
        if self.em_curva:
            return False

        dx, dy = 0, 0
        if self.direcao == Direcao.NORTE:
            dy = self.velocidade + CONFIG.DISTANCIA_MIN_VEICULO / 2
        elif self.direcao == Direcao.LESTE:
            dx = self.velocidade + CONFIG.DISTANCIA_MIN_VEICULO / 2

        posicao_futura = [self.posicao[0] + dx, self.posicao[1] + dy]

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

        for outro in todos_veiculos:
            if outro.id == self.id or not outro.ativo:
                continue
            if not self._mesma_via(outro):
                continue
            rect_outro_expandido = outro.rect.inflate(10, 10)
            if rect_futuro.colliderect(rect_outro_expandido):
                return True
        return False

    def processar_todos_veiculos(self, todos_veiculos: List['Veiculo']) -> None:
        if self.em_curva:
            # durante a curva, ignoramos o líder retilíneo
            self.veiculo_frente = None
            self.distancia_veiculo_frente = float('inf')
            return

        veiculo_mais_proximo = None
        distancia_minima = float('inf')

        for outro in todos_veiculos:
            if outro.id == self.id or not outro.ativo:
                continue
            if self.direcao != outro.direcao or not self._mesma_via(outro):
                continue

            if self.direcao == Direcao.NORTE:
                if outro.posicao[1] > self.posicao[1]:
                    distancia = outro.posicao[1] - self.posicao[1]
                    if distancia < distancia_minima:
                        distancia_minima = distancia
                        veiculo_mais_proximo = outro
            elif self.direcao == Direcao.LESTE:
                if outro.posicao[0] > self.posicao[0]:
                    distancia = outro.posicao[0] - self.posicao[0]
                    if distancia < distancia_minima:
                        distancia_minima = distancia
                        veiculo_mais_proximo = outro

        if veiculo_mais_proximo:
            self.veiculo_frente = veiculo_mais_proximo
            self.distancia_veiculo_frente = distancia_minima
            self.processar_veiculo_frente(veiculo_mais_proximo)
        else:
            self.veiculo_frente = None
            self.distancia_veiculo_frente = float('inf')
            if not self.aguardando_semaforo:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO

    # ----------------- ATUALIZAÇÃO -----------------
    def atualizar(self, dt: float = 1.0, todos_veiculos: List['Veiculo'] = None, malha=None) -> None:
        # Métricas
        self.tempo_viagem += dt
        if self.velocidade < 0.1:
            self.tempo_parado += dt
            if not self.parado:
                self.paradas_totais += 1
            self.parado = True
        else:
            self.parado = False

        # Aceleração / limite local (caos)
        self.velocidade += self.aceleracao_atual * dt
        fator = malha.obter_fator_caos(self) if malha is not None else 1.0
        vmax_local = CONFIG.VELOCIDADE_MAX_VEICULO * fator
        self.velocidade = max(CONFIG.VELOCIDADE_MIN_VEICULO, min(vmax_local, self.velocidade))

        # Colisão simples
        if (todos_veiculos is not None) and self.velocidade > 0 and not self.em_curva:
            if self.verificar_colisao_futura(todos_veiculos):
                self.velocidade = 0
                self.aceleracao_atual = 0
                self._atualizar_rect()
                return

        # Movimento
        if self.em_curva:
            # Atualiza ao longo do arco
            self._atualizar_curva(dt)
            # distância percorrida (aproximação)
            self.distancia_percorrida += self.velocidade * dt
            self._atualizar_rect()
        else:
            dx, dy = 0, 0
            if self.direcao == Direcao.NORTE:
                dy = self.velocidade
            elif self.direcao == Direcao.LESTE:
                dx = self.velocidade

            self.posicao[0] += dx
            self.posicao[1] += dy
            self.distancia_percorrida += math.sqrt(dx ** 2 + dy ** 2)
            self._atualizar_rect()

        # Saída da tela
        margem = 100
        if (self.posicao[0] < -margem or
                self.posicao[0] > CONFIG.LARGURA_TELA + margem or
                self.posicao[1] < -margem or
                self.posicao[1] > CONFIG.ALTURA_TELA + margem):
            self.ativo = False

    # ----------------- SEMÁFORO -----------------
    def processar_semaforo(
        self,
        semaforo: Semaforo,
        posicao_parada: Tuple[float, float],
        semaforos_cruz: Dict[Direcao, Semaforo],
        centro_cruz: Tuple[float, float]
    ) -> None:
        """Inclui decisão de virada na zona de decisão e início da curva quando permitido."""
        if not semaforo:
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        # Novo semáforo detectado?
        if self.ultimo_semaforo_processado != semaforo:
            self.passou_semaforo = False
            self.ultimo_semaforo_processado = semaforo
            self.pode_passar_amarelo = False

        if self.passou_semaforo:
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        # Distância até a linha de parada
        self.distancia_semaforo = self._calcular_distancia_ate_ponto(posicao_parada)

        # Zona de decisão de rota (antes da linha)
        if CONFIG.HABILITAR_VIRADAS and self.distancia_semaforo <= CONFIG.ZONA_DECISAO_VIRADA:
            self._decidir_mudanca()

        # Se já passou a linha, marca como passado e, se for virar, inicia curva (se permitido)
        if self._passou_da_linha(posicao_parada):
            # Está autorizado a executar a virada agora?
            if self.proxima_mudanca and self.proxima_mudanca != self.direcao:
                if self._virada_permitida(semaforos_cruz) and not self.em_curva:
                    self._iniciar_curva(centro_cruz)
            self.passou_semaforo = True
            self.aguardando_semaforo = False
            if not self.veiculo_frente or self.distancia_veiculo_frente > CONFIG.DISTANCIA_REACAO:
                self.aceleracao_atual = CONFIG.ACELERACAO_VEICULO
            return

        # Lógica por estado do semáforo
        if semaforo.estado == EstadoSemaforo.VERDE:
            self.aguardando_semaforo = False

            # Se pretende virar, certifique-se de que é permitido entrar
            if self.proxima_mudanca and self.proxima_mudanca != self.direcao:
                if not self._virada_permitida(semaforos_cruz):
                    # Trate como um “pare” antes da linha de parada
                    self._aplicar_frenagem_para_parada(self.distancia_semaforo)
                    self.aguardando_semaforo = True
                    return

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

    # ----------------- FOLLOWING / UTIL -----------------
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

    def _calcular_distancia_ate_ponto(self, ponto: Tuple[float, float]) -> float:
        if self.direcao == Direcao.NORTE:
            return max(0, ponto[1] - self.posicao[1])
        elif self.direcao == Direcao.LESTE:
            return max(0, ponto[0] - self.posicao[0])
        return float('inf')

    def _passou_da_linha(self, ponto: Tuple[float, float]) -> bool:
        margem = 10
        if self.direcao == Direcao.NORTE:
            return self.posicao[1] > ponto[1] + margem
        elif self.direcao == Direcao.LESTE:
            return self.posicao[0] > ponto[0] + margem
        return False

    def _calcular_distancia_para_veiculo(self, outro: 'Veiculo') -> float:
        if self.direcao != outro.direcao:
            return float('inf')
        if not self._mesma_via(outro):
            return float('inf')
        dx = outro.posicao[0] - self.posicao[0]
        dy = outro.posicao[1] - self.posicao[1]
        if self.direcao == Direcao.NORTE:
            if dy > 0:
                return max(0, dy - (self.altura + outro.altura) / 2)
        elif self.direcao == Direcao.LESTE:
            if dx > 0:
                return max(0, dx - (self.altura + outro.altura) / 2)
        return float('inf')

    def _mesma_via(self, outro: 'Veiculo') -> bool:
        tolerancia = CONFIG.LARGURA_RUA * 0.8
        if self.direcao == Direcao.NORTE:
            return abs(self.posicao[0] - outro.posicao[0]) < tolerancia
        elif self.direcao == Direcao.LESTE:
            return abs(self.posicao[1] - outro.posicao[1]) < tolerancia
        return False

    def _calcular_velocidade_segura(self, distancia: float, velocidade_lider: float) -> float:
        if distancia < CONFIG.DISTANCIA_MIN_VEICULO:
            return 0
        tempo_reacao = 1.0
        distancia_segura = CONFIG.DISTANCIA_SEGURANCA + velocidade_lider * tempo_reacao
        if distancia < distancia_segura:
            fator = distancia / distancia_segura
            return max(0.0, velocidade_lider * fator)
        return CONFIG.VELOCIDADE_VEICULO

    def _aplicar_frenagem_para_parada(self, distancia: float) -> None:
        if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO:
            self.aceleracao_atual = -CONFIG.DESACELERACAO_EMERGENCIA
            self.velocidade_desejada = 0
            if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO / 2:
                self.velocidade = 0.0
        else:
            if self.velocidade > 0.1:
                desaceleracao_necessaria = (self.velocidade ** 2) / (2 * distancia)
                self.aceleracao_atual = -min(desaceleracao_necessaria, CONFIG.DESACELERACAO_VEICULO)
            else:
                self.aceleracao_atual = 0

    def desenhar(self, tela: pygame.Surface) -> None:
        if self.direcao == Direcao.NORTE:
            superficie = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
        else:
            superficie = pygame.Surface((self.altura, self.largura), pygame.SRCALPHA)

        pygame.draw.rect(superficie, self.cor, superficie.get_rect(), border_radius=4)

        cor_janela = (200, 220, 255, 180)
        if self.direcao == Direcao.NORTE:
            pygame.draw.rect(superficie, cor_janela,
                             (3, self.altura * 0.7, self.largura - 6, self.altura * 0.25),
                             border_radius=2)
            pygame.draw.rect(superficie, cor_janela,
                             (3, 3, self.largura - 6, self.altura * 0.3),
                             border_radius=2)
        else:
            pygame.draw.rect(superficie, cor_janela,
                             (self.altura * 0.7, 3, self.altura * 0.25, self.largura - 6),
                             border_radius=2)
            pygame.draw.rect(superficie, cor_janela,
                             (3, 3, self.altura * 0.3, self.largura - 6),
                             border_radius=2)

        if self.aceleracao_atual < -0.1:
            cor_freio = (255, 100, 100)
            if self.direcao == Direcao.NORTE:
                pygame.draw.rect(superficie, cor_freio, (2, 1, 6, 3))
                pygame.draw.rect(superficie, cor_freio, (self.largura - 8, 1, 6, 3))
            elif self.direcao == Direcao.LESTE:
                pygame.draw.rect(superficie, cor_freio, (1, 2, 3, 6))
                pygame.draw.rect(superficie, cor_freio, (1, self.largura - 8, 3, 6))

        cor_farol = (255, 255, 200, 150)
        if self.direcao == Direcao.NORTE:
            pygame.draw.circle(superficie, cor_farol, (8, self.altura - 5), 3)
            pygame.draw.circle(superficie, cor_farol, (self.largura - 8, self.altura - 5), 3)
        elif self.direcao == Direcao.LESTE:
            pygame.draw.circle(superficie, cor_farol, (self.altura - 5, 8), 3)
            pygame.draw.circle(superficie, cor_farol, (self.altura - 5, self.largura - 8), 3)

        rect = superficie.get_rect(center=(int(self.posicao[0]), int(self.posicao[1])))
        tela.blit(superficie, rect)

        # (Opcional) Trajetória de depuração para curvas
        if CONFIG.MOSTRAR_INFO_VEICULO:
            fonte = pygame.font.SysFont('Arial', 10)
            aguardando = ""
            if self.aguardando_semaforo:
                aguardando = "🔴"
            elif self.veiculo_frente and self.distancia_veiculo_frente < CONFIG.DISTANCIA_REACAO:
                aguardando = "🚗"
            texto = f"V:{self.velocidade:.1f} ID:{self.id} {aguardando}"
            superficie_texto = fonte.render(texto, True, CONFIG.BRANCO)
            tela.blit(superficie_texto, (self.posicao[0] - 20, self.posicao[1] - 25))
