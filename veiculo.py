# veiculo.py
import random
import math
from typing import Tuple, Optional, List, Dict
import pygame
from configuracao import CONFIG, Direcao, EstadoSemaforo, TipoVeiculo
from semaforo import Semaforo


def _offset_faixa(idx: int) -> float:
    return (idx - (CONFIG.NUM_FAIXAS - 1) / 2.0) * CONFIG.LARGURA_FAIXA


def _ease_in_out_sine(t: float) -> float:
    # Curva suave para troca de faixa
    return 0.5 * (1 - math.cos(math.pi * max(0.0, min(1.0, t))))


class Veiculo:
    """Veículo com viradas (Item 1) + múltiplas faixas e troca (Item 2) + TIPOS (Item 3)."""

    _contador_id = 0

    def __init__(
        self,
        direcao: Direcao,
        posicao: Tuple[float, float],
        id_cruzamento_origem: Tuple[int, int],
        tipo: Optional[TipoVeiculo] = None
    ):
        if direcao not in CONFIG.DIRECOES_PERMITIDAS:
            raise ValueError(f"Direção {direcao} não permitida. Use {CONFIG.DIRECOES_PERMITIDAS}")

        Veiculo._contador_id += 1
        self.id = Veiculo._contador_id

        self.direcao = direcao
        self.posicao = list(posicao)
        self.posicao_inicial = list(posicao)
        self.id_cruzamento_origem = id_cruzamento_origem
        self.id_cruzamento_atual = id_cruzamento_origem

        # ---------- Tipo de Veículo ----------
        self.tipo: TipoVeiculo = tipo or TipoVeiculo.CARRO
        params = CONFIG.PARAMS_TIPO_VEICULO.get(self.tipo, {})

        # Dimensões
        self.largura = int(params.get('largura', CONFIG.LARGURA_VEICULO))
        self.altura = int(params.get('comprimento', CONFIG.ALTURA_VEICULO))

        # Física
        self.vmin = float(params.get('vel_min', CONFIG.VELOCIDADE_MIN_VEICULO))
        self.velocidade_desejada = float(params.get('vel_base', CONFIG.VELOCIDADE_VEICULO))
        self.vmax = float(params.get('vel_max', CONFIG.VELOCIDADE_MAX_VEICULO))

        self.acel_base = float(params.get('acel', CONFIG.ACELERACAO_VEICULO))
        self.desac = float(params.get('desac', CONFIG.DESACELERACAO_VEICULO))
        self.desac_emer = float(params.get('desac_emer', CONFIG.DESACELERACAO_EMERGENCIA))

        self.dist_min = float(params.get('dist_min', CONFIG.DISTANCIA_MIN_VEICULO))
        self.dist_seguranca = float(params.get('dist_seg', CONFIG.DISTANCIA_SEGURANCA))
        self.dist_reacao = float(params.get('dist_reacao', CONFIG.DISTANCIA_REACAO))

        # Cor (prioriza cor por tipo)
        self.cor = CONFIG.CORES_TIPO.get(self.tipo, random.choice(CONFIG.CORES_VEICULO))

        # Estados dinâmicos
        self.ativo = True
        self.velocidade = 0.0
        self.aceleracao_atual = 0.0

        self.parado = True
        self.no_cruzamento = False
        self.passou_semaforo = False
        self.aguardando_semaforo = False
        self.em_desaceleracao = False

        self.semaforo_proximo: Optional[Semaforo] = None
        self.ultimo_semaforo_processado: Optional[Semaforo] = None
        self.distancia_semaforo: float = float('inf')
        self.pode_passar_amarelo: bool = False

        self.veiculo_frente: Optional['Veiculo'] = None
        self.distancia_veiculo_frente: float = float('inf')

        self.tempo_viagem = 0
        self.tempo_parado = 0
        self.paradas_totais = 0
        self.distancia_percorrida = 0.0

        # ---------- Faixas ----------
        self.faixa_id: int = 0  # definido no spawn; default 0 por segurança
        self.em_troca_faixa: bool = False
        self.faixa_destino: Optional[int] = None
        self.troca_t: float = 0.0
        self._lateral_inicio: float = 0.0
        self._lateral_fim: float = 0.0

        # ------------ VIRADAS ------------
        self.proxima_mudanca: Optional[Direcao] = None
        self.em_curva: bool = False
        self.curva_t: float = 0.0
        self.curva_raio: float = CONFIG.RAIO_CURVA
        self.curva_origem: Optional[Direcao] = None
        self.curva_destino: Optional[Direcao] = None
        self.curva_centro: Optional[Tuple[float, float]] = None

        self._atualizar_rect()

    # -------- util de grade/lanes ----------
    def _centro_via_atual(self) -> Tuple[float, float]:
        """Retorna (x_centro_via, y_centro_via) do eixo da via onde o veículo está."""
        if self.direcao == Direcao.LESTE:
            idx_linha = round((self.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
            y = CONFIG.POSICAO_INICIAL_Y + idx_linha * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            return (None, y)
        elif self.direcao == Direcao.NORTE:
            idx_col = round((self.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS)
            x = CONFIG.POSICAO_INICIAL_X + idx_col * CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS
            return (x, None)
        return (None, None)

    def _centro_da_faixa(self) -> float:
        """Coordenada lateral do centro da faixa atual."""
        cx, cy = self._centro_via_atual()
        if self.direcao == Direcao.LESTE:
            return (cy or 0.0) + _offset_faixa(self.faixa_id)
        elif self.direcao == Direcao.NORTE:
            return (cx or 0.0) + _offset_faixa(self.faixa_id)
        return 0.0

    def _alinhar_na_faixa(self) -> None:
        """Clampa a coordenada lateral para o centro da faixa (evita drift)."""
        alvo = self._centro_da_faixa()
        if self.direcao == Direcao.LESTE:
            self.posicao[1] = alvo
        elif self.direcao == Direcao.NORTE:
            self.posicao[0] = alvo

    # ---------- retângulo ----------
    def _atualizar_rect(self) -> None:
        if self.direcao == Direcao.NORTE:
            self.rect = pygame.Rect(
                self.posicao[0] - self.largura // 2,
                self.posicao[1] - self.altura // 2,
                self.largura, self.altura
            )
        elif self.direcao == Direcao.LESTE:
            self.rect = pygame.Rect(
                self.posicao[0] - self.altura // 2,
                self.posicao[1] - self.largura // 2,
                self.altura, self.largura
            )

    def resetar_controle_semaforo(self, novo_cruzamento_id: Optional[Tuple[int, int]] = None) -> None:
        if novo_cruzamento_id and novo_cruzamento_id != self.id_cruzamento_atual:
            self.id_cruzamento_atual = novo_cruzamento_id
            self.passou_semaforo = False
            self.aguardando_semaforo = False
            self.pode_passar_amarelo = False
            self.semaforo_proximo = None
            self.distancia_semaforo = float('inf')
            self.proxima_mudanca = None

    # ----------------- DECISÃO DE VIRADA -----------------
    def _decidir_mudanca(self) -> None:
        if not CONFIG.HABILITAR_VIRADAS or self.proxima_mudanca is not None:
            return
        if self.direcao == Direcao.NORTE:
            self.proxima_mudanca = Direcao.LESTE if random.random() < CONFIG.PROB_VIRAR_NORTE_PARA_LESTE else Direcao.NORTE
        elif self.direcao == Direcao.LESTE:
            self.proxima_mudanca = Direcao.NORTE if random.random() < CONFIG.PROB_VIRAR_LESTE_PARA_NORTE else Direcao.LESTE

    def _virada_permitida(self, semaforos_cruz: Dict[Direcao, Semaforo]) -> bool:
        if self.proxima_mudanca is None or self.proxima_mudanca == self.direcao:
            return True
        if self.direcao == Direcao.NORTE and self.proxima_mudanca == Direcao.LESTE:
            sem_leste = semaforos_cruz.get(Direcao.LESTE)
            if CONFIG.ESQUERDA_NORTE_PROTEGIDA:
                return (sem_leste is not None) and (sem_leste.estado == EstadoSemaforo.VERMELHO)
            return (sem_leste is None) or (sem_leste.estado != EstadoSemaforo.VERDE)
        if self.direcao == Direcao.LESTE and self.proxima_mudanca == Direcao.NORTE:
            return True
        return True

    def _iniciar_curva(self, centro_cruz: Tuple[float, float]) -> None:
        if self.proxima_mudanca is None or self.proxima_mudanca == self.direcao:
            return
        cx, cy = centro_cruz
        r = self.curva_raio
        self.curva_t = 0.0
        self.em_curva = True
        self.curva_origem = self.direcao
        self.curva_destino = self.proxima_mudanca

        if self.direcao == Direcao.NORTE and self.proxima_mudanca == Direcao.LESTE:
            self.curva_centro = (cx + r, cy - r)
            self.posicao[0] = cx
            self.posicao[1] = cy - r
        elif self.direcao == Direcao.LESTE and self.proxima_mudanca == Direcao.NORTE:
            self.curva_centro = (cx - r, cy + r)
            self.posicao[0] = cx - r
            self.posicao[1] = cy

        self.aceleracao_atual = 0.0
        self._atualizar_rect()

    def _atualizar_curva(self, dt: float) -> None:
        if not self.em_curva or self.curva_centro is None or self.curva_destino is None:
            return
        r = self.curva_raio
        comprimento = (math.pi / 2.0) * r
        delta_t = 0.0 if comprimento <= 0 else (self.velocidade * dt) / comprimento
        self.curva_t = min(1.0, self.curva_t + delta_t)
        t = self.curva_t
        theta = t * (math.pi / 2.0)
        cx, cy = self.curva_centro

        if self.curva_origem == Direcao.NORTE and self.curva_destino == Direcao.LESTE:
            x = cx - r * math.cos(theta)
            y = cy + r * math.sin(theta)
            self.posicao[0] = x
            self.posicao[1] = y
        elif self.curva_origem == Direcao.LESTE and self.curva_destino == Direcao.NORTE:
            x = cx + r * math.sin(theta)
            y = cy - r * math.cos(theta)
            self.posicao[0] = x
            self.posicao[1] = y

        self._atualizar_rect()

        if self.curva_t >= 1.0:
            self.direcao = self.curva_destino
            self.em_curva = False
            self.curva_origem = None
            self.curva_destino = None
            self.curva_centro = None
            # ao sair da curva, alinhar à faixa mais próxima
            self._snap_para_faixa_mais_proxima()
            self.aceleracao_atual = self.acel_base * 0.5
            self._atualizar_rect()

    def _snap_para_faixa_mais_proxima(self) -> None:
        """Após a curva, escolhe a faixa mais próxima e alinha ao centro."""
        melhor = 0
        melhor_dist = float('inf')
        for f in range(CONFIG.NUM_FAIXAS):
            alvo = (self._centro_via_atual()[1] if self.direcao == Direcao.LESTE
                    else self._centro_via_atual()[0]) + _offset_faixa(f)
            dist = abs((self.posicao[1] if self.direcao == Direcao.LESTE else self.posicao[0]) - alvo)
            if dist < melhor_dist:
                melhor_dist = dist
                melhor = f
        self.faixa_id = melhor
        self._alinhar_na_faixa()

    # ----------------- COLISÃO / FOLLOWING - MELHORADO -----------------
    def verificar_colisao_completa(self, todos_veiculos: List['Veiculo']) -> bool:
        """Verificação robusta de colisão em todas as situações."""
        # Margem de segurança maior para evitar colisões
        margem_seguranca = 25
        rect_expandido = self.rect.inflate(margem_seguranca, margem_seguranca)
        
        for outro in todos_veiculos:
            if outro.id == self.id or not outro.ativo:
                continue
            
            # Verifica colisão com rect expandido
            if rect_expandido.colliderect(outro.rect):
                return True
                
        return False

    def verificar_colisao_futura(self, todos_veiculos: List['Veiculo']) -> bool:
        """Verifica colisões futuras considerando movimento."""
        # Calcula posição futura
        passos_futuro = 2  # Verifica 2 frames à frente (reduzido para evitar paradas excessivas)
        dx = dy = 0
        
        if not self.em_curva:
            if self.direcao == Direcao.NORTE:
                dy = self.velocidade * passos_futuro
            elif self.direcao == Direcao.LESTE:
                dx = self.velocidade * passos_futuro
        else:
            # Durante curva, usa velocidade reduzida
            if self.direcao == Direcao.NORTE or self.curva_origem == Direcao.NORTE:
                dy = self.velocidade * passos_futuro * 0.5
            if self.direcao == Direcao.LESTE or self.curva_origem == Direcao.LESTE:
                dx = self.velocidade * passos_futuro * 0.5
        
        pos_fut = [self.posicao[0] + dx, self.posicao[1] + dy]
        
        # Cria retângulo futuro com margem menor para evitar paradas desnecessárias
        margem = 15
        if self.direcao == Direcao.NORTE or (self.em_curva and self.curva_origem == Direcao.NORTE):
            rect_fut = pygame.Rect(
                pos_fut[0] - self.largura // 2 - margem // 2,
                pos_fut[1] - self.altura // 2 - margem // 2,
                self.largura + margem,
                self.altura + margem
            )
        else:
            rect_fut = pygame.Rect(
                pos_fut[0] - self.altura // 2 - margem // 2,
                pos_fut[1] - self.largura // 2 - margem // 2,
                self.altura + margem,
                self.largura + margem
            )

        for outro in todos_veiculos:
            if outro.id == self.id or not outro.ativo:
                continue
            
            # Verifica colisão com qualquer veículo próximo
            rect_outro_expandido = outro.rect.inflate(10, 10)
            if rect_fut.colliderect(rect_outro_expandido):
                return True
                
        return False

    def detectar_veiculo_proximo(self, todos_veiculos: List['Veiculo'], raio: float = 100) -> Optional['Veiculo']:
        """Detecta qualquer veículo dentro de um raio, independente de faixa ou direção."""
        veiculo_mais_proximo = None
        dist_min = raio
        
        for outro in todos_veiculos:
            if outro.id == self.id or not outro.ativo:
                continue
                
            dx = abs(outro.posicao[0] - self.posicao[0])
            dy = abs(outro.posicao[1] - self.posicao[1])
            dist = math.sqrt(dx**2 + dy**2)
            
            if dist < dist_min:
                dist_min = dist
                veiculo_mais_proximo = outro
                
        return veiculo_mais_proximo

    def processar_todos_veiculos(self, todos_veiculos: List['Veiculo']) -> None:
        """Processamento melhorado considerando múltiplas situações."""
        # Durante curva, detecta veículos em qualquer direção
        if self.em_curva:
            proximo = self.detectar_veiculo_proximo(todos_veiculos, raio=60)
            if proximo:
                dist = math.sqrt((proximo.posicao[0] - self.posicao[0])**2 + 
                               (proximo.posicao[1] - self.posicao[1])**2)
                if dist < self.dist_min * 1.2:
                    self.velocidade = min(self.velocidade, proximo.velocidade * 0.7)
                    self.aceleracao_atual = -self.desac
            self.veiculo_frente = proximo
            self.distancia_veiculo_frente = dist if proximo else float('inf')
            return

        # Procura líder na mesma faixa ou em transição
        veiculo_mais_prox = None
        dist_min = float('inf')
        
        for outro in todos_veiculos:
            if outro.id == self.id or not outro.ativo:
                continue
                
            # Verifica se está na mesma via ou em transição próxima
            if self.direcao != outro.direcao:
                # Verifica se outro está virando para nossa direção
                if not (outro.em_curva and outro.curva_destino == self.direcao):
                    continue
            
            # Durante troca de faixa, considera ambas as faixas
            if self.em_troca_faixa:
                faixas_considerar = [self.faixa_id]
                if self.faixa_destino is not None:
                    faixas_considerar.append(self.faixa_destino)
                    
                if hasattr(outro, 'faixa_id'):
                    if outro.faixa_id not in faixas_considerar:
                        # Também considera veículos em troca adjacente
                        if outro.em_troca_faixa:
                            if outro.faixa_destino not in faixas_considerar and outro.faixa_id not in faixas_considerar:
                                continue
                        else:
                            continue
            else:
                # Mesma faixa ou veículo em troca para nossa faixa
                if hasattr(outro, 'faixa_id'):
                    if outro.faixa_id != self.faixa_id:
                        if not (outro.em_troca_faixa and outro.faixa_destino == self.faixa_id):
                            continue
            
            # Verifica se está à frente
            if self.direcao == Direcao.NORTE:
                if outro.posicao[1] > self.posicao[1]:
                    d = outro.posicao[1] - self.posicao[1]
                    if d < dist_min:
                        dist_min = d
                        veiculo_mais_prox = outro
            elif self.direcao == Direcao.LESTE:
                if outro.posicao[0] > self.posicao[0]:
                    d = outro.posicao[0] - self.posicao[0]
                    if d < dist_min:
                        dist_min = d
                        veiculo_mais_prox = outro

        if veiculo_mais_prox:
            self.veiculo_frente = veiculo_mais_prox
            self.distancia_veiculo_frente = dist_min
            self.processar_veiculo_frente(veiculo_mais_prox)
        else:
            self.veiculo_frente = None
            self.distancia_veiculo_frente = float('inf')
            if not self.aguardando_semaforo:
                self.aceleracao_atual = self.acel_base

        # Avaliar troca de faixa apenas se seguro
        if CONFIG.TROCA_FAIXA_ATIVA and not self.em_troca_faixa and not self.em_curva:
            if random.random() < CONFIG.PROB_TENTAR_TROCAR:
                if not self.verificar_colisao_futura(todos_veiculos):
                    self._avaliar_e_tentar_troca(todos_veiculos)

    # ----------------- ATUALIZAÇÃO - MELHORADA -----------------
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

        # Verificação de segurança anti-colisão absoluta
        if todos_veiculos:
            # Verifica colisão atual
            if self.verificar_colisao_completa(todos_veiculos):
                self.velocidade = 0
                self.aceleracao_atual = -self.desac_emer
                self._atualizar_rect()
                return
            
            # Verifica colisão futura apenas se velocidade for significativa
            if self.velocidade > 0.5:
                if self.verificar_colisao_futura(todos_veiculos):
                    # Reduz velocidade gradualmente
                    self.velocidade *= 0.7
                    self.aceleracao_atual = -self.desac
                    
                    # Se ainda há risco, para completamente
                    if self.verificar_colisao_futura(todos_veiculos):
                        self.velocidade = 0
                        self.aceleracao_atual = 0
                        self._atualizar_rect()
                        return

        # Aceleração / limites
        self.velocidade += self.aceleracao_atual * dt
        fator = 1.0
        if malha is not None:
            fator = malha.obter_fator_caos(self)
        self.velocidade = max(self.vmin, min(self.vmax * fator, self.velocidade))

        # Movimento
        if self.em_curva:
            self._atualizar_curva(dt)
            self.distancia_percorrida += self.velocidade * dt
        else:
            # Troca de faixa suave
            if self.em_troca_faixa:
                self.troca_t = min(1.0, self.troca_t + 1.0 / CONFIG.DURACAO_TROCA_FRAMES)
                t = _ease_in_out_sine(self.troca_t)
                lateral = self._lateral_inicio + (self._lateral_fim - self._lateral_inicio) * t
                if self.direcao == Direcao.LESTE:
                    self.posicao[1] = lateral
                else:
                    self.posicao[0] = lateral
                if self.troca_t >= 1.0:
                    self.em_troca_faixa = False
                    if self.faixa_destino is not None:
                        self.faixa_id = self.faixa_destino
                    self.faixa_destino = None
                    self._alinhar_na_faixa()

            # Deslocamento no eixo do movimento
            dx = dy = 0
            if self.direcao == Direcao.NORTE:
                dy = self.velocidade
            elif self.direcao == Direcao.LESTE:
                dx = self.velocidade
            
            # Verificação final antes de mover
            pos_temp = [self.posicao[0] + dx, self.posicao[1] + dy]
            pode_mover = True
            
            if todos_veiculos:
                # Cria rect temporário na nova posição
                if self.direcao == Direcao.NORTE:
                    rect_temp = pygame.Rect(
                        pos_temp[0] - self.largura // 2,
                        pos_temp[1] - self.altura // 2,
                        self.largura, self.altura
                    )
                else:
                    rect_temp = pygame.Rect(
                        pos_temp[0] - self.altura // 2,
                        pos_temp[1] - self.largura // 2,
                        self.altura, self.largura
                    )
                
                # Verifica se movimento é seguro com margem menor
                for outro in todos_veiculos:
                    if outro.id == self.id or not outro.ativo:
                        continue
                    if rect_temp.colliderect(outro.rect.inflate(2, 2)):
                        pode_mover = False
                        break
            
            if pode_mover:
                self.posicao[0] += dx
                self.posicao[1] += dy
                self.distancia_percorrida += math.sqrt(dx ** 2 + dy ** 2)
            else:
                # Reduz velocidade gradualmente em vez de parar completamente
                self.velocidade *= 0.8
                self.aceleracao_atual = -self.desac

            # Manter centro da faixa quando não trocando
            if not self.em_troca_faixa:
                self._alinhar_na_faixa()

        self._atualizar_rect()

        # Fora da tela?
        margem = 100
        if (self.posicao[0] < -margem or self.posicao[0] > CONFIG.LARGURA_TELA + margem or
                self.posicao[1] < -margem or self.posicao[1] > CONFIG.ALTURA_TELA + margem):
            self.ativo = False

    # ----------------- SEMÁFORO -----------------
    def processar_semaforo(
        self,
        semaforo: Semaforo,
        posicao_parada: Tuple[float, float],
        semaforos_cruz: Dict[Direcao, Semaforo],
        centro_cruz: Tuple[float, float]
    ) -> None:
        if not semaforo:
            if not self.veiculo_frente or self.distancia_veiculo_frente > self.dist_reacao:
                self.aceleracao_atual = self.acel_base
            return

        if self.ultimo_semaforo_processado != semaforo:
            self.passou_semaforo = False
            self.ultimo_semaforo_processado = semaforo
            self.pode_passar_amarelo = False

        if self.passou_semaforo:
            if not self.veiculo_frente or self.distancia_veiculo_frente > self.dist_reacao:
                self.aceleracao_atual = self.acel_base
            return

        self.distancia_semaforo = self._calcular_distancia_ate_ponto(posicao_parada)

        if CONFIG.HABILITAR_VIRADAS and self.distancia_semaforo <= CONFIG.ZONA_DECISAO_VIRADA:
            self._decidir_mudanca()

        if self._passou_da_linha(posicao_parada):
            if self.proxima_mudanca and self.proxima_mudanca != self.direcao:
                if self._virada_permitida(semaforos_cruz) and not self.em_curva:
                    self._iniciar_curva(centro_cruz)
            self.passou_semaforo = True
            self.aguardando_semaforo = False
            if not self.veiculo_frente or self.distancia_veiculo_frente > self.dist_reacao:
                self.aceleracao_atual = self.acel_base
            return

        if semaforo.estado == EstadoSemaforo.VERDE:
            if self.proxima_mudanca and self.proxima_mudanca != self.direcao:
                if not self._virada_permitida(semaforos_cruz):
                    # Só para se estiver muito próximo do semáforo
                    if self.distancia_semaforo < CONFIG.DISTANCIA_PARADA_SEMAFORO * 0.5:
                        self._aplicar_frenagem_para_parada(self.distancia_semaforo)
                        self.aguardando_semaforo = True
                        return
            self.aguardando_semaforo = False
            if not self.veiculo_frente or self.distancia_veiculo_frente > self.dist_reacao:
                self.aceleracao_atual = self.acel_base

        elif semaforo.estado == EstadoSemaforo.AMARELO:
            if self.pode_passar_amarelo:
                self.aceleracao_atual = 0
            else:
                tempo = self.distancia_semaforo / max(self.velocidade, 0.1)
                if (tempo < 1.0 and self.velocidade > self.velocidade_desejada * 0.7 and
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

    # ----------------- TROCA DE FAIXA - MELHORADA -----------------
    def _avaliar_e_tentar_troca(self, todos: List['Veiculo']) -> None:
        """Heurística melhorada com verificações de segurança adicionais."""
        if self.distancia_semaforo < CONFIG.DISTANCIA_DETECCAO_SEMAFORO * 0.6:
            return
        if self.veiculo_frente is None:
            return

        # Ganho esperado
        ganho = max(0.0, self.velocidade_desejada - self.veiculo_frente.velocidade)
        if ganho < CONFIG.VANTAGEM_MINIMA:
            return

        candidatos = []
        if self.faixa_id - 1 >= 0:
            candidatos.append(self.faixa_id - 1)
        if self.faixa_id + 1 < CONFIG.NUM_FAIXAS:
            candidatos.append(self.faixa_id + 1)
        random.shuffle(candidatos)

        for alvo in candidatos:
            if self._faixa_livre_para_trocar(todos, alvo):
                # Verificação adicional de segurança
                if not self._verificar_seguranca_troca(todos, alvo):
                    continue
                self._iniciar_troca_para(alvo)
                break

    def _verificar_seguranca_troca(self, todos: List['Veiculo'], faixa_alvo: int) -> bool:
        """Verificação adicional de segurança para troca de faixa."""
        # Simula posição na faixa alvo
        offset_atual = _offset_faixa(self.faixa_id)
        offset_alvo = _offset_faixa(faixa_alvo)
        diferenca = offset_alvo - offset_atual
        
        # Cria rect simulado na faixa alvo
        if self.direcao == Direcao.NORTE:
            pos_simulada = [self.posicao[0] + diferenca, self.posicao[1]]
            rect_simulado = pygame.Rect(
                pos_simulada[0] - self.largura // 2 - 10,
                pos_simulada[1] - self.altura // 2 - 10,
                self.largura + 20,
                self.altura + 20
            )
        else:
            pos_simulada = [self.posicao[0], self.posicao[1] + diferenca]
            rect_simulado = pygame.Rect(
                pos_simulada[0] - self.altura // 2 - 10,
                pos_simulada[1] - self.largura // 2 - 10,
                self.altura + 20,
                self.largura + 20
            )
        
        # Verifica colisão com rect simulado
        for outro in todos:
            if outro.id == self.id or not outro.ativo:
                continue
            if rect_simulado.colliderect(outro.rect.inflate(20, 20)):
                return False
                
        return True

    def _faixa_livre_para_trocar(self, todos: List['Veiculo'], faixa_alvo: int) -> bool:
        """Verificação melhorada de espaço livre na faixa alvo."""
        dist_a_frente = float('inf')
        dist_atras = float('inf')
        vel_atras = 0.0

        for outro in todos:
            if outro.id == self.id or not outro.ativo or outro.direcao != self.direcao:
                continue
            if not self._mesma_rua(outro):
                continue
            
            # Considera veículos na faixa alvo ou em troca para ela
            faixa_outro = getattr(outro, "faixa_id", None)
            faixa_destino_outro = getattr(outro, "faixa_destino", None) if outro.em_troca_faixa else None
            
            if faixa_outro != faixa_alvo and faixa_destino_outro != faixa_alvo:
                continue

            if self.direcao == Direcao.NORTE:
                delta = outro.posicao[1] - self.posicao[1]
                if delta >= 0:
                    dist_a_frente = min(dist_a_frente, delta)
                else:
                    if abs(delta) < dist_atras:
                        dist_atras = abs(delta)
                        vel_atras = outro.velocidade
            else:
                delta = outro.posicao[0] - self.posicao[0]
                if delta >= 0:
                    dist_a_frente = min(dist_a_frente, delta)
                else:
                    if abs(delta) < dist_atras:
                        dist_atras = abs(delta)
                        vel_atras = outro.velocidade

        # Margens de segurança aumentadas
        margem_frente = CONFIG.GAP_FRENTE_TROCA * 1.2
        margem_tras = CONFIG.GAP_TRAS_TROCA * 1.2
        
        if dist_a_frente < margem_frente:
            return False
        if dist_atras < margem_tras and vel_atras > self.velocidade * 0.8:
            return False
            
        return True

    def _iniciar_troca_para(self, faixa_alvo: int) -> None:
        self.em_troca_faixa = True
        self.faixa_destino = faixa_alvo
        self.troca_t = 0.0
        # lateral atual e final
        atual = self._centro_da_faixa()
        self._lateral_inicio = atual
        # troca para o alvo: muda faixa_id temporário para computar alvo
        old = self.faixa_id
        self.faixa_id = faixa_alvo
        alvo = self._centro_da_faixa()
        self._lateral_fim = alvo
        # restaura até finalizar
        self.faixa_id = old

    # ----------------- FOLLOWING / UTIL -----------------
    def processar_veiculo_frente(self, veiculo_frente: 'Veiculo') -> None:
        if not veiculo_frente:
            return
        distancia = self._calcular_distancia_para_veiculo(veiculo_frente)
        
        # Distância crítica - para imediatamente
        if distancia < self.dist_min * 0.6:
            self.velocidade = 0
            self.aceleracao_atual = 0
            return
            
        if distancia < self.dist_reacao:
            velocidade_segura = self._calcular_velocidade_segura(distancia, veiculo_frente.velocidade)
            if self.velocidade > velocidade_segura:
                if distancia < self.dist_min * 1.2:
                    self.aceleracao_atual = -self.desac_emer
                else:
                    self.aceleracao_atual = -self.desac
            elif self.velocidade < velocidade_segura * 0.9:
                self.aceleracao_atual = self.acel_base * 0.5
            else:
                self.aceleracao_atual = 0
        else:
            if not self.aguardando_semaforo:
                self.aceleracao_atual = self.acel_base

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
            # Considera veículos em curva
            if outro.em_curva and outro.curva_destino == self.direcao:
                dx = abs(outro.posicao[0] - self.posicao[0])
                dy = abs(outro.posicao[1] - self.posicao[1])
                return math.sqrt(dx**2 + dy**2) - (self.altura + outro.altura) / 2
            return float('inf')
            
        # Durante troca de faixa, considera ambas as faixas
        if self.em_troca_faixa:
            faixas_minhas = [self.faixa_id]
            if self.faixa_destino is not None:
                faixas_minhas.append(self.faixa_destino)
            
            faixa_outro = getattr(outro, 'faixa_id', -1)
            if faixa_outro not in faixas_minhas:
                if outro.em_troca_faixa and outro.faixa_destino in faixas_minhas:
                    pass  # Considera
                else:
                    return float('inf')
        else:
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

    def _mesma_rua(self, outro: 'Veiculo') -> bool:
        """Mesma rua (ignora faixa). Usa tolerância lateral pela largura total da via."""
        tolerancia = CONFIG.LARGURA_RUA * 0.5
        if self.direcao == Direcao.NORTE:
            return abs(self.posicao[0] - outro.posicao[0]) < tolerancia
        elif self.direcao == Direcao.LESTE:
            return abs(self.posicao[1] - outro.posicao[1]) < tolerancia
        return False

    def _mesma_via(self, outro: 'Veiculo') -> bool:
        """Mesma via E MESMA FAIXA (para car-following e colisão)."""
        if not self._mesma_rua(outro):
            return False
        return getattr(self, "faixa_id", 0) == getattr(outro, "faixa_id", -1)

    def _calcular_velocidade_segura(self, distancia: float, velocidade_lider: float) -> float:
        if distancia < self.dist_min:
            return 0
        tempo_reacao = 1.0
        distancia_segura = self.dist_seguranca + velocidade_lider * tempo_reacao
        if distancia < distancia_segura:
            fator = distancia / distancia_segura
            return max(0.0, velocidade_lider * fator)
        return self.velocidade_desejada

    def _aplicar_frenagem_para_parada(self, distancia: float) -> None:
        if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO:
            self.aceleracao_atual = -self.desac_emer
            self.velocidade_desejada = 0
            if distancia < CONFIG.DISTANCIA_PARADA_SEMAFORO / 2:
                self.velocidade = 0.0
        else:
            if self.velocidade > 0.1:
                desac = (self.velocidade ** 2) / (2 * distancia)
                self.aceleracao_atual = -min(desac, self.desac)
            else:
                self.aceleracao_atual = 0

    # ----------------- DESENHO -----------------
    def desenhar(self, tela: pygame.Surface) -> None:
        if self.direcao == Direcao.NORTE:
            superficie = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
        else:
            superficie = pygame.Surface((self.altura, self.largura), pygame.SRCALPHA)

        pygame.draw.rect(superficie, self.cor, superficie.get_rect(), border_radius=4)

        cor_janela = (200, 220, 255, 180)
        if self.direcao == Direcao.NORTE:
            pygame.draw.rect(superficie, cor_janela,
                             (3, self.altura * 0.7, self.largura - 6, self.altura * 0.25), border_radius=2)
            pygame.draw.rect(superficie, cor_janela,
                             (3, 3, self.largura - 6, self.altura * 0.3), border_radius=2)
        else:
            pygame.draw.rect(superficie, cor_janela,
                             (self.altura * 0.7, 3, self.altura * 0.25, self.largura - 6), border_radius=2)
            pygame.draw.rect(superficie, cor_janela,
                             (3, 3, self.altura * 0.3, self.largura - 6), border_radius=2)

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

        if CONFIG.MOSTRAR_INFO_VEICULO:
            fonte = pygame.font.SysFont('Arial', 10)
            tag = f"{self.tipo.name[:3]} F{self.faixa_id}"
            if self.em_troca_faixa:
                tag += "⇄"
            if self.aguardando_semaforo:
                tag += " 🔴"
            texto = f"V:{self.velocidade:.1f} {tag}"
            tela.blit(fonte.render(texto, True, CONFIG.BRANCO),
                      (self.posicao[0] - 22, self.posicao[1] - 25))