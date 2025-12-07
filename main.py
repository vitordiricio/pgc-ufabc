"""
Ponto de entrada principal para a simulação de tráfego urbano.
Projeto de Graduação em Computação - UFABC
Autores: Vitor Bobig Diricio e Thiago Schwartz Machado
"""
import pygame
import os
import argparse
import time
from datetime import datetime
from configuracao import CONFIG, TipoHeuristica
from simulacao import Simulacao


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Simulação de Tráfego Urbano - UFABC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Simulação com interface gráfica (Modo Padrão)
  python main.py                            # Executa com heurística padrão (3x3)
  python main.py --adaptive                 # Executa com heurística adaptativa
  python main.py --rows 4 --cols 5          # Executa com grade 4x5
  python main.py --manual                   # Executa com controle manual
  
  # Simulação com tempo definido (fecha automaticamente)
  python main.py --vertical-horizontal 200  # Executa por 200s com heurística vertical/horizontal
  python main.py --random 300               # Executa por 300s com heurística aleatória
  python main.py --llm 180                  # Executa por 180s com heurística LLM
  python main.py --rl 60                    # Executa por 60s com reinforcement learning
  
  # Reinforcement Learning
  python main.py --train-rl                 # Treina modelo RL
  python main.py --test-rl                  # Testa modelo RL
        """
    )
    
    # Heuristic-specific modes with optional duration
    parser.add_argument('--vertical-horizontal', type=int, metavar='SECONDS', nargs='?',
                       help='Executa usando heurística vertical/horizontal (opcional: duração em segundos)')
    parser.add_argument('--random', type=int, metavar='SECONDS', nargs='?',
                       help='Executa usando heurística aleatória (opcional: duração em segundos)')
    parser.add_argument('--llm', type=int, metavar='SECONDS', nargs='?',
                       help='Executa usando heurística LLM (opcional: duração em segundos)')
    parser.add_argument('--engine', type=str, choices=['ollama', 'openai'], default='ollama',
                       help='Engine para usar com heurística LLM (padrão: ollama)')
    parser.add_argument('--adaptive', type=int, metavar='SECONDS', nargs='?',
                       help='Executa usando heurística adaptativa (opcional: duração em segundos)')
    parser.add_argument('--rl', type=int, metavar='SECONDS', nargs='?',
                       help='Executa usando reinforcement learning (opcional: duração em segundos)')
    parser.add_argument('--manual', type=int, metavar='SECONDS', nargs='?',
                       help='Executa usando controle manual (opcional: duração em segundos)')
    
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
    
    parser.add_argument('--rl-model', type=str, metavar='PATH',
                       help='Caminho para o modelo RL a ser usado na simulação')
    
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


def executar_modo_gui(heuristica: TipoHeuristica, duracao: int = None, rows: int = 3, cols: int = 3, engine: str = 'ollama'):
    # Exibe introdução
    exibir_introducao()
    
    # Configura ambiente
    configurar_ambiente()
    
    # Inicializa Pygame
    pygame.init()
    
    try:
        # Cria e executa a simulação
        print(f"\nIniciando simulação com grade {rows}x{cols}...")
        if duracao:
            print(f"Duração definida: {duracao} segundos")

        simulacao = Simulacao(
            heuristica=heuristica,
            use_gui=True,
            duracao_segundos=duracao,
            linhas=rows,
            colunas=cols,
            engine=engine
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


def validate_arguments(args):
    """Validate command line arguments for conflicts and requirements."""
    import sys
    
    # Check which heuristic arguments were provided (regardless of value)
    heuristic_provided = [
        '--vertical-horizontal' in sys.argv,
        '--random' in sys.argv,
        '--llm' in sys.argv,
        '--adaptive' in sys.argv,
        '--rl' in sys.argv,
        '--manual' in sys.argv
    ]
    heuristic_count = sum(heuristic_provided)
    
    # Check for multiple heuristics
    if heuristic_count > 1:
        print("ERRO: Apenas uma heurística pode ser especificada por vez.")
        return False
    
    return True


def main():
    """Função principal do programa."""
    import sys
    
    # Record start time
    start_time = time.time()
    start_datetime = datetime.now()
    start_str = start_datetime.strftime("%H:%M:%S.%f")[:-3]  # Hours:Minutes:Seconds.Milliseconds
    
    print(f"\n{'='*60}")
    print(f"PROGRAM START TIME: {start_str}")
    print(f"{'='*60}\n")
    
    args = parse_arguments()
    
    # Validate arguments
    if not validate_arguments(args):
        # Record end time even if validation fails
        end_time = time.time()
        end_datetime = datetime.now()
        end_str = end_datetime.strftime("%H:%M:%S.%f")[:-3]
        duration = end_time - start_time
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        milliseconds = int((duration % 1) * 1000)
        print(f"\n{'='*60}")
        print(f"PROGRAM END TIME: {end_str}")
        print(f"TOTAL DURATION: {hours:02d}h {minutes:02d}m {seconds:02d}s {milliseconds:03d}ms")
        print(f"TOTAL DURATION (seconds): {duration:.6f}")
        print(f"{'='*60}\n")
        return
    
    # FIX: Update global configuration with provided arguments
    CONFIG.LINHAS_GRADE = args.rows
    CONFIG.COLUNAS_GRADE = args.cols
    
    # Determina o modo de execução
    if args.train_rl is not None:
        print("Opção --train-rl detectada. Use 'python train_rl.py' para treinar o modelo RL.")
        print("Exemplo: python train_rl.py --timesteps 100000")
        # Record end time
        end_time = time.time()
        end_datetime = datetime.now()
        end_str = end_datetime.strftime("%H:%M:%S.%f")[:-3]
        duration = end_time - start_time
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        milliseconds = int((duration % 1) * 1000)
        print(f"\n{'='*60}")
        print(f"PROGRAM START TIME: {start_str}")
        print(f"PROGRAM END TIME: {end_str}")
        print(f"TOTAL DURATION: {hours:02d}h {minutes:02d}m {seconds:02d}s {milliseconds:03d}ms")
        print(f"TOTAL DURATION (seconds): {duration:.6f}")
        print(f"{'='*60}\n")
        return
    elif args.test_rl is not None:
        print("Opção --test-rl detectada. Use 'python test_rl.py' para testar o modelo RL.")
        print("Exemplo: python test_rl.py --model-path rl/models/traffic_model.zip")
        # Record end time
        end_time = time.time()
        end_datetime = datetime.now()
        end_str = end_datetime.strftime("%H:%M:%S.%f")[:-3]
        duration = end_time - start_time
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        milliseconds = int((duration % 1) * 1000)
        print(f"\n{'='*60}")
        print(f"PROGRAM START TIME: {start_str}")
        print(f"PROGRAM END TIME: {end_str}")
        print(f"TOTAL DURATION: {hours:02d}h {minutes:02d}m {seconds:02d}s {milliseconds:03d}ms")
        print(f"TOTAL DURATION (seconds): {duration:.6f}")
        print(f"{'='*60}\n")
        return

    # Determine heuristic and duration
    heuristica = CONFIG.HEURISTICA_ATIVA
    duracao = None
    
    # Update RL model path if provided
    if args.rl_model:
        CONFIG.RL_MODEL_PATH = args.rl_model
    
    if '--vertical-horizontal' in sys.argv:
        heuristica = TipoHeuristica.VERTICAL_HORIZONTAL
        duracao = args.vertical_horizontal
    elif '--random' in sys.argv:
        heuristica = TipoHeuristica.RANDOM_OPEN_CLOSE
        duracao = args.random
    elif '--llm' in sys.argv:
        heuristica = TipoHeuristica.LLM_HEURISTICA
        duracao = args.llm
    elif '--adaptive' in sys.argv:
        heuristica = TipoHeuristica.ADAPTATIVA_DENSIDADE
        duracao = args.adaptive
    elif '--rl' in sys.argv:
        heuristica = TipoHeuristica.REINFORCEMENT_LEARNING
        duracao = args.rl
    elif '--manual' in sys.argv:
        heuristica = TipoHeuristica.MANUAL
        duracao = args.manual
        
    # Execute directly in GUI mode (headless is gone)
    executar_modo_gui(heuristica, duracao, args.rows, args.cols, args.engine)
    
    # Record end time
    end_time = time.time()
    end_datetime = datetime.now()
    end_str = end_datetime.strftime("%H:%M:%S.%f")[:-3]  # Hours:Minutes:Seconds.Milliseconds
    duration = end_time - start_time
    
    # Calculate hours, minutes, seconds, milliseconds
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = int(duration % 60)
    milliseconds = int((duration % 1) * 1000)
    
    print(f"\n{'='*60}")
    print(f"PROGRAM START TIME: {start_str}")
    print(f"PROGRAM END TIME: {end_str}")
    print(f"TOTAL DURATION: {hours:02d}h {minutes:02d}m {seconds:02d}s {milliseconds:03d}ms")
    print(f"TOTAL DURATION (seconds): {duration:.6f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
