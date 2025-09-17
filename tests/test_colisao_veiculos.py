import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cruzamento import Cruzamento, MalhaViaria
from veiculo import Veiculo
from semaforo import GerenciadorSemaforos
from configuracao import Direcao


def test_veiculo_criacao_basica():
    """Testa a criação básica de um veículo."""
    veiculo = Veiculo(direcao=Direcao.NORTE, posicao=(100, 100), id_cruzamento_origem=(0, 0))
    
    assert veiculo.direcao == Direcao.NORTE
    assert veiculo.posicao == [100, 100]
    assert veiculo.id_cruzamento_origem == (0, 0)
    assert veiculo.ativo == True
    assert veiculo.velocidade == 0.0


def test_veiculo_colisao_sem_colisao():
    """Testa detecção de colisão quando não há colisão."""
    # Cria dois veículos distantes
    veiculo1 = Veiculo(direcao=Direcao.NORTE, posicao=(100, 100), id_cruzamento_origem=(0, 0))
    veiculo2 = Veiculo(direcao=Direcao.NORTE, posicao=(100, 200), id_cruzamento_origem=(0, 0))
    
    todos_veiculos = [veiculo1, veiculo2]
    
    # Veículo 1 não deve detectar colisão com veículo 2 (muito distante)
    assert veiculo1.verificar_colisao_futura(todos_veiculos) == False


def test_veiculo_colisao_com_colisao():
    """Testa detecção de colisão quando há colisão iminente."""
    # Cria dois veículos muito próximos
    veiculo1 = Veiculo(direcao=Direcao.NORTE, posicao=(100, 100), id_cruzamento_origem=(0, 0))
    veiculo2 = Veiculo(direcao=Direcao.NORTE, posicao=(100, 120), id_cruzamento_origem=(0, 0))
    
    todos_veiculos = [veiculo1, veiculo2]
    
    # Veículo 1 deve detectar colisão com veículo 2 (muito próximo)
    assert veiculo1.verificar_colisao_futura(todos_veiculos) == True


def test_veiculo_mesma_via():
    """Testa se dois veículos estão na mesma via."""
    veiculo1 = Veiculo(direcao=Direcao.NORTE, posicao=(100, 100), id_cruzamento_origem=(0, 0))
    veiculo2 = Veiculo(direcao=Direcao.NORTE, posicao=(105, 200), id_cruzamento_origem=(0, 0))
    veiculo3 = Veiculo(direcao=Direcao.NORTE, posicao=(200, 100), id_cruzamento_origem=(0, 0))
    
    # Veículos na mesma via vertical (X similar)
    assert veiculo1._mesma_via(veiculo2) == True
    
    # Veículos em vias diferentes (X muito diferente)
    assert veiculo1._mesma_via(veiculo3) == False


def test_cruzamento_criacao():
    """Testa a criação básica de um cruzamento."""
    gerenciador = GerenciadorSemaforos()
    malha = MalhaViaria()
    cruzamento = Cruzamento(posicao=(100, 100), id_cruzamento=(0, 0), 
                           gerenciador_semaforos=gerenciador, malha_viaria=malha)
    
    assert cruzamento.posicao == (100, 100)
    assert cruzamento.id == (0, 0)
    assert cruzamento.centro_x == 100
    assert cruzamento.centro_y == 100


def test_veiculo_movimento():
    """Testa o movimento básico de um veículo."""
    veiculo = Veiculo(direcao=Direcao.NORTE, posicao=(100, 100), id_cruzamento_origem=(0, 0))
    veiculo.velocidade = 1.0
    
    posicao_inicial = veiculo.posicao.copy()
    veiculo.atualizar(dt=1.0, todos_veiculos=[], malha=None)
    
    # Veículo Norte deve se mover para baixo (Y aumenta)
    assert veiculo.posicao[1] > posicao_inicial[1]
    assert veiculo.posicao[0] == posicao_inicial[0]  # X não muda