"""
Testing script for RL traffic control agent.
Simple evaluation and comparison with other heuristics.
"""

import argparse
import time
from rl import TrafficRLEnvironment, RLTrafficAgent
from simulacao import SimulacaoHeadless
from configuracao import TipoHeuristica


def test_rl_agent(model_path: str = "rl/models/traffic_model.zip", 
                  duration: int = 300,
                  episodes: int = 3):
    """Test RL agent performance."""
    
    print("="*60)
    print("TESTING RL TRAFFIC CONTROL AGENT")
    print("="*60)
    
    try:
        # Load agent
        print(f"Loading RL agent from {model_path}...")
        agent = RLTrafficAgent(model_path=model_path)
        
        # Test on environment
        print(f"Testing on {episodes} episodes of {duration} seconds each...")
        print("-" * 60)
        
        total_rewards = []
        total_throughputs = []
        total_wait_times = []
        
        for episode in range(episodes):
            print(f"Episode {episode + 1}/{episodes}")
            
            env = TrafficRLEnvironment({'max_steps': duration})
            obs, _ = env.reset()
            episode_reward = 0
            done = False
            step = 0
            
            while not done:
                action = agent.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated
                episode_reward += reward
                step += 1
                
                if step % 60 == 0:  # Print every minute
                    print(f"  Step {step}/{duration}: Reward={episode_reward:.2f}, "
                          f"Vehicles={info['total_vehicles']}, "
                          f"Wait={info['average_wait_time']:.1f}s")
            
            total_rewards.append(episode_reward)
            total_throughputs.append(info['throughput'])
            total_wait_times.append(info['average_wait_time'])
            
            print(f"  Episode {episode + 1} completed: Reward={episode_reward:.2f}")
            print()
        
        # Calculate averages
        avg_reward = sum(total_rewards) / len(total_rewards)
        avg_throughput = sum(total_throughputs) / len(total_throughputs)
        avg_wait_time = sum(total_wait_times) / len(total_wait_times)
        
        print("="*60)
        print("RL AGENT TEST RESULTS")
        print("="*60)
        print(f"Average reward: {avg_reward:.2f}")
        print(f"Average throughput: {avg_throughput:.2f}")
        print(f"Average wait time: {avg_wait_time:.2f}s")
        print("="*60)
        
        return {
            'avg_reward': avg_reward,
            'avg_throughput': avg_throughput,
            'avg_wait_time': avg_wait_time
        }
        
    except FileNotFoundError:
        print(f"Error: Model file not found at {model_path}")
        print("Please train the model first using: python train_rl.py")
        return None
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_with_baseline(duration: int = 300):
    """Compare RL agent with baseline heuristics."""
    
    print("="*60)
    print("COMPARING RL WITH BASELINE HEURISTICS")
    print("="*60)
    
    # Test baseline heuristics
    baseline_results = {}
    
    for heuristic in [TipoHeuristica.VERTICAL_HORIZONTAL, 
                      TipoHeuristica.RANDOM_OPEN_CLOSE,
                      TipoHeuristica.ADAPTATIVA_DENSIDADE]:
        
        print(f"Testing {heuristic.name}...")
        
        try:
            simulacao = SimulacaoHeadless(
                heuristica=heuristic,
                duracao_segundos=duration,
                verbose=False
            )
            
            start_time = time.time()
            simulacao.executar()
            end_time = time.time()
            
            # Get final statistics
            estatisticas = simulacao.malha.obter_estatisticas()
            
            baseline_results[heuristic.name] = {
                'veiculos_concluidos': estatisticas['veiculos_concluidos'],
                'tempo_viagem_medio': estatisticas['tempo_viagem_medio'],
                'tempo_parado_medio': estatisticas['tempo_parado_medio'],
                'throughput_por_minuto': estatisticas.get('throughput_por_minuto', 0),
                'execution_time': end_time - start_time
            }
            
            print(f"  Completed: {estatisticas['veiculos_concluidos']} vehicles, "
                  f"Travel time: {estatisticas['tempo_viagem_medio']:.1f}s")
            
        except Exception as e:
            print(f"  Error testing {heuristic.name}: {e}")
            baseline_results[heuristic.name] = None
    
    # Test RL agent
    print("\nTesting RL agent...")
    rl_results = test_rl_agent(duration=duration, episodes=1)
    
    # Print comparison
    print("\n" + "="*60)
    print("COMPARISON RESULTS")
    print("="*60)
    
    if rl_results:
        print(f"{'Heuristic':<20} {'Vehicles':<10} {'Travel Time':<12} {'Throughput':<12}")
        print("-" * 60)
        
        for name, results in baseline_results.items():
            if results:
                print(f"{name:<20} {results['veiculos_concluidos']:<10} "
                      f"{results['tempo_viagem_medio']:<12.1f} "
                      f"{results['throughput_por_minuto']:<12.1f}")
        
        print(f"{'RL Agent':<20} {'N/A':<10} {'N/A':<12} {rl_results['avg_throughput']:<12.1f}")
        print("-" * 60)
    
    return baseline_results, rl_results


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description="Test RL traffic control agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_rl.py --model-path rl/models/traffic_model.zip
  python test_rl.py --duration 600 --episodes 5
  python test_rl.py --compare --duration 300
        """
    )
    
    parser.add_argument('--model-path', type=str, default='rl/models/traffic_model.zip',
                       help='Path to the trained model (default: rl/models/traffic_model.zip)')
    parser.add_argument('--duration', type=int, default=300,
                       help='Test duration in seconds (default: 300)')
    parser.add_argument('--episodes', type=int, default=3,
                       help='Number of test episodes (default: 3)')
    parser.add_argument('--compare', action='store_true',
                       help='Compare with baseline heuristics')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.duration <= 0:
        print("Error: duration must be positive")
        return 1
        
    if args.episodes <= 0:
        print("Error: episodes must be positive")
        return 1
    
    try:
        if args.compare:
            compare_with_baseline(duration=args.duration)
        else:
            test_rl_agent(
                model_path=args.model_path,
                duration=args.duration,
                episodes=args.episodes
            )
        return 0
    except KeyboardInterrupt:
        print("\nTesting interrupted by user")
        return 1
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

