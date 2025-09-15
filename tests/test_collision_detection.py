"""
Testes para detecção de colisões no simulador de tráfego.
Estes testes ajudam a entender por que veículos estão colidindo e congelando.
"""
import pytest
import pygame
import math
from unittest.mock import Mock
import sys
import os

# Adiciona o diretório raiz ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from veiculo import Veiculo
from configuracao import CONFIG, Direcao, TipoVeiculo
from semaforo import Semaforo


class TestCollisionDetection:
    """Testa a detecção de colisões entre veículos."""
    
    def setup_method(self):
        """Configuração inicial para cada teste."""
        pygame.init()
        
    def teardown_method(self):
        """Limpeza após cada teste."""
        pygame.quit()
    
    def test_vehicle_creation(self):
        """Testa se veículos são criados corretamente."""
        veiculo = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        assert veiculo.direcao == Direcao.NORTE
        assert veiculo.posicao == [100, 100]
        assert veiculo.ativo == True
        assert veiculo.velocidade == 0.0
    
    def test_vehicle_rect_calculation(self):
        """Testa se o retângulo de colisão é calculado corretamente."""
        veiculo = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo._atualizar_rect()
        
        # Para direção NORTE, altura deve ser maior que largura
        assert veiculo.rect.width == veiculo.largura
        assert veiculo.rect.height == veiculo.altura
        assert veiculo.rect.centerx == 100
        assert veiculo.rect.centery == 100
    
    def test_vehicle_rect_east_direction(self):
        """Testa retângulo para veículo indo para LESTE."""
        veiculo = Veiculo(Direcao.LESTE, (100, 100), (0, 0))
        veiculo._atualizar_rect()
        
        # Para direção LESTE, largura deve ser maior que altura (veículo rotacionado)
        assert veiculo.rect.width == veiculo.altura  # altura vira largura
        assert veiculo.rect.height == veiculo.largura  # largura vira altura
    
    def test_collision_detection_same_position(self):
        """Testa detecção de colisão quando veículos estão na mesma posição."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        assert veiculo1.verificar_colisao_completa([veiculo2]) == True
        assert veiculo2.verificar_colisao_completa([veiculo1]) == True
    
    def test_collision_detection_close_vehicles(self):
        """Testa detecção de colisão quando veículos estão muito próximos."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 120), (0, 0))  # 20 pixels de distância
        
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        # Com margem de segurança de 25, deve detectar colisão
        assert veiculo1.verificar_colisao_completa([veiculo2]) == True
    
    def test_collision_detection_safe_distance(self):
        """Testa que veículos com distância segura não colidem."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 200), (0, 0))  # 100 pixels de distância
        
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        assert veiculo1.verificar_colisao_completa([veiculo2]) == False
    
    def test_future_collision_detection(self):
        """Testa detecção de colisão futura."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 150), (0, 0))
        
        # Define velocidade para veículo 1
        veiculo1.velocidade = 2.0
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        # Deve detectar colisão futura
        assert veiculo1.verificar_colisao_futura([veiculo2]) == True
    
    def test_vehicle_movement_safety(self):
        """Testa se movimento de veículo é seguro."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 120), (0, 0))
        
        veiculo1.velocidade = 1.0
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        # Simula movimento
        pos_original = veiculo1.posicao.copy()
        veiculo1.posicao[1] += veiculo1.velocidade
        
        # Verifica se movimento causaria colisão
        veiculo1._atualizar_rect()
        colisao = veiculo1.verificar_colisao_completa([veiculo2])
        
        # Restaura posição original
        veiculo1.posicao = pos_original
        veiculo1._atualizar_rect()
        
        assert colisao == True  # Deve detectar colisão
    
    def test_vehicle_following_behavior(self):
        """Testa comportamento de seguimento de veículos."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 150), (0, 0))
        
        veiculo1.velocidade = 1.0
        veiculo2.velocidade = 0.5
        
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        # Processa veículo 1 com veículo 2 na frente
        veiculo1.processar_todos_veiculos([veiculo2])
        
        # Deve detectar veículo na frente
        assert veiculo1.veiculo_frente == veiculo2
        assert veiculo1.distancia_veiculo_frente < float('inf')
    
    def test_vehicle_lane_changing_safety(self):
        """Testa segurança na troca de faixa."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo1.faixa_id = 0
        
        veiculo2 = Veiculo(Direcao.NORTE, (126, 100), (0, 0))  # Faixa 1
        veiculo2.faixa_id = 1
        
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        # Tenta trocar para faixa 1 onde está veículo 2
        pode_trocar = veiculo1._faixa_livre_para_trocar([veiculo2], 1)
        
        assert pode_trocar == False  # Não deve poder trocar
    
    def test_vehicle_curve_collision(self):
        """Testa detecção de colisão durante curvas."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.LESTE, (120, 120), (0, 0))
        
        # Simula veículo 1 virando para LESTE
        veiculo1.em_curva = True
        veiculo1.curva_origem = Direcao.NORTE
        veiculo1.curva_destino = Direcao.LESTE
        veiculo1.curva_centro = (100, 100)
        veiculo1.curva_t = 0.5
        
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        # Deve detectar veículo próximo durante curva
        proximo = veiculo1.detectar_veiculo_proximo([veiculo2], raio=60)
        assert proximo == veiculo2
    
    def test_vehicle_spawn_safety(self):
        """Testa se spawn de veículos é seguro."""
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


class TestVehicleMovement:
    """Testa o movimento de veículos e prevenção de colisões."""
    
    def setup_method(self):
        """Configuração inicial para cada teste."""
        pygame.init()
    
    def teardown_method(self):
        """Limpeza após cada teste."""
        pygame.quit()
    
    def test_vehicle_velocity_limits(self):
        """Testa se velocidades são limitadas corretamente."""
        veiculo = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        
        # Testa velocidade mínima
        veiculo.velocidade = -1.0
        veiculo.atualizar(1.0, [])
        assert veiculo.velocidade >= veiculo.vmin
        
        # Testa velocidade máxima
        veiculo.velocidade = 10.0
        veiculo.atualizar(1.0, [])
        assert veiculo.velocidade <= veiculo.vmax
    
    def test_vehicle_acceleration(self):
        """Testa aceleração de veículos."""
        veiculo = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo.aceleracao_atual = 0.1
        
        velocidade_inicial = veiculo.velocidade
        veiculo.atualizar(1.0, [])
        
        assert veiculo.velocidade > velocidade_inicial
    
    def test_vehicle_emergency_braking(self):
        """Testa frenagem de emergência."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 110), (0, 0))  # Muito próximo
        
        veiculo1.velocidade = 1.0
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        # Processa colisão
        veiculo1.processar_todos_veiculos([veiculo2])
        
        # Deve aplicar frenagem de emergência
        assert veiculo1.aceleracao_atual < 0
    
    def test_vehicle_stop_on_collision(self):
        """Testa se veículo para completamente em caso de colisão."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))  # Mesma posição
        
        veiculo1.velocidade = 1.0
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        # Atualiza com colisão
        veiculo1.atualizar(1.0, [veiculo2])
        
        # Deve parar completamente
        assert veiculo1.velocidade == 0
        assert veiculo1.aceleracao_atual <= 0


class TestCollisionScenarios:
    """Testa cenários específicos de colisão."""
    
    def setup_method(self):
        """Configuração inicial para cada teste."""
        pygame.init()
    
    def teardown_method(self):
        """Limpeza após cada teste."""
        pygame.quit()
    
    def test_multiple_vehicles_collision(self):
        """Testa colisão com múltiplos veículos."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo2 = Veiculo(Direcao.NORTE, (100, 120), (0, 0))
        veiculo3 = Veiculo(Direcao.NORTE, (100, 140), (0, 0))
        
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        veiculo3._atualizar_rect()
        
        # Veículo 1 deve detectar colisão com veículo 2
        assert veiculo1.verificar_colisao_completa([veiculo2, veiculo3]) == True
        
        # Veículo 2 deve detectar colisão com veículo 1
        assert veiculo2.verificar_colisao_completa([veiculo1, veiculo3]) == True
    
    def test_different_directions_collision(self):
        """Testa colisão entre veículos de direções diferentes."""
        veiculo_norte = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo_leste = Veiculo(Direcao.LESTE, (100, 100), (0, 0))
        
        veiculo_norte._atualizar_rect()
        veiculo_leste._atualizar_rect()
        
        # Deve detectar colisão mesmo com direções diferentes
        assert veiculo_norte.verificar_colisao_completa([veiculo_leste]) == True
    
    def test_vehicle_following_chain(self):
        """Testa cadeia de veículos seguindo uns aos outros."""
        veiculos = []
        for i in range(5):
            veiculo = Veiculo(Direcao.NORTE, (100, 100 + i * 60), (0, 0))
            veiculo.velocidade = 1.0
            veiculo._atualizar_rect()
            veiculos.append(veiculo)
        
        # Cada veículo deve detectar o da frente
        for i in range(len(veiculos) - 1):
            veiculo_atual = veiculos[i]
            veiculo_atual.processar_todos_veiculos(veiculos)
            assert veiculo_atual.veiculo_frente == veiculos[i + 1]
    
    def test_vehicle_lane_changing_collision(self):
        """Testa colisão durante troca de faixa."""
        veiculo1 = Veiculo(Direcao.NORTE, (100, 100), (0, 0))
        veiculo1.faixa_id = 0
        veiculo1.em_troca_faixa = True
        veiculo1.faixa_destino = 1
        
        veiculo2 = Veiculo(Direcao.NORTE, (126, 100), (0, 0))  # Faixa 1
        veiculo2.faixa_id = 1
        
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        # Deve detectar colisão durante troca de faixa
        assert veiculo1.verificar_colisao_completa([veiculo2]) == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
