"""
Ponto de entrada principal para a simulação de tráfego urbano.
Projeto de Graduação em Computação - UFABC
Autores: Vitor Bobig Diricio e Thiago Schwartz Machado
"""
import pygame
import os
import argparse
from configuracao import CONFIG, TipoHeuristica
from simulacao import Simulacao, SimulacaoHeadless


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Simulação de Tráfego Urbano - UFABC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Simulação com interface gráfica
  python main.py --usegui                    # Executa com interface gráfica (3x3)
  python main.py --usegui --rows 4 --cols 5  # Executa com grade 4x5
  
  # Simulação headless com diferentes heurísticas
  python main.py --vertical-horizontal 200   # Executa por 200s com heurística vertical/horizontal (3x3)
  python main.py --random 300 --rows 2 --cols 4  # Executa por 300s com heurística aleatória (2x4)
  python main.py --llm 180                  # Executa por 180s com heurística LLM (3x3)
  python main.py --adaptive 240 --rows 5 --cols 5  # Executa por 240s com heurística adaptativa (5x5)
  python main.py --rl 300                   # Executa por 300s com reinforcement learning (3x3)
  python main.py --manual 120               # Executa por 120s com controle manual (3x3)
  
  # Reinforcement Learning
  python main.py --train-rl                 # Treina modelo RL por 100000 timesteps (padrão)
  python main.py --train-rl 500000          # Treina modelo RL por 500000 timesteps
  python main.py --train-rl 100000 --rl-save-path rl/models/my_model.zip  # Treina com caminho customizado
  python main.py --test-rl                  # Testa modelo RL padrão (best_model.zip)
  python main.py --test-rl rl/models/my_model.zip --rl-episodes 10  # Testa modelo específico com 10 episódios
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
    parser.add_argument('--rl', type=int, metavar='SECONDS',
                       help='Executa simulação por X segundos usando reinforcement learning')
    parser.add_argument('--manual', type=int, metavar='SECONDS',
                       help='Executa simulação por X segundos usando controle manual')
    
    # Reinforcement Learning options
    parser.add_argument('--train-rl', type=int, metavar='TIMESTEPS', nargs='?', const=100000,
                       help='Treina modelo de reinforcement learning por X timesteps (padrão: 100000)')
    parser.add_argument('--rl-save-path', type=str, metavar='PATH',
                       help='Caminho para salvar o modelo RL treinado (padrão: rl/models/traffic_model.zip)')
    parser.add_argument('--rl-eval-freq', type=int, metavar='FREQ', default=10000,
                       help='Frequência de avaliação durante treinamento RL (padrão: 10000)')
    parser.add_argument('--test-rl', type=str, metavar='MODEL_PATH', nargs='?', const='rl/models/best_model.zip',
                       help='Testa modelo RL treinado (padrão: rl/models/best_model.zip)')
    parser.add_argument('--rl-episodes', type=int, metavar='EPISODES', default=5,
                       help='Número de episódios para teste RL (padrão: 5)')
    
    # Grid size options
    parser.add_argument('--rows', type=int, default=3, metavar='ROWS',
                       help='Número de linhas da grade de cruzamentos (padrão: 3)')
    parser.add_argument('--cols', type=int, default=3, metavar='COLS',
                       help='Número de colunas da grade de cruzamentos (padrão: 3)')
    
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


def executar_modo_gui(rows: int = 3, cols: int = 3):
    # Exibe introdução
    exibir_introducao()
    
    # Configura ambiente
    configurar_ambiente()
    
    # Inicializa Pygame
    pygame.init()
    
    try:
        # Cria e executa a simulação
        print(f"\nIniciando simulação com grade {rows}x{cols}...")
        simulacao = Simulacao(
            linhas=rows,
            colunas=cols
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
                          nome_arquivo: str = None, verbose: bool = False,
                          rows: int = 3, cols: int = 3):
    """Executa a simulação sem interface gráfica."""
    try:
        print(f"Iniciando simulação headless com grade {rows}x{cols}...")
        # Note: SimulacaoHeadless doesn't support custom grid sizes yet
        # For now, it uses the default grid size from CONFIG
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
    if args.train_rl is not None:
        print("Opção --train-rl detectada. Use 'python train_rl.py' para treinar o modelo RL.")
        print("Exemplo: python train_rl.py --timesteps 100000")
        return
    elif args.test_rl is not None:
        print("Opção --test-rl detectada. Use 'python test_rl.py' para testar o modelo RL.")
        print("Exemplo: python test_rl.py --model-path rl/models/traffic_model.zip")
        return
    elif args.vertical_horizontal is not None:
        executar_modo_headless(TipoHeuristica.VERTICAL_HORIZONTAL, 
                              args.vertical_horizontal, args.output, args.verbose,
                              args.rows, args.cols)
    elif args.random is not None:
        executar_modo_headless(TipoHeuristica.RANDOM_OPEN_CLOSE, 
                              args.random, args.output, args.verbose,
                              args.rows, args.cols)
    elif args.llm is not None:
        executar_modo_headless(TipoHeuristica.LLM_HEURISTICA, 
                              args.llm, args.output, args.verbose,
                              args.rows, args.cols)
    elif args.adaptive is not None:
        executar_modo_headless(TipoHeuristica.ADAPTATIVA_DENSIDADE, 
                              args.adaptive, args.output, args.verbose,
                              args.rows, args.cols)
    elif args.rl is not None:
        executar_modo_headless(TipoHeuristica.REINFORCEMENT_LEARNING, 
                              args.rl, args.output, args.verbose,
                              args.rows, args.cols)
    elif args.manual is not None:
        executar_modo_headless(TipoHeuristica.MANUAL, 
                              args.manual, args.output, args.verbose,
                              args.rows, args.cols)
    else:
        # Modo padrão: GUI
        executar_modo_gui(args.rows, args.cols)


if __name__ == "__main__":
    main()