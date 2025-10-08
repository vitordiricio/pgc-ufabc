"""
Ponto de entrada principal para a simulação de tráfego urbano.
Projeto de Graduação em Computação - UFABC
Autores: Vitor Bobig Diricio e Thiago Schwartz Machado
"""
import pygame
import sys
import os
import argparse
from configuracao import CONFIG, TipoHeuristica
from simulacao import Simulacao, SimulacaoHeadless


def verificar_requisitos():
    """Verifica se todos os requisitos estão instalados."""
    try:
        import pygame
        print(f"✓ Pygame {pygame.version.ver} instalado")
        return True
    except ImportError:
        print("✗ Pygame não encontrado. Instale com: pip install pygame")
        return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Simulação de Tráfego Urbano - UFABC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python main.py --usegui                    # Executa com interface gráfica
  python main.py --vertical-horizontal 200   # Executa por 200s com heurística vertical/horizontal
  python main.py --random 300               # Executa por 300s com heurística aleatória
  python main.py --llm 180                  # Executa por 180s com heurística LLM
  python main.py --adaptive 240             # Executa por 240s com heurística adaptativa de densidade
  python main.py --manual 120               # Executa por 120s com controle manual
        """
    )
    
    # GUI mode
    parser.add_argument('--usegui', action='store_true',
                       help='Executa a simulação com interface gráfica (modo padrão)')
    
    # Heuristic-specific modes
    parser.add_argument('--vertical-horizontal', type=int, metavar='SECONDS',
                       help='Executa simulação por X segundos usando heurística vertical/horizontal')
    parser.add_argument('--random', type=int, metavar='SECONDS',
                       help='Executa simulação por X segundos usando heurística aleatória')
    parser.add_argument('--llm', type=int, metavar='SECONDS',
                       help='Executa simulação por X segundos usando heurística LLM')
    parser.add_argument('--adaptive', type=int, metavar='SECONDS',
                       help='Executa simulação por X segundos usando heurística adaptativa de densidade')
    parser.add_argument('--manual', type=int, metavar='SECONDS',
                       help='Executa simulação por X segundos usando controle manual')
    
    # Additional options
    parser.add_argument('--output', '-o', type=str, metavar='FILE',
                       help='Nome do arquivo de saída para o relatório (padrão: auto-gerado)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mostra informações detalhadas durante a execução')
    
    return parser.parse_args()


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
    print("  • 1-5: Mudar heurística (1:Vertical/Horizontal, 2:Aleatório, 3:LLM, 4:Adaptativa, 5:Manual)")
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


def executar_modo_gui():
    """Executa a simulação com interface gráfica."""
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


def executar_modo_headless(heuristica: TipoHeuristica, duracao: int, 
                          nome_arquivo: str = None, verbose: bool = False):
    """Executa a simulação sem interface gráfica."""
    try:
        simulacao = SimulacaoHeadless(
            heuristica=heuristica,
            duracao_segundos=duracao,
            nome_arquivo=nome_arquivo,
            verbose=verbose
        )
        simulacao.executar()
    except KeyboardInterrupt:
        print("\n\nSimulação interrompida pelo usuário.")
    except Exception as e:
        print(f"\nErro durante a execução: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Função principal do programa."""
    args = parse_arguments()
    
    # Determina o modo de execução
    if args.vertical_horizontal is not None:
        executar_modo_headless(TipoHeuristica.VERTICAL_HORIZONTAL, 
                              args.vertical_horizontal, args.output, args.verbose)
    elif args.random is not None:
        executar_modo_headless(TipoHeuristica.RANDOM_OPEN_CLOSE, 
                              args.random, args.output, args.verbose)
    elif args.llm is not None:
        executar_modo_headless(TipoHeuristica.LLM_HEURISTICA, 
                              args.llm, args.output, args.verbose)
    elif args.adaptive is not None:
        executar_modo_headless(TipoHeuristica.ADAPTATIVA_DENSIDADE, 
                              args.adaptive, args.output, args.verbose)
    elif args.manual is not None:
        executar_modo_headless(TipoHeuristica.MANUAL, 
                              args.manual, args.output, args.verbose)
    else:
        # Modo padrão: GUI
        executar_modo_gui()


if __name__ == "__main__":
    main()