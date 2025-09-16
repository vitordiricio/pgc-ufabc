"""
Testes unitários para o sistema de colisão de veículos.
Testa se os veículos se movem SOMENTE quando há espaço disponível.
"""
import pytest
import pygame
import sys
import os
from unittest.mock import Mock, patch

# Adiciona o diretório raiz ao path para importar os módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from veiculo import Veiculo
from configuracao import CONFIG, Direcao
from fisica_veiculo import FisicaVeiculo
from sistema_colisao import SistemaColisao


class TestColisaoVeiculos:
    """Testes para verificar se os veículos respeitam as regras de colisão."""
    
    def setup_method(self):
        """Configuração inicial para cada teste."""
        # Inicializa pygame para os testes
        pygame.init()
        
        # Reset do contador de IDs para testes consistentes
        Veiculo._contador_id = 0
    
    def teardown_method(self):
        """Limpeza após cada teste."""
        pygame.quit()
    
    def criar_veiculo_norte(self, posicao=(100, 100)):
        """Cria um veículo movendo para o Norte (vertical)."""
        return Veiculo(Direcao.NORTE, posicao, (0, 0))
    
    def criar_veiculo_leste(self, posicao=(100, 100)):
        """Cria um veículo movendo para o Leste (horizontal)."""
        return Veiculo(Direcao.LESTE, posicao, (0, 0))
    
    def test_veiculo_nao_deve_mover_com_obstaculo_muito_proximo(self):
        """Testa se veículo para quando há obstáculo muito próximo."""
        # Cria dois veículos na mesma via com distância mínima
        veiculo1 = self.criar_veiculo_norte((100, 100))
        veiculo2 = self.criar_veiculo_norte((100, 100 + CONFIG.DISTANCIA_MIN_VEICULO - 10))
        
        # Define velocidades para ambos
        veiculo1.fisica.velocidade = 1.0
        veiculo2.fisica.velocidade = 0.5
        
        # Lista de todos os veículos
        todos_veiculos = [veiculo1, veiculo2]
        
        # Simula atualização do veículo1
        posicao_inicial = veiculo1.posicao.copy()
        veiculo1.atualizar(1.0, todos_veiculos)
        
        # Verifica se o veículo1 parou devido à colisão
        assert veiculo1.fisica.velocidade == 0.0, "Veículo deveria ter parado devido à proximidade"
        assert veiculo1.posicao == posicao_inicial, "Veículo não deveria ter se movido"
    
    def test_veiculo_deve_mover_quando_nao_há_obstaculos(self):
        """Testa se veículo se move quando não há obstáculos."""
        veiculo = self.criar_veiculo_norte((100, 100))
        veiculo.fisica.velocidade = 1.0
        
        posicao_inicial = veiculo.posicao.copy()
        veiculo.atualizar(1.0, [veiculo])
        
        # Verifica se o veículo se moveu
        assert veiculo.posicao[1] > posicao_inicial[1], "Veículo deveria ter se movido para baixo"
        assert veiculo.fisica.velocidade > 0, "Veículo deveria estar se movendo"
    
    def test_veiculo_para_quando_veiculo_frente_para(self):
        """Testa se veículo para quando o veículo à frente para."""
        # Cria veículo à frente parado
        veiculo_frente = self.criar_veiculo_norte((100, 150))
        veiculo_frente.fisica.velocidade = 0.0
        
        # Cria veículo atrás
        veiculo_atras = self.criar_veiculo_norte((100, 100))
        veiculo_atras.fisica.velocidade = 1.0
        
        todos_veiculos = [veiculo_frente, veiculo_atras]
        
        # Simula várias atualizações
        for _ in range(10):
            veiculo_atras.atualizar(1.0, todos_veiculos)
        
        # Verifica se o veículo atrás parou
        assert veiculo_atras.fisica.velocidade == 0.0, "Veículo atrás deveria ter parado"
    
    def test_veiculo_mantem_distancia_segura(self):
        """Testa se veículo mantém distância segura do veículo à frente."""
        # Cria veículo à frente
        veiculo_frente = self.criar_veiculo_norte((100, 200))
        veiculo_frente.fisica.velocidade = 0.5
        
        # Cria veículo atrás
        veiculo_atras = self.criar_veiculo_norte((100, 100))
        veiculo_atras.fisica.velocidade = 1.0
        
        todos_veiculos = [veiculo_frente, veiculo_atras]
        
        # Simula várias atualizações
        for _ in range(20):
            veiculo_atras.atualizar(1.0, todos_veiculos)
        
        # Calcula distância final
        distancia_final = abs(veiculo_atras.posicao[1] - veiculo_frente.posicao[1])
        
        # Verifica se mantém distância segura
        assert distancia_final >= CONFIG.DISTANCIA_MIN_VEICULO, f"Distância {distancia_final} é menor que mínima {CONFIG.DISTANCIA_MIN_VEICULO}"
    
    def test_veiculo_nao_colide_com_veiculo_lateral(self):
        """Testa se veículo não considera colisão com veículo em via perpendicular."""
        # Cria veículo vertical
        veiculo_vertical = self.criar_veiculo_norte((100, 100))
        veiculo_vertical.fisica.velocidade = 1.0
        
        # Cria veículo horizontal em posição diferente (mas mesma coordenada Y)
        veiculo_horizontal = self.criar_veiculo_leste((200, 100))
        veiculo_horizontal.fisica.velocidade = 1.0
        
        todos_veiculos = [veiculo_vertical, veiculo_horizontal]
        
        # Simula atualização
        posicao_inicial_vertical = veiculo_vertical.posicao.copy()
        posicao_inicial_horizontal = veiculo_horizontal.posicao.copy()
        
        veiculo_vertical.atualizar(1.0, todos_veiculos)
        veiculo_horizontal.atualizar(1.0, todos_veiculos)
        
        # Ambos devem se mover pois estão em vias diferentes
        assert veiculo_vertical.posicao[1] > posicao_inicial_vertical[1], "Veículo vertical deveria se mover"
        assert veiculo_horizontal.posicao[0] > posicao_inicial_horizontal[0], "Veículo horizontal deveria se mover"
    
    def test_veiculo_desacelera_gradualmente_ao_aproximar(self):
        """Testa se veículo desacelera gradualmente ao se aproximar de obstáculo."""
        # Cria veículo à frente
        veiculo_frente = self.criar_veiculo_norte((100, 200))
        veiculo_frente.fisica.velocidade = 0.3
        
        # Cria veículo atrás com velocidade alta
        veiculo_atras = self.criar_veiculo_norte((100, 100))
        veiculo_atras.fisica.velocidade = 1.0
        
        todos_veiculos = [veiculo_frente, veiculo_atras]
        
        velocidades = []
        
        # Simula várias atualizações e coleta velocidades
        for _ in range(15):
            veiculo_atras.atualizar(1.0, todos_veiculos)
            velocidades.append(veiculo_atras.fisica.velocidade)
        
        # Verifica se houve desaceleração (pelo menos uma redução significativa)
        assert velocidades[0] > velocidades[-1] or abs(velocidades[0] - velocidades[-1]) < 0.1, "Velocidade deveria ter diminuído ou se estabilizado"
        # Verifica se a velocidade final está dentro de um range aceitável
        assert velocidades[-1] <= veiculo_atras.velocidade_maxima_individual, "Velocidade final deveria respeitar limite individual"
    
    def test_veiculo_para_imediatamente_em_colisao_iminente(self):
        """Testa se veículo para imediatamente quando colisão é iminente."""
        # Cria dois veículos muito próximos
        veiculo1 = self.criar_veiculo_norte((100, 100))
        veiculo2 = self.criar_veiculo_norte((100, 100 + 5))  # Muito próximo
        
        veiculo1.fisica.velocidade = 1.0
        veiculo2.fisica.velocidade = 0.0
        
        todos_veiculos = [veiculo1, veiculo2]
        
        # Simula atualização
        posicao_inicial = veiculo1.posicao.copy()
        veiculo1.atualizar(1.0, todos_veiculos)
        
        # Verifica parada imediata
        assert veiculo1.fisica.velocidade == 0.0, "Veículo deveria ter parado imediatamente"
        assert veiculo1.posicao == posicao_inicial, "Veículo não deveria ter se movido"
    
    def test_veiculo_acelera_quando_obstaculo_remove(self):
        """Testa se veículo acelera quando obstáculo é removido."""
        # Cria veículo atrás
        veiculo = self.criar_veiculo_norte((100, 100))
        veiculo.fisica.velocidade = 0.5  # Velocidade inicial não zero
        
        # Cria veículo à frente que será removido
        veiculo_frente = self.criar_veiculo_norte((100, 150))
        veiculo_frente.fisica.velocidade = 0.0
        
        todos_veiculos = [veiculo, veiculo_frente]
        
        # Simula algumas atualizações com obstáculo
        for _ in range(5):
            veiculo.atualizar(1.0, todos_veiculos)
        
        velocidade_com_obstaculo = veiculo.fisica.velocidade
        
        # Remove o obstáculo
        veiculo_frente.ativo = False
        todos_veiculos = [veiculo]
        
        # Simula atualizações sem obstáculo
        for _ in range(10):
            veiculo.atualizar(1.0, todos_veiculos)
        
        # Verifica se acelerou ou pelo menos manteve velocidade
        assert veiculo.fisica.velocidade >= velocidade_com_obstaculo, "Veículo deveria ter acelerado ou mantido velocidade após remoção do obstáculo"
    
    def test_veiculo_respeita_limite_velocidade_individual(self):
        """Testa se veículo respeita seu limite de velocidade individual."""
        veiculo = self.criar_veiculo_norte((100, 100))
        
        # Simula várias atualizações sem obstáculos
        for _ in range(50):
            veiculo.atualizar(1.0, [veiculo])
        
        # Verifica se não excedeu velocidade máxima individual
        assert veiculo.fisica.velocidade <= veiculo.velocidade_maxima_individual, "Velocidade excedeu limite individual"
    
    def test_veiculo_nao_muda_direcao_em_colisao(self):
        """Testa se veículo não muda de direção ao evitar colisão."""
        veiculo = self.criar_veiculo_norte((100, 100))
        veiculo.fisica.velocidade = 1.0
        
        # Cria obstáculo à frente
        obstaculo = self.criar_veiculo_norte((100, 150))
        obstaculo.fisica.velocidade = 0.0
        
        todos_veiculos = [veiculo, obstaculo]
        
        # Simula atualizações
        for _ in range(10):
            veiculo.atualizar(1.0, todos_veiculos)
        
        # Verifica se manteve direção Norte (movimento vertical)
        assert veiculo.direcao == Direcao.NORTE, "Veículo não deveria mudar de direção"
        assert veiculo.posicao[0] == 100, "Veículo não deveria se mover horizontalmente"
    
    def test_veiculo_para_em_frenagem_emergencia(self):
        """Testa se veículo para corretamente em frenagem de emergência."""
        # Cria veículo muito próximo do obstáculo
        veiculo = self.criar_veiculo_norte((100, 100))
        veiculo.fisica.velocidade = 1.0
        
        obstaculo = self.criar_veiculo_norte((100, 100 + CONFIG.DISTANCIA_MIN_VEICULO // 2))
        obstaculo.fisica.velocidade = 0.0
        
        todos_veiculos = [veiculo, obstaculo]
        
        # Simula atualização
        veiculo.atualizar(1.0, todos_veiculos)
        
        # Verifica se parou (pode ser por colisão futura ou frenagem)
        assert veiculo.fisica.velocidade == 0.0, "Deveria ter parado completamente"
        # Verifica se não se moveu devido à proximidade
        assert veiculo.posicao == [100, 100], "Veículo não deveria ter se movido devido à proximidade"
    
    def test_multiplos_veiculos_em_fila(self):
        """Testa comportamento de múltiplos veículos em fila."""
        # Cria fila de 3 veículos
        veiculos = []
        for i in range(3):
            veiculo = self.criar_veiculo_norte((100, 100 + i * 60))
            veiculo.fisica.velocidade = 1.0
            veiculos.append(veiculo)
        
        # Simula várias atualizações
        for _ in range(20):
            for veiculo in veiculos:
                veiculo.atualizar(1.0, veiculos)
        
        # Verifica se mantiveram distâncias seguras
        for i in range(len(veiculos) - 1):
            distancia = abs(veiculos[i].posicao[1] - veiculos[i+1].posicao[1])
            assert distancia >= CONFIG.DISTANCIA_MIN_VEICULO, f"Veículos {i} e {i+1} muito próximos"
    
    def test_veiculo_nao_move_com_velocidade_zero(self):
        """Testa se veículo com velocidade zero não se move."""
        veiculo = self.criar_veiculo_norte((100, 100))
        veiculo.fisica.velocidade = 0.0
        
        posicao_inicial = veiculo.posicao.copy()
        
        # Simula várias atualizações
        for _ in range(10):
            veiculo.atualizar(1.0, [veiculo])
        
        # Verifica se não se moveu
        assert veiculo.posicao == posicao_inicial, "Veículo com velocidade zero não deveria se mover"
        assert veiculo.fisica.velocidade == 0.0, "Velocidade deveria permanecer zero"
    
    # def test_veiculo_troca_faixa_quando_frente_mais_lento(self):
    #     """Testa se veículo troca de faixa quando o veículo da frente é mais lento."""
    #     # Cria veículo lento na faixa 0
    #     veiculo_lento = self.criar_veiculo_norte((20, 150))  # Faixa 0
    #     veiculo_lento.fisica.velocidade = 0.3
        
    #     # Cria veículo rápido na mesma faixa
    #     veiculo_rapido = self.criar_veiculo_norte((20, 100))  # Faixa 0
    #     veiculo_rapido.fisica.velocidade = 0.8
        
    #     todos_veiculos = [veiculo_lento, veiculo_rapido]
        
    #     # Simula várias atualizações
    #     for _ in range(30):
    #         veiculo_rapido.atualizar(1.0, todos_veiculos)
    #         veiculo_lento.atualizar(1.0, todos_veiculos)
        
    #     # Verifica se o veículo rápido mudou de faixa (posição X deve estar próxima da faixa 1)
    #     faixa_1_posicao = CONFIG.LARGURA_FAIXA + CONFIG.LARGURA_FAIXA // 2
    #     assert abs(veiculo_rapido.posicao[0] - faixa_1_posicao) < CONFIG.LARGURA_FAIXA * 0.5, "Veículo deveria ter trocado para faixa 1"
    
    # def test_veiculo_nao_troca_faixa_quando_faixa_ocupada(self):
    #     """Testa se veículo não troca de faixa quando a faixa alternativa está ocupada."""
    #     # Cria veículo lento na faixa 0
    #     veiculo_lento = self.criar_veiculo_norte((20, 150))  # Faixa 0
    #     veiculo_lento.fisica.velocidade = 0.3
        
    #     # Cria veículo rápido na faixa 0
    #     veiculo_rapido = self.criar_veiculo_norte((20, 100))  # Faixa 0
    #     veiculo_rapido.fisica.velocidade = 0.8
        
    #     # Cria veículo na faixa 1 (bloqueando a troca)
    #     veiculo_bloqueador = self.criar_veiculo_norte((60, 120))  # Faixa 1
    #     veiculo_bloqueador.fisica.velocidade = 0.5
        
    #     todos_veiculos = [veiculo_lento, veiculo_rapido, veiculo_bloqueador]
        
    #     # Simula várias atualizações
    #     for _ in range(20):
    #         veiculo_rapido.atualizar(1.0, todos_veiculos)
    #         veiculo_lento.atualizar(1.0, todos_veiculos)
    #         veiculo_bloqueador.atualizar(1.0, todos_veiculos)
        
    #     # Verifica se o veículo rápido NÃO mudou de faixa (deve ter freado)
    #     faixa_0_posicao = CONFIG.LARGURA_FAIXA // 2
    #     assert abs(veiculo_rapido.posicao[0] - faixa_0_posicao) < CONFIG.LARGURA_FAIXA * 0.5, "Veículo não deveria ter trocado de faixa"
    #     # Verifica se freou devido ao obstáculo
    #     assert veiculo_rapido.fisica.velocidade < 0.8, "Veículo deveria ter freado"
    
    # def test_veiculo_nao_troca_faixa_quando_frente_mais_rapido(self):
    #     """Testa se veículo não tenta trocar de faixa quando o veículo da frente é mais rápido."""
    #     # Cria veículo rápido na faixa 0
    #     veiculo_rapido_frente = self.criar_veiculo_norte((20, 150))  # Faixa 0
    #     veiculo_rapido_frente.fisica.velocidade = 0.9
        
    #     # Cria veículo lento na faixa 0
    #     veiculo_lento = self.criar_veiculo_norte((20, 100))  # Faixa 0
    #     veiculo_lento.fisica.velocidade = 0.5
        
    #     todos_veiculos = [veiculo_rapido_frente, veiculo_lento]
        
    #     # Simula várias atualizações
    #     for _ in range(20):
    #         veiculo_lento.atualizar(1.0, todos_veiculos)
    #         veiculo_rapido_frente.atualizar(1.0, todos_veiculos)
        
    #     # Verifica se o veículo lento NÃO mudou de faixa (não deveria tentar trocar)
    #     faixa_0_posicao = CONFIG.LARGURA_FAIXA // 2
    #     assert abs(veiculo_lento.posicao[0] - faixa_0_posicao) < CONFIG.LARGURA_FAIXA * 0.5, "Veículo não deveria ter trocado de faixa"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
