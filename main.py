"""
Ponto de entrada principal para a simulação de tráfego urbano.
Projeto de Graduação em Computação - UFABC
Autores: Vitor Bobig Diricio e Thiago Schwartz Machado
"""
import pygame
import sys
import os
from configuracao import CONFIG
from simulacao import Simulacao


def verificar_requisitos():
    """Verifica se todos os requisitos estão instalados."""
    try:
        import pygame
        print(f"✓ Pygame {pygame.version.ver} instalado")
        return True
    except ImportError:
        print("✗ Pygame não encontrado. Instale com: pip install pygame")
        return False


def exibir_introducao():
    """Exibe informações iniciais sobre o projeto."""
    print("="*60)
    print("SIMULAÇÃO DE TRÁFEGO URBANO")
    print("Projeto de Graduação em Computação - UFABC")
    print("="*60)
    print("\nAutores:")
    print("  • Vitor Bobig Diricio")
    print("  • Thiago Schwartz Machado")
    print("\nObjetivo:")
    print("  Desenvolver um sistema de simulação para análise e")
    print("  otimização da dinâmica do tráfego urbano através de")
    print("  diferentes estratégias de controle de semáforos.")
    print("\nFuncionalidades principais:")
    print("  • Múltiplas heurísticas de controle")
    print("  • Análise comparativa de desempenho")
    print("  • Visualização em tempo real")
    print("  • Coleta e exportação de métricas")
    print("="*60)
    print("\nControles principais:")
    print("  • ESPAÇO: Pausar/Continuar")
    print("  • 1-4: Mudar heurística")
    print("  • +/-: Ajustar velocidade")
    print("  • R: Reiniciar")
    print("  • ESC: Sair")
    print("  • CTRL+S: Salvar relatório")
    print("="*60)
    print("\nIniciando simulação automaticamente...")


def configurar_ambiente():
    """Configura o ambiente de execução."""
    # Centraliza a janela
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    
    # Cria diretório para relatórios se não existir
    os.makedirs('relatorios', exist_ok=True)


def main():
    """Função principal do programa."""
    # Verifica requisitos
    if not verificar_requisitos():
        sys.exit(1)
    
    # Exibe introdução
    exibir_introducao()
    
    # Configura ambiente
    configurar_ambiente()
    
    # Inicializa Pygame
    pygame.init()
    
    try:
        # Cria e executa a simulação
        print("\nIniciando simulação...")
        simulacao = Simulacao(
            linhas=CONFIG.LINHAS_GRADE,
            colunas=CONFIG.COLUNAS_GRADE
        )
        
        # Executa o loop principal
        simulacao.executar()
        
    except KeyboardInterrupt:
        print("\n\nSimulação interrompida pelo usuário.")
    except Exception as e:
        print(f"\nErro durante a execução: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Finaliza Pygame
        pygame.quit()
        print("\nSimulação finalizada.")


if __name__ == "__main__":
    main()