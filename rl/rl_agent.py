"""
RL Agent implementation for traffic control.
Simple wrapper around Stable-Baselines3 PPO.
"""

import numpy as np
import os
from typing import Dict, Any, Optional
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from .rl_environment import TrafficRLEnvironment


class RLTrafficAgent:
    """RL Agent for traffic control using PPO."""
    
    def __init__(self, 
                 config: Optional[Dict[str, Any]] = None,
                 model_path: Optional[str] = None):
        self.config = config or self._get_default_config()
        self.model = None
        self.model_path = model_path or "rl/models/traffic_model.zip"
        
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
        else:
            self._create_model()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for PPO."""
        return {
            'learning_rate': 3e-4,
            'n_steps': 2048,
            'batch_size': 64,
            'n_epochs': 10,
            'gamma': 0.99,
            'gae_lambda': 0.95,
            'clip_range': 0.2,
            'ent_coef': 0.0,
            'vf_coef': 0.5,
            'max_grad_norm': 0.5,
            'verbose': 1
        }
            
    def _create_model(self):
        """Create new PPO model."""
        env = TrafficRLEnvironment()
        
        self.model = PPO(
            "MlpPolicy",
            env,
            learning_rate=self.config['learning_rate'],
            n_steps=self.config['n_steps'],
            batch_size=self.config['batch_size'],
            n_epochs=self.config['n_epochs'],
            gamma=self.config['gamma'],
            gae_lambda=self.config['gae_lambda'],
            clip_range=self.config['clip_range'],
            ent_coef=self.config['ent_coef'],
            vf_coef=self.config['vf_coef'],
            max_grad_norm=self.config['max_grad_norm'],
            verbose=self.config['verbose']
        )
        
    def train(self, 
              total_timesteps: int = 100000,
              callback: Optional[BaseCallback] = None,
              **kwargs):
        """Train the RL model."""
        if self.model is None:
            self._create_model()
            
        print(f"Training PPO agent for {total_timesteps} timesteps...")
        self.model.learn(
            total_timesteps=total_timesteps,
            callback=callback,
            **kwargs
        )
        print("Training completed!")
        
    def predict(self, observation: np.ndarray, deterministic: bool = True) -> np.ndarray:
        """Predict action for given observation."""
        if self.model is None:
            raise ValueError("Model not loaded or created")
            
        action, _states = self.model.predict(observation, deterministic=deterministic)
        return action
        
    def save_model(self, path: Optional[str] = None):
        """Save trained model."""
        if self.model is None:
            raise ValueError("No model to save")
            
        save_path = path or self.model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        self.model.save(save_path)
        print(f"Model saved to {save_path}")
        
    def load_model(self, path: str):
        """Load trained model."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")
            
        self.model = PPO.load(path)
        self.model_path = path
        print(f"Model loaded from {path}")
        
    def evaluate(self, env: TrafficRLEnvironment, n_episodes: int = 5) -> Dict[str, float]:
        """Evaluate the model on the environment."""
        if self.model is None:
            raise ValueError("Model not loaded")
            
        episode_rewards = []
        episode_lengths = []
        
        for episode in range(n_episodes):
            obs, _ = env.reset()
            episode_reward = 0
            episode_length = 0
            done = False
            
            while not done:
                action = self.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated
                episode_reward += reward
                episode_length += 1
                
            episode_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
            
        return {
            'mean_reward': np.mean(episode_rewards),
            'std_reward': np.std(episode_rewards),
            'mean_length': np.mean(episode_lengths),
            'std_length': np.std(episode_lengths)
        }
