from cruzamento import Cruzamento, MalhaViaria
from veiculo import Veiculo
from semaforo import Semaforo, GerenciadorSemaforos
from configuracao import Direcao


def test_colisao_veiculos():
    cruzamento = Cruzamento(posicao=(0, 0), id_cruzamento=(0, 0), gerenciador_semaforos=GerenciadorSemaforos(), malha_viaria=MalhaViaria())
    veiculo = Veiculo(direcao=Direcao.NORTE, posicao=(0, 0), id_cruzamento_origem=(0, 0))
    assert cruzamento.colisao_veiculos(veiculo) == False