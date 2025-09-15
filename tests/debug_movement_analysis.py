#!/usr/bin/env python3
"""
Análise de movimento de veículos - identifica padrões de travamento
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from simulacao import Simulacao
from configuracao import CONFIG

def debug_movement_analysis():
    """Análise detalhada do movimento dos veículos"""
    print("🔍 Iniciando análise de movimento...")
    print("Executando por 1000 frames em velocidade máxima...")
    
    # Configuração para velocidade máxima
    CONFIG.FPS = 1000
    CONFIG.DT = 0.016
    
    # Inicializa pygame
    pygame.init()
    
    # Cria simulação
    simulacao = Simulacao()
    
    # Dados de análise
    veiculo_data = {}
    collision_events = []
    
    # Executa por 1000 frames
    for frame in range(1000):
        # Atualiza simulação
        simulacao.atualizar(CONFIG.DT)
        
        # Analisa cada veículo
        for veiculo in simulacao.malha.veiculos:
            if not veiculo.ativo:
                continue
                
            vid = veiculo.id
            if vid not in veiculo_data:
                veiculo_data[vid] = {
                    'positions': [],
                    'velocities': [],
                    'accelerations': [],
                    'frames_stopped': 0,
                    'last_position': None
                }
            
            # Registra dados
            veiculo_data[vid]['positions'].append(veiculo.posicao.copy())
            veiculo_data[vid]['velocities'].append(veiculo.velocidade)
            veiculo_data[vid]['accelerations'].append(veiculo.aceleracao_atual)
            
            # Verifica se está parado
            if veiculo.velocidade < 0.1:
                veiculo_data[vid]['frames_stopped'] += 1
            else:
                veiculo_data[vid]['frames_stopped'] = 0
            
            # Verifica se mudou de posição
            if veiculo_data[vid]['last_position'] is not None:
                dx = veiculo.posicao[0] - veiculo_data[vid]['last_position'][0]
                dy = veiculo.posicao[1] - veiculo_data[vid]['last_position'][1]
                distance_moved = (dx**2 + dy**2)**0.5
                
                if distance_moved < 0.1 and veiculo.velocidade > 0.1:
                    print(f"⚠️ Veículo {vid} com velocidade {veiculo.velocidade:.2f} mas não se moveu!")
                    print(f"   Posição: {veiculo.posicao}")
                    print(f"   Aceleração: {veiculo.aceleracao_atual}")
                    print(f"   Direção: {veiculo.direcao.name}")
                    print(f"   Faixa: {veiculo.faixa_id}")
                    print()
            
            veiculo_data[vid]['last_position'] = veiculo.posicao.copy()
        
        # Verifica colisões
        for i, veiculo1 in enumerate(simulacao.malha.veiculos):
            if not veiculo1.ativo:
                continue
            for j, veiculo2 in enumerate(simulacao.malha.veiculos):
                if i >= j or not veiculo2.ativo:
                    continue
                if veiculo1.rect.colliderect(veiculo2.rect):
                    collision_events.append({
                        'frame': frame,
                        'veiculo1': veiculo1.id,
                        'veiculo2': veiculo2.id,
                        'pos1': veiculo1.posicao.copy(),
                        'pos2': veiculo2.posicao.copy(),
                        'vel1': veiculo1.velocidade,
                        'vel2': veiculo2.velocidade
                    })
    
    # Análise dos dados
    print("=" * 60)
    print("ANÁLISE DE MOVIMENTO")
    print("=" * 60)
    
    # Veículos que ficaram parados por muito tempo
    stuck_vehicles = []
    for vid, data in veiculo_data.items():
        if data['frames_stopped'] > 50:  # Parado por mais de 50 frames
            stuck_vehicles.append((vid, data['frames_stopped']))
    
    if stuck_vehicles:
        print(f"Veículos que ficaram parados por muito tempo:")
        for vid, frames in sorted(stuck_vehicles, key=lambda x: x[1], reverse=True):
            print(f"  - Veículo {vid}: {frames} frames parado")
    
    # Análise de colisões
    print(f"\nTotal de eventos de colisão: {len(collision_events)}")
    
    if collision_events:
        print("Primeiros 5 eventos de colisão:")
        for i, event in enumerate(collision_events[:5]):
            print(f"{i+1}. Frame {event['frame']}: Veículos {event['veiculo1']} e {event['veiculo2']}")
            print(f"   Posições: {event['pos1']} e {event['pos2']}")
            print(f"   Velocidades: {event['vel1']:.2f} e {event['vel2']:.2f}")
    
    # Análise de padrões de movimento
    print(f"\nAnálise de padrões de movimento:")
    for vid, data in veiculo_data.items():
        if len(data['velocities']) > 100:  # Só analisa veículos com dados suficientes
            avg_vel = sum(data['velocities']) / len(data['velocities'])
            max_vel = max(data['velocities'])
            min_vel = min(data['velocities'])
            
            if avg_vel < 0.5 and max_vel < 2.0:
                print(f"  - Veículo {vid}: Velocidade média {avg_vel:.2f}, max {max_vel:.2f}, min {min_vel:.2f}")
    
    pygame.quit()
    return len(stuck_vehicles), len(collision_events)

if __name__ == "__main__":
    debug_movement_analysis()
