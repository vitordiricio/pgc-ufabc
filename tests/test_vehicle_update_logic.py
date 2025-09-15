"""
Testes específicos para a lógica de atualização de veículos.
Foca em identificar onde veículos podem colidir ou congelar.
"""
import pytest
import pygame
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from veiculo import Veiculo
from configuracao import CONFIG, Direcao, TipoVeiculo


class TestVehicleUpdateLogic:
    """Testa a lógica de atualização de veículos."""
    
    def setup_method(self):
        """Configuração inicial para cada teste."""
        pygame.init()
    
    def teardown_method(self):
        """Limpeza após cada teste."""
        pygame.quit()
    
    def test_vehicle_update_without_collision_check(self):
        """Testa atualização de veículo sem verificação de colisão."""
        veiculo = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo.velocidade = 1.0
        veiculo.aceleracao_atual = 0.1
        
        posicao_inicial = veiculo.posicao.copy()
        veiculo.atualizar(1.0, [])  # Sem outros veículos
        
        # Deve mover
        assert veiculo.posicao[1] > posicao_inicial[1]  # Movendo para baixo (NORTE)
        assert veiculo.velocidade > 0
    
    def test_vehicle_update_with_collision_detection(self):
        """Testa atualização com detecção de colisão."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 120), (0, 0))
        
        veiculo1.velocidade = 1.0
        veiculo1.aceleracao_atual = 0.1
        
        posicao_inicial = veiculo1.posicao.copy()
        
        # Atualiza com verificação de colisão
        veiculo1.atualizar(1.0, [veiculo2])
        
        # Deve detectar colisão e parar
        assert veiculo1.velocidade == 0
        assert veiculo1.posicao == posicao_inicial  # Não deve mover
    
    def test_vehicle_future_collision_prevention(self):
        """Testa prevenção de colisão futura."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 150), (0, 0))
        
        veiculo1.velocidade = 2.0  # Velocidade alta
        veiculo1.aceleracao_atual = 0.1
        
        # Deve detectar colisão futura e reduzir velocidade
        veiculo1.atualizar(1.0, [veiculo2])
        
        # Deve ter reduzido velocidade
        assert veiculo1.velocidade < 2.0
    
    def test_vehicle_emergency_braking(self):
        """Testa frenagem de emergência."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 105), (0, 0))  # Muito próximo
        
        veiculo1.velocidade = 1.0
        veiculo1.aceleracao_atual = 0.1
        
        # Deve aplicar frenagem de emergência
        veiculo1.atualizar(1.0, [veiculo2])
        
        assert veiculo1.velocidade == 0
        assert veiculo1.aceleracao_atual <= 0
    
    def test_vehicle_movement_safety_check(self):
        """Testa verificação de segurança antes do movimento."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 120), (0, 0))
        
        veiculo1.velocidade = 1.0
        veiculo1.aceleracao_atual = 0.1
        
        # Simula movimento manual
        dx = dy = 0
        if veiculo1.direcao == Direcao.NORTE:
            dy = veiculo1.velocidade
        
        pos_temp = [veiculo1.posicao[0] + dx, veiculo1.posicao[1] + dy]
        
        # Verifica se movimento é seguro
        pode_mover = True
        if veiculo1.direcao == Direcao.NORTE:
            rect_temp = pygame.Rect(
                pos_temp[0] - veiculo1.largura // 2,
                pos_temp[1] - veiculo1.altura // 2,
                veiculo1.largura, veiculo1.altura
            )
        else:
            rect_temp = pygame.Rect(
                pos_temp[0] - veiculo1.altura // 2,
                pos_temp[1] - veiculo1.largura // 2,
                veiculo1.altura, veiculo1.largura
            )
        
        # Verifica colisão com veículo 2
        veiculo2._atualizar_rect()
        if rect_temp.colliderect(veiculo2.rect.inflate(2, 2)):
            pode_mover = False
        
        # Com veículo próximo, não deve poder mover
        assert pode_mover == False
    
    def test_vehicle_velocity_reduction_on_collision_risk(self):
        """Testa redução de velocidade quando há risco de colisão."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 130), (0, 0))
        
        veiculo1.velocidade = 1.0
        veiculo1.aceleracao_atual = 0.1
        
        # Simula múltiplas atualizações
        for i in range(5):
            veiculo1.atualizar(1.0, [veiculo2])
            print(f"Frame {i+1}: posição {veiculo1.posicao}, velocidade {veiculo1.velocidade}")
        
        # Deve ter reduzido velocidade devido ao risco de colisão
        assert veiculo1.velocidade < 1.0
    
    def test_vehicle_following_behavior(self):
        """Testa comportamento de seguimento de veículos."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 150), (0, 0))
        
        veiculo1.velocidade = 1.0
        veiculo2.velocidade = 0.5
        
        # Processa veículo 1
        veiculo1.processar_todos_veiculos([veiculo2])
        
        # Deve detectar veículo na frente
        assert veiculo1.veiculo_frente == veiculo2
        assert veiculo1.distancia_veiculo_frente < float('inf')
        
        # Deve ajustar aceleração baseada no veículo da frente
        veiculo1.atualizar(1.0, [veiculo2])
        
        # Deve ter aceleração negativa (frenagem)
        assert veiculo1.aceleracao_atual < 0
    
    def test_vehicle_lane_changing_safety(self):
        """Testa segurança na troca de faixa."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo1.faixa_id = 0
        
        veiculo2 = Veiculo(Direcao.NORTE, (126, 100), (0, 0))  # Faixa 1
        veiculo2.faixa_id = 1
        
        # Tenta trocar para faixa 1
        pode_trocar = veiculo1._faixa_livre_para_trocar([veiculo2], 1)
        
        # Não deve poder trocar com veículo na faixa alvo
        assert pode_trocar == False
        
        # Verifica segurança adicional
        seguranca = veiculo1._verificar_seguranca_troca([veiculo2], 1)
        assert seguranca == False
    
    def test_vehicle_curve_collision_detection(self):
        """Testa detecção de colisão durante curvas."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.LESTE, (120, 120), (0, 0))
        
        # Simula veículo 1 virando
        veiculo1.em_curva = True
        veiculo1.curva_origem = Direcao.NORTE
        veiculo1.curva_destino = Direcao.LESTE
        veiculo1.curva_centro = (100, 100)
        veiculo1.curva_t = 0.5
        
        # Deve detectar veículo próximo durante curva
        proximo = veiculo1.detectar_veiculo_proximo([veiculo2], raio=60)
        assert proximo == veiculo2
        
        # Deve ajustar velocidade
        veiculo1.velocidade = 1.0
        veiculo1.atualizar(1.0, [veiculo2])
        
        # Deve ter reduzido velocidade
        assert veiculo1.velocidade < 1.0
    
    def test_vehicle_spawn_collision_prevention(self):
        """Testa prevenção de colisão no spawn."""
        from cruzamento import Cruzamento
        from semaforo import GerenciadorSemaforos
        
        gerenciador = GerenciadorSemaforos()
        cruzamento = Cruzamento((200, 200), (0, 0), gerenciador, None)
        
        # Cria veículo existente
        veiculo_existente = Veiculo(Direcao.NORTE, (200, 50), (0, 0))
        veiculo_existente.faixa_id = 0
        
        # Verifica se há espaço para gerar novo veículo
        posicao_spawn = cruzamento._posicao_spawn_por_faixa(Direcao.NORTE, 0)
        tem_espaco = cruzamento._tem_espaco_para_gerar(Direcao.NORTE, posicao_spawn, TipoVeiculo.CARRO)
        
        # Com veículo muito próximo, não deve ter espaço
        assert tem_espaco == False
        
        # Move veículo para longe
        veiculo_existente.posicao[1] = 200
        
        # Agora deve ter espaço
        tem_espaco = cruzamento._tem_espaco_para_gerar(Direcao.NORTE, posicao_spawn, TipoVeiculo.CARRO)
        assert tem_espaco == True


class TestCollisionPrevention:
    """Testa prevenção de colisões em cenários específicos."""
    
    def setup_method(self):
        """Configuração inicial para cada teste."""
        pygame.init()
    
    def teardown_method(self):
        """Limpeza após cada teste."""
        pygame.quit()
    
    def test_chain_reaction_prevention(self):
        """Testa prevenção de reação em cadeia."""
        veiculos = []
        for i in range(3):
            veiculo = Veiculo(Direcao.NORTE, (100, 100 + i * 30), (0, 0))
            veiculo.velocidade = 1.0
            veiculo.aceleracao_atual = 0.1
            veiculo._atualizar_rect()
            veiculos.append(veiculo)
        
        # Atualiza todos os veículos
        for veiculo in veiculos:
            veiculo.atualizar(1.0, veiculos)
        
        # Verifica se não há colisões
        for i, veiculo1 in enumerate(veiculos):
            for j, veiculo2 in enumerate(veiculos[i+1:], i+1):
                colisao = veiculo1.verificar_colisao_completa([veiculo2])
                assert colisao == False, f"Colisão entre veículos {i} e {j}"
    
    def test_high_density_safety(self):
        """Testa segurança com alta densidade de veículos."""
        veiculos = []
        for i in range(10):
            veiculo = Veiculo(Direcao.NORTE, (100, 100 + i * 40), (0, 0))
            veiculo.velocidade = 0.5
            veiculo.aceleracao_atual = 0.05
            veiculo._atualizar_rect()
            veiculos.append(veiculo)
        
        # Atualiza múltiplas vezes
        for frame in range(10):
            for veiculo in veiculos:
                veiculo.atualizar(1.0, veiculos)
        
        # Verifica se não há colisões
        for i, veiculo1 in enumerate(veiculos):
            for j, veiculo2 in enumerate(veiculos[i+1:], i+1):
                colisao = veiculo1.verificar_colisao_completa([veiculo2])
                assert colisao == False, f"Colisão entre veículos {i} e {j} no frame {frame}"
    
    def test_different_directions_safety(self):
        """Testa segurança entre veículos de direções diferentes."""
        veiculo_norte = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo_leste = Veiculo(Direcao.LESTE, (100, 100), (0, 0))
        
        veiculo_norte.velocidade = 1.0
        veiculo_leste.velocidade = 1.0
        
        # Deve detectar colisão imediatamente
        colisao = veiculo_norte.verificar_colisao_completa([veiculo_leste])
        assert colisao == True
        
        # Deve parar ambos os veículos
        veiculo_norte.atualizar(1.0, [veiculo_leste])
        veiculo_leste.atualizar(1.0, [veiculo_norte])
        
        assert veiculo_norte.velocidade == 0
        assert veiculo_leste.velocidade == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
