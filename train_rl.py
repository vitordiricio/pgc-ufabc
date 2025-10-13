"""
Training script for RL traffic control agent.
Simple command-line interface for training.
"""

import argparse
import os
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.monitor import Monitor

from rl import TrafficRLEnvironment, RLTrafficAgent


def train_agent(timesteps: int = 100000, 
                save_path: str = "rl/models/traffic_model.zip",
                eval_freq: int = 10000):
    """Train RL agent for traffic control."""
    
    print("="*60)
    print("TRAINING RL TRAFFIC CONTROL AGENT")
    print("="*60)
    
    # Create environment
    print("Creating environment...")
    env = TrafficRLEnvironment()
    env = Monitor(env)
    
    # Create agent
    print("Creating RL agent...")
    agent = RLTrafficAgent()
    
    # Setup evaluation callback
    eval_callback = EvalCallback(
        env,
        best_model_save_path=os.path.dirname(save_path),
        log_path=os.path.join(os.path.dirname(save_path), "logs"),
        eval_freq=eval_freq,
        deterministic=True,
        render=False,
        verbose=1
    )
    
    # Train
    print(f"Training for {timesteps} timesteps...")
    print(f"Evaluation every {eval_freq} timesteps...")
    print("-" * 60)
    
    agent.train(
        total_timesteps=timesteps,
        callback=eval_callback
    )
    
    # Save final model
    print("-" * 60)
    print("Saving final model...")
    agent.save_model(save_path)
    
    # Evaluate final model
    print("Evaluating final model...")
    eval_results = agent.evaluate(env, n_episodes=5)
    
    print("="*60)
    print("TRAINING COMPLETED!")
    print("="*60)
    print(f"Final evaluation results:")
    print(f"  Mean reward: {eval_results['mean_reward']:.2f} ± {eval_results['std_reward']:.2f}")
    print(f"  Mean episode length: {eval_results['mean_length']:.0f} ± {eval_results['std_length']:.0f}")
    print(f"Model saved to: {save_path}")
    print("="*60)


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description="Train RL traffic control agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python train_rl.py --timesteps 100000
  python train_rl.py --timesteps 500000 --save-path rl/models/my_model.zip
  python train_rl.py --timesteps 1000000 --eval-freq 5000
        """
    )
    
    parser.add_argument('--timesteps', type=int, default=100000,
                       help='Number of training timesteps (default: 100000)')
    parser.add_argument('--save-path', type=str, default='rl/models/traffic_model.zip',
                       help='Path to save the trained model (default: rl/models/traffic_model.zip)')
    parser.add_argument('--eval-freq', type=int, default=10000,
                       help='Evaluation frequency in timesteps (default: 10000)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.timesteps <= 0:
        print("Error: timesteps must be positive")
        return 1
        
    if args.eval_freq <= 0:
        print("Error: eval-freq must be positive")
        return 1
    
    try:
        train_agent(
            timesteps=args.timesteps,
            save_path=args.save_path,
            eval_freq=args.eval_freq
        )
        return 0
    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
        return 1
    except Exception as e:
        print(f"Error during training: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

