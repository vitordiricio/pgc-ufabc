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
    
    # Contador estático para IDs únicos
    _contador_id = 0
    
    def __init__(self, direcao: Direcao, posicao: Tuple[float, float], id_cruzamento_origem: Tuple[int, int], indice_faixa: int = 0):
        """
        Inicializa um veículo.
        
        Args:
            direcao: Direção do veículo (apenas NORTE ou LESTE em mão única)
            posicao: Posição inicial (x, y) do veículo
            id_cruzamento_origem: ID do cruzamento onde o veículo foi gerado
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
        self.indice_faixa = int(indice_faixa)
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
        
        # Controle de semáforo - MELHORADO
        self.semaforo_proximo = None
        self.ultimo_semaforo_processado = None
        self.distancia_semaforo = float('inf')
        self.pode_passar_amarelo = False
        
        # Controle de colisão
        self.veiculo_frente = None
        self.distancia_veiculo_frente = float('inf')
        
        # Métricas
        self.tempo_viagem = 0
        self.tempo_parado = 0
        self.paradas_totais = 0
        self.distancia_percorrida = 0.0
        
        # Retângulo de colisão
        self._atualizar_rect()
    
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


    # ===============================
    # MOBIL-lite / Gap acceptance
    # ===============================

    def _faixas_por_via(self) -> int:
        return getattr(CONFIG, "FAIXAS_POR_VIA", max(2, int(CONFIG.LARGURA_RUA // CONFIG.LARGURA_FAIXA)))

    def _garantir_campos_lane(self) -> None:
        if not hasattr(self, "indice_faixa"):
            self.indice_faixa = 0
        if not hasattr(self, "cooldown_mudanca_faixa"):
            self.cooldown_mudanca_faixa = 0
        if not hasattr(self, "vmax_local_atual"):
            self.vmax_local_atual = CONFIG.VELOCIDADE_MAX_VEICULO
        if not hasattr(self, "frames_pos_troca"):
            self.frames_pos_troca = 0

    def _via_indice_e_centro(self) -> tuple[int, float]:
        if self.direcao == Direcao.LESTE:
            idx = round((self.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_VERTICAL)
            idx = max(0, min(idx, CONFIG.LINHAS_GRADE - 1))
            yc = CONFIG.POSICAO_INICIAL_Y + idx * CONFIG.ESPACAMENTO_VERTICAL
            return idx, yc
        else:  # NORTE
            idx = round((self.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_HORIZONTAL)
            idx = max(0, min(idx, CONFIG.COLUNAS_GRADE - 1))
            xc = CONFIG.POSICAO_INICIAL_X + idx * CONFIG.ESPACAMENTO_HORIZONTAL
            return idx, xc

    def _coord_centro_faixa(self, idx_faixa: int) -> float:
        """Coordenada lateral (y se LESTE, x se NORTE) do centro da faixa pedida na via atual."""
        _, centro_via = self._via_indice_e_centro()
        return (centro_via - CONFIG.LARGURA_RUA / 2.0
                + CONFIG.LARGURA_FAIXA * (idx_faixa + 0.5))

    def _mesma_via_mesma_faixa(self, outro: 'Veiculo', idx_faixa: int | None = None) -> bool:
        """True se 'outro' está na mesma via (mesmo centro) e na faixa indicada (ou na minha atual)."""
        if outro.direcao != self.direcao:
            return False
        via_self, centro_self = self._via_indice_e_centro()
        via_outro, centro_outro = outro._via_indice_e_centro()
        if via_self != via_outro:
            return False
        # tolerância para lateral
        tol = CONFIG.LARGURA_FAIXA * 0.5
        faixa = self.indice_faixa if idx_faixa is None else idx_faixa
        alvo_lateral = self._coord_centro_faixa(faixa)
        if self.direcao == Direcao.LESTE:
            return abs(outro.posicao[1] - alvo_lateral) < tol
        else:
            return abs(outro.posicao[0] - alvo_lateral) < tol

    def _distancia_1d(self, outro: 'Veiculo') -> float:
        """
        Distância 1D ao longo do eixo de movimento até o centro do 'outro'.
        > 0 => 'outro' está à frente; < 0 => está atrás; INF se não é mesma via (lateralmente muito fora).
        """
        via_ok = abs((self.posicao[1] if self.direcao == Direcao.LESTE else self.posicao[0]) -
                     (outro.posicao[1] if self.direcao == Direcao.LESTE else outro.posicao[0])) <= CONFIG.LARGURA_RUA * 0.6
        if not via_ok:
            return float('inf')
        if self.direcao == Direcao.LESTE:
            return (outro.posicao[0] - self.posicao[0])
        else:
            return (outro.posicao[1] - self.posicao[1])

    def _lider_e_seguidor_na_faixa(self, todos: list['Veiculo'], idx_faixa: int) -> tuple['Veiculo|None','Veiculo|None', float, float]:
        """
        Retorna (lider_ahead, seguidor_behind, dist_ahead, dist_behind) na faixa idx_faixa.
        """
        lider = None
        seguidor = None
        menor_frente = float('inf')
        menor_atras = float('inf')

        for v in todos:
            if not v.ativo or v.id == self.id:
                continue
            if not self._mesma_via_mesma_faixa(v, idx_faixa):
                continue
            d = self._distancia_1d(v)
            if d > 0 and d < menor_frente:
                menor_frente = d
                lider = v
            elif d < 0:
                d_abs = -d
                if d_abs < menor_atras:
                    menor_atras = d_abs
                    seguidor = v

        return lider, seguidor, menor_frente, menor_atras

    def _velocidade_limite_por_lider(self, lider: 'Veiculo|None', dist: float) -> float:
        """
        Estima a velocidade viável imposta pelo líder a 'dist' (metros/pixels).
        Usa o mesmo modelo de car-following simplificado da classe.
        """
        vcap = getattr(self, "vmax_local_atual", CONFIG.VELOCIDADE_MAX_VEICULO)
        if not lider:
            return vcap
        # Se muito longe, praticamente livre
        if dist >= CONFIG.DISTANCIA_REACAO * 1.5:
            return vcap
        # Senão, use a velocidade segura
        vseg = self._calcular_velocidade_segura(dist, lider.velocidade)
        return max(0.0, min(vcap, vseg))

    def _dist_prox_cruzamento(self) -> float:
        """Distância (ao longo do eixo de movimento) até o próximo cruzamento à frente."""
        if self.direcao == Direcao.LESTE:
            col_atual = math.floor((self.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_HORIZONTAL)
            prox_cx = CONFIG.POSICAO_INICIAL_X + (col_atual + 1) * CONFIG.ESPACAMENTO_HORIZONTAL
            return prox_cx - self.posicao[0]
        else:
            lin_atual = math.floor((self.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_VERTICAL)
            prox_cy = CONFIG.POSICAO_INICIAL_Y + (lin_atual + 1) * CONFIG.ESPACAMENTO_VERTICAL
            return prox_cy - self.posicao[1]

    def pode_mudar_faixa(self, todos: list['Veiculo'], delta: int) -> int | None:
        """
        Decide se a mudança para a faixa (indice_faixa + delta) é aceitável, retornando o índice alvo;
        caso contrário, retorna None.
        Critérios: gap seguro (à frente e atrás) + ganho de velocidade individual + cooldown + penalidade perto de cruzamento.
        """
        self._garantir_campos_lane()

        alvo = self.indice_faixa + delta
        if alvo < 0 or alvo >= self._faixas_por_via():
            return None

        # Cooldown para evitar oscilação
        cooldown_frames = getattr(CONFIG, "COOLDOWN_MUDANCA_FAIXA", 60)
        if self.cooldown_mudanca_faixa > 0:
            return None

        # Penalidade perto do cruzamento
        limite_cruz = getattr(CONFIG, "DIST_MIN_TROCA_PERTO_CRUZAMENTO", max(80, int(CONFIG.LARGURA_RUA * 1.5)))
        if self._dist_prox_cruzamento() < limite_cruz:
            return None

        # Líder/seguidor na faixa atual (para estimar minha velocidade "capada")
        lider_atual, _, dist_atual, _ = self._lider_e_seguidor_na_faixa(todos, self.indice_faixa)
        vcap_atual = self._velocidade_limite_por_lider(lider_atual, dist_atual)

        # Líder/seguidor na faixa alvo (gap acceptance)
        lider_alvo, seguidor_alvo, dist_ahead, dist_behind = self._lider_e_seguidor_na_faixa(todos, alvo)

        # Requisitos de segurança (gap)
        tr = 1.0  # tempo de reação (s)
        # à frente: distância deve cobrir headway + pequena margem proporcional ao delta de velocidade
        v_lider = lider_alvo.velocidade if lider_alvo else self.vmax_local_atual
        req_ahead = CONFIG.DISTANCIA_SEGURANCA + max(0.0, self.velocidade - v_lider) * tr
        safe_ahead = (dist_ahead == float('inf')) or (dist_ahead > req_ahead)

        # atrás: seguidor precisa ter espaço para reagir a mim
        if seguidor_alvo:
            v_seg = seguidor_alvo.velocidade
        else:
            v_seg = 0.0
        req_behind = CONFIG.DISTANCIA_SEGURANCA + max(0.0, v_seg - self.velocidade) * tr
        safe_behind = (dist_behind == float('inf')) or (dist_behind > req_behind)

        if not (safe_ahead and safe_behind):
            return None

        # Ganho de velocidade individual: só troca se a faixa alvo permitir ir mais rápido
        vcap_alvo = self._velocidade_limite_por_lider(lider_alvo, dist_ahead)
        ganho_min = getattr(CONFIG, "GANHO_MIN_MUDANCA_FAIXA", 0.2)
        if vcap_alvo <= vcap_atual + ganho_min:
            return None

        return alvo

    def _aplicar_mudanca_faixa(self, idx_alvo: int) -> None:
        lateral = self._coord_centro_faixa(idx_alvo)
        if self.direcao == Direcao.LESTE:
            self.posicao[1] = lateral
        else:
            self.posicao[0] = lateral

        self.indice_faixa = idx_alvo
        self._atualizar_rect()
        self.cooldown_mudanca_faixa = getattr(CONFIG, "COOLDOWN_MUDANCA_FAIXA", 60)
        self.frames_pos_troca = getattr(CONFIG, "GRACE_FRAMES_LANE_CHANGE", 3)

    def resetar_controle_semaforo(self, novo_cruzamento_id: Optional[Tuple[int, int]] = None) -> None:
        """
        Reseta o controle de semáforo quando o veículo muda de cruzamento.
        
        Args:
            novo_cruzamento_id: ID do novo cruzamento (opcional)
        """
        if novo_cruzamento_id and novo_cruzamento_id != self.id_cruzamento_atual:
            self.id_cruzamento_atual = novo_cruzamento_id
            self.passou_semaforo = False
            self.aguardando_semaforo = False
            self.pode_passar_amarelo = False
            self.semaforo_proximo = None
            self.distancia_semaforo = float('inf')

    def verificar_colisao_futura(self, todos_veiculos: List['Veiculo']) -> bool:
        # posição futura (centro)
        dx, dy = 0.0, 0.0
        adiant = CONFIG.DISTANCIA_MIN_VEICULO / 2
        if self.direcao == Direcao.NORTE:
            dy = self.velocidade + adiant
        elif self.direcao == Direcao.LESTE:
            dx = self.velocidade + adiant
        pos_fut = [self.posicao[0] + dx, self.posicao[1] + dy]

        # rect futuro com mesma orientação
        if self.direcao == Direcao.NORTE:
            rect_fut = pygame.Rect(
                pos_fut[0] - self.largura // 2,
                pos_fut[1] - self.altura // 2,
                self.largura,
                self.altura
            )
        else:
            rect_fut = pygame.Rect(
                pos_fut[0] - self.altura // 2,
                pos_fut[1] - self.largura // 2,
                self.altura,
                self.largura
            )

        # tolerance lateral mínima e somente MESMA FAIXA
        for outro in todos_veiculos:
            if not outro.ativo or outro.id == self.id:
                continue
            # Checa mesma via & MESMA FAIXA explicitamente
            if not self._mesma_via_mesma_faixa(outro, self.indice_faixa):
                continue

            # Se o outro está bem atrás no eixo de movimento, não conta
            dalong = self._distancia_1d(outro)  # >0 = à frente; <0 = atrás
            if dalong < -max(self.altura, self.largura) * 0.8:
                continue

            # Inflar muito pouco para evitar falso positivo lateral
            # E reduzir ainda mais nos frames de "graça" pós-troca
            margem = 4 if self.frames_pos_troca == 0 else 1
            rect_outro = outro.rect.inflate(margem, margem)

            if rect_fut.colliderect(rect_outro):
                return True

        return False

    def processar_todos_veiculos(self, todos_veiculos: List['Veiculo']) -> None:
        """
        Processa interação com todos os veículos, não apenas os do cruzamento atual.
        + MOBIL-lite: avalia mudança de faixa por gap acceptance e ganho individual.
        """
        self._garantir_campos_lane()

        veiculo_mais_proximo = None
        distancia_minima = float('inf')

        for outro in todos_veiculos:
            if outro.id == self.id or not outro.ativo:
                continue

            # Verifica se estão na mesma via e direção (mesma faixa atual para car-following)
            if self.direcao != outro.direcao or not self._mesma_via(outro):
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

        # Processa o veículo mais próximo à frente (mesma faixa)
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

        # =============== Decisão de mudança de faixa (MOBIL-lite) ===============
        # Tenta esquerda/direita (ordem pode influenciar; aqui preferimos a esquerda primeiro)
        candidatos = []
        for delta in (-1, 1):
            alvo = self.pode_mudar_faixa(todos_veiculos, delta)
            if alvo is not None:
                candidatos.append(alvo)

        if candidatos:
            # Se houver 2 candidatos, escolha o que dá maior vcap (mais ganho)
            melhor = None
            melhor_vcap = -1.0
            for idx_alvo in candidatos:
                lider, _, dist_ahead, _ = self._lider_e_seguidor_na_faixa(todos_veiculos, idx_alvo)
                vcap = self._velocidade_limite_por_lider(lider, dist_ahead)
                if vcap > melhor_vcap:
                    melhor_vcap = vcap
                    melhor = idx_alvo

            # Aplica a troca (snap para o centro)
            if melhor is not None:
                self._aplicar_mudanca_faixa(melhor)

    # troque a assinatura atual por esta
    def atualizar(self, dt: float = 1.0, todos_veiculos: List['Veiculo'] = None, malha=None) -> None:
        # NOVO: lane fields + cooldown/grace
        self._garantir_campos_lane()
        if self.cooldown_mudanca_faixa > 0:
            self.cooldown_mudanca_faixa -= 1
        if self.frames_pos_troca > 0:
            self.frames_pos_troca -= 1

        # métricas
        self.tempo_viagem += dt
        if self.velocidade < 0.1:
            self.tempo_parado += dt
            if not self.parado:
                self.paradas_totais += 1
            self.parado = True
        else:
            self.parado = False

        # aceleração
        self.velocidade += self.aceleracao_atual * dt

        # limite local (CAOS)
        fator = malha.obter_fator_caos(self) if malha is not None else 1.0
        vmax_local = CONFIG.VELOCIDADE_MAX_VEICULO * fator
        self.vmax_local_atual = vmax_local
        self.velocidade = max(CONFIG.VELOCIDADE_MIN_VEICULO, min(vmax_local, self.velocidade))

        # colisão futura
        if todos_veiculos and self.velocidade > 0:
            if self.verificar_colisao_futura(todos_veiculos):
                self.velocidade = 0
                self.aceleracao_atual = 0
                self._atualizar_rect()
                return

        # movimento
        dx, dy = 0.0, 0.0
        if self.direcao == Direcao.NORTE:
            dy = self.velocidade
        elif self.direcao == Direcao.LESTE:
            dx = self.velocidade

        self.posicao[0] += dx
        self.posicao[1] += dy
        self.distancia_percorrida += math.sqrt(dx ** 2 + dy ** 2)
        self._atualizar_rect()

        # NOVO: saída da tela com margens direcionais (lateral mais tolerante)
        margem_long = 100
        margem_lat = max(CONFIG.LARGURA_RUA, 80)
        if self.direcao == Direcao.LESTE:
            if (self.posicao[0] < -margem_long or self.posicao[0] > CONFIG.LARGURA_TELA + margem_long or
                    self.posicao[1] < -margem_lat or self.posicao[1] > CONFIG.ALTURA_TELA + margem_lat):
                self.ativo = False
        else:  # NORTE
            if (self.posicao[1] < -margem_long or self.posicao[1] > CONFIG.ALTURA_TELA + margem_long or
                    self.posicao[0] < -margem_lat or self.posicao[0] > CONFIG.LARGURA_TELA + margem_lat):
                self.ativo = False

    def processar_semaforo(self, semaforo: Semaforo, posicao_parada: Tuple[float, float]) -> None:
        """
        Processa a reação do veículo ao semáforo.

        Args:
            semaforo: Semáforo a ser processado
            posicao_parada: Posição onde o veículo deve parar
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
        Processa a reação a um veículo à frente.
        
        Args:
            veiculo_frente: Veículo detectado à frente
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
        margem = 5
        if self.direcao == Direcao.NORTE:
            # Norte→Sul: passou se Y atual > Y do ponto
            return self.posicao[1] > ponto[1] + margem
        elif self.direcao == Direcao.LESTE:
            # Leste→Oeste: passou se X atual > X do ponto
            return self.posicao[0] > ponto[0] + margem
        return False
    
    def _calcular_distancia_para_veiculo(self, outro: 'Veiculo') -> float:
        """Calcula a distância até outro veículo - MÃO ÚNICA."""
        # Em vias de mão única, todos os veículos na mesma via vão na mesma direção
        if self.direcao != outro.direcao:
            return float('inf')
        
        # Verifica se estão na mesma via
        if not self._mesma_via(outro):
            return float('inf')
        
        # Calcula distância centro a centro
        dx = outro.posicao[0] - self.posicao[0]
        dy = outro.posicao[1] - self.posicao[1]
        
        # Ajusta pela direção e dimensões dos veículos
        if self.direcao == Direcao.NORTE:
            if dy > 0:  # Outro está à frente
                return max(0, dy - (self.altura + outro.altura) / 2)
        elif self.direcao == Direcao.LESTE:
            if dx > 0:  # Outro está à frente
                return max(0, dx - (self.altura + outro.altura) / 2)
        
        return float('inf')
    
    def _mesma_via(self, outro: 'Veiculo') -> bool:
        """
        Dois veículos compartilham a mesma via se:
        - têm a mesma DIREÇÃO,
        - estão na MESMA LINHA (horizontais) ou MESMA COLUNA (verticais) da grade,
        - e têm o MESMO indice_faixa.
        """
        if self.direcao != outro.direcao:
            return False
        if self.indice_faixa != outro.indice_faixa:
            return False

        # Identifica linha/coluna da via
        if self.direcao == Direcao.LESTE:
            linha_self = round((self.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_VERTICAL)
            linha_out = round((outro.posicao[1] - CONFIG.POSICAO_INICIAL_Y) / CONFIG.ESPACAMENTO_VERTICAL)
            return linha_self == linha_out
        else:  # Direcao.NORTE
            col_self = round((self.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_HORIZONTAL)
            col_out  = round((outro.posicao[0] - CONFIG.POSICAO_INICIAL_X) / CONFIG.ESPACAMENTO_HORIZONTAL)
            return col_self == col_out

    
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
    