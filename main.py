"""
Ponto de entrada principal para a simulação de tráfego urbano.
Projeto de Graduação em Computação - UFABC
Autores: Vitor Bobig Diricio e Thiago Schwartz Machado
"""
import pygame
import os
import argparse
from configuracao import CONFIG, TipoHeuristica
from simulacao import Simulacao


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Simulação de Tráfego Urbano - UFABC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Simulação com interface gráfica
  python main.py --gui                      # Executa com interface gráfica (heurística padrão, 3x3)
  python main.py --adaptive --gui           # Executa com heurística adaptativa em modo GUI (3x3)
  python main.py --gui --rows 4 --cols 5    # Executa com grade 4x5 (heurística padrão)
  python main.py --manual --gui             # Executa com controle manual (requer GUI)
  
  # Simulação headless com diferentes heurísticas
  python main.py --vertical-horizontal 200  # Executa por 200s com heurística vertical/horizontal (3x3)
  python main.py --random 300 --rows 2 --cols 4  # Executa por 300s com heurística aleatória (2x4)
  python main.py --llm 180                  # Executa por 180s com heurística LLM (3x3)
  python main.py --adaptive 240 --rows 5 --cols 5  # Executa por 240s com heurística adaptativa (5x5)
  python main.py --rl 300                   # Executa por 300s com reinforcement learning (3x3)
  
  # Reinforcement Learning
  python main.py --train-rl                 # Treina modelo RL por 100000 timesteps (padrão)
  python main.py --train-rl 500000          # Treina modelo RL por 500000 timesteps
  python main.py --train-rl 100000 --rl-save-path rl/models/my_model.zip  # Treina com caminho customizado
  python main.py --test-rl                  # Testa modelo RL padrão (best_model.zip)
  python main.py --test-rl rl/models/my_model.zip --rl-episodes 10  # Testa modelo específico com 10 episódios
        """
    )
    
    # GUI mode
    parser.add_argument('--gui', action='store_true',
                       help='Executa a simulação com interface gráfica (executa indefinidamente)')
    
    # Heuristic-specific modes
    parser.add_argument('--vertical-horizontal', type=int, metavar='SECONDS', nargs='?',
                       help='Executa simulação por X segundos usando heurística vertical/horizontal (ou indefinidamente com --gui)')
    parser.add_argument('--random', type=int, metavar='SECONDS', nargs='?',
                       help='Executa simulação por X segundos usando heurística aleatória (ou indefinidamente com --gui)')
    parser.add_argument('--llm', type=int, metavar='SECONDS', nargs='?',
                       help='Executa simulação por X segundos usando heurística LLM (modelo Ollama) ou indefinidamente com --gui')
    parser.add_argument('--chatgpt', type=int, metavar='SECONDS', nargs='?',
                       help='Executa simulação por X segundos usando heurística ChatGPT (OpenAI) ou indefinidamente com --gui')
    parser.add_argument('--adaptive', type=int, metavar='SECONDS', nargs='?',
                       help='Executa simulação por X segundos usando heurística adaptativa de densidade (ou indefinidamente com --gui)')
    parser.add_argument('--rl', type=int, metavar='SECONDS', nargs='?',
                       help='Executa simulação por X segundos usando reinforcement learning (ou indefinidamente com --gui)')
    parser.add_argument('--manual', type=int, metavar='SECONDS', nargs='?',
                       help='Executa simulação por X segundos usando controle manual (ou indefinidamente com --gui, requer --gui)')
    
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
    parser.add_argument('--openai-api-key', type=str, metavar='KEY',
                       help='Define a chave de API da OpenAI para a heurística ChatGPT (sobrescreve a variável de ambiente)')
    parser.add_argument('--openai-model', type=str, metavar='MODEL',
                       help='Define o modelo da OpenAI usado pela heurística ChatGPT (sobrescreve a variável de ambiente)')
    
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
    print("  • +/-: Ajustar velocidade")
    print("  • R: Reiniciar")
    print("  • ESC: Sair (salva relatório automaticamente)")
    print("  • N: Avançar semáforos (modo manual)")
    print("  • Clique: Controlar semáforos (modo manual)")
    print("="*60)
    print("\nIniciando simulação automaticamente...")


def configurar_ambiente():
    """Configura o ambiente de execução."""
    # Centraliza a janela
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    
    # Cria diretório para relatórios se não existir
    os.makedirs('relatorios', exist_ok=True)


def executar_modo_gui(heuristica: TipoHeuristica, rows: int = 3, cols: int = 3):
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
            heuristica=heuristica,
            use_gui=True,
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
        simulacao = Simulacao(
            heuristica=heuristica,
            use_gui=False,
            duracao_segundos=duracao,
            nome_arquivo=nome_arquivo,
            verbose=verbose,
            linhas=rows,
            colunas=cols
        )
        simulacao.executar()
    except KeyboardInterrupt:
        print("\n\nSimulação interrompida pelo usuário.")
    except Exception as e:
        print(f"\nErro durante a execução: {e}")
        import traceback
        traceback.print_exc()


def validate_arguments(args):
    """Validate command line arguments for conflicts and requirements."""
    import sys
    
    # Check which heuristic arguments were provided (regardless of value)
    heuristic_provided = [
        '--vertical-horizontal' in sys.argv,
        '--random' in sys.argv,
        '--llm' in sys.argv,
        '--chatgpt' in sys.argv,
        '--adaptive' in sys.argv,
        '--rl' in sys.argv,
        '--manual' in sys.argv
    ]
    heuristic_count = sum(heuristic_provided)
    
    # Check for multiple heuristics
    if heuristic_count > 1:
        print("ERRO: Apenas uma heurística pode ser especificada por vez.")
        return False
    
    # Check manual heuristic requirements
    if '--manual' in sys.argv and not args.gui:
        print("ERRO: Heurística manual requer modo GUI (--gui).")
        print("Use: python main.py --manual --gui")
        return False
    
    # Check GUI mode conflicts
    if args.gui and heuristic_count > 0:
        # Check if any heuristic has duration specified (not None means duration was provided)
        heuristic_args = [
            args.vertical_horizontal, args.random, args.llm,
            args.chatgpt,
            args.adaptive, args.rl, args.manual
        ]
        for heuristic_arg in heuristic_args:
            if heuristic_arg is not None:
                print("ERRO: Modo GUI não aceita duração em segundos.")
                print("Use: python main.py --adaptive --gui (sem duração)")
                return False
    
    # Check headless mode requirements
    if not args.gui and heuristic_count == 0:
        print("ERRO: Modo headless requer especificação de heurística e duração.")
        print("Use: python main.py --adaptive 200")
        return False
    
    return True


def main():
    """Função principal do programa."""
    import sys
    args = parse_arguments()

    # Configurações diretas da API OpenAI (caso informadas por linha de comando)
    if getattr(args, 'openai_api_key', None):
        os.environ['OPENAI_API_KEY'] = args.openai_api_key
    if getattr(args, 'openai_model', None):
        os.environ['OPENAI_MODEL'] = args.openai_model
    
    # Validate arguments
    if not validate_arguments(args):
        return
    
    # Determina o modo de execução
    if args.train_rl is not None:
        print("Opção --train-rl detectada. Use 'python train_rl.py' para treinar o modelo RL.")
        print("Exemplo: python train_rl.py --timesteps 100000")
        return
    elif args.test_rl is not None:
        print("Opção --test-rl detectada. Use 'python test_rl.py' para testar o modelo RL.")
        print("Exemplo: python test_rl.py --model-path rl/models/traffic_model.zip")
        return
    elif args.gui:
        # GUI mode - determine heuristic
        if '--vertical-horizontal' in sys.argv:
            executar_modo_gui(TipoHeuristica.VERTICAL_HORIZONTAL, args.rows, args.cols)
        elif '--random' in sys.argv:
            executar_modo_gui(TipoHeuristica.RANDOM_OPEN_CLOSE, args.rows, args.cols)
        elif '--llm' in sys.argv:
            executar_modo_gui(TipoHeuristica.LLM_HEURISTICA, args.rows, args.cols)
        elif '--chatgpt' in sys.argv:
            executar_modo_gui(TipoHeuristica.LLM_CHATGPT, args.rows, args.cols)
        elif '--adaptive' in sys.argv:
            executar_modo_gui(TipoHeuristica.ADAPTATIVA_DENSIDADE, args.rows, args.cols)
        elif '--rl' in sys.argv:
            executar_modo_gui(TipoHeuristica.REINFORCEMENT_LEARNING, args.rows, args.cols)
        elif '--manual' in sys.argv:
            executar_modo_gui(TipoHeuristica.MANUAL, args.rows, args.cols)
        else:
            # Default heuristic
            executar_modo_gui(CONFIG.HEURISTICA_ATIVA, args.rows, args.cols)
    else:
        # Headless mode
        if args.vertical_horizontal is not None:
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
        elif args.chatgpt is not None:
            executar_modo_headless(TipoHeuristica.LLM_CHATGPT,
                                  args.chatgpt, args.output, args.verbose,
                                  args.rows, args.cols)
        elif args.adaptive is not None:
            executar_modo_headless(TipoHeuristica.ADAPTATIVA_DENSIDADE, 
                                  args.adaptive, args.output, args.verbose,
                                  args.rows, args.cols)
        elif args.rl is not None:
            executar_modo_headless(TipoHeuristica.REINFORCEMENT_LEARNING, 
                                  args.rl, args.output, args.verbose,
                                  args.rows, args.cols)


if __name__ == "__main__":
    main()