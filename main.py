"""
Ponto de entrada principal para a simulação de malha viária urbana.
"""
import pygame
import os
from configuracao import CONFIG
from simulacao import Simulacao


def main():
    """Função principal para inicializar e executar a simulação."""
    # Inicializa pygame
    pygame.init()
    
    # Configura o ambiente para centralizar a janela do pygame
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    
    # Usa os valores padrão de configuração
    linhas = CONFIG.LINHAS_GRADE
    colunas = CONFIG.COLUNAS_GRADE
    
    # Ajusta a posição inicial com base no número de linhas e colunas para centralizar
    largura_grade = CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS * (colunas - 1) + CONFIG.LARGURA_RUA
    altura_grade = CONFIG.ESPACAMENTO_ENTRE_CRUZAMENTOS * (linhas - 1) + CONFIG.LARGURA_RUA
    
    CONFIG.POSICAO_INICIAL_X = (CONFIG.LARGURA_TELA - largura_grade) // 2 + CONFIG.LARGURA_RUA // 2
    CONFIG.POSICAO_INICIAL_Y = (CONFIG.ALTURA_TELA - altura_grade) // 2 + CONFIG.LARGURA_RUA // 2
    
    # Inicializa e executa a simulação
    sim = Simulacao(linhas=linhas, colunas=colunas)
    sim.executar()
    
    # Finaliza pygame
    pygame.quit()


if __name__ == "__main__":
    main()