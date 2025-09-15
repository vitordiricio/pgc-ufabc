#!/usr/bin/env python3
"""
Debug rápido de colisões - executa em velocidade máxima
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
from simulacao import Simulacao
from configuracao import CONFIG

def debug_collisions_fast():
    """Debug rápido de colisões com velocidade máxima"""
    print("🚀 Iniciando debug RÁPIDO de colisões...")
    print("Executando em velocidade máxima por 3000 frames...")
    
    # Configuração para velocidade máxima
    CONFIG.FPS = 1000  # FPS muito alto para velocidade máxima
    CONFIG.DT = 0.016  # Delta time fixo
    
    # Inicializa pygame
    pygame.init()
    
    # Cria simulação
    simulacao = Simulacao()
    
    # Contadores
    total_colisoes = 0
    veiculos_congelados = set()
    colisoes_por_frame = {}
    
    # Executa por 3000 frames em velocidade máxima
    for frame in range(3000):
        # Atualiza simulação
        simulacao.atualizar(CONFIG.DT)
        
        # Verifica colisões
        colisoes_frame = 0
        for i, veiculo1 in enumerate(simulacao.malha.veiculos):
            if not veiculo1.ativo:
                continue
                
            for j, veiculo2 in enumerate(simulacao.malha.veiculos):
                if i >= j or not veiculo2.ativo:
                    continue
                    
                if veiculo1.rect.colliderect(veiculo2.rect):
                    colisoes_frame += 1
                    total_colisoes += 1
                    
                    # Calcula distância
                    dx = veiculo1.posicao[0] - veiculo2.posicao[0]
                    dy = veiculo1.posicao[1] - veiculo2.posicao[1]
                    distancia = (dx**2 + dy**2)**0.5
                    
                    print(f"🚨 COLISÃO DETECTADA no frame {frame}:")
                    print(f"   Veículo {veiculo1.id} ({veiculo1.direcao.name}) em {veiculo1.posicao}")
                    print(f"   Veículo {veiculo2.id} ({veiculo2.direcao.name}) em {veiculo2.posicao}")
                    print(f"   Distância: {distancia:.2f}")
                    print()
        
        # Verifica veículos congelados
        for veiculo in simulacao.malha.veiculos:
            if not veiculo.ativo:
                continue
            if veiculo.velocidade < 0.1 and frame > 100:  # Só conta após 100 frames
                veiculos_congelados.add(veiculo.id)
                if veiculo.id not in [v for v in veiculos_congelados if v != veiculo.id]:
                    print(f"❄️ VEÍCULO CONGELADO no frame {frame}:")
                    print(f"   ID: {veiculo.id}, Posição: {veiculo.posicao}")
                    print(f"   Velocidade: {veiculo.velocidade}, Aceleração: {veiculo.aceleracao_atual}")
                    print(f"   Direção: {veiculo.direcao.name}, Faixa: {veiculo.faixa_id}")
                    print()
        
        # Log a cada 500 frames
        if frame % 500 == 0:
            ativos = sum(1 for v in simulacao.malha.veiculos if v.ativo)
            print(f"Frame {frame}: {ativos} veículos ativos")
    
    # Resumo final
    print("=" * 60)
    print("RESUMO DE COLISÕES DETECTADAS")
    print("=" * 60)
    print(f"Total de colisões: {total_colisoes}")
    print(f"Veículos congelados: {len(veiculos_congelados)}")
    print()
    
    if total_colisoes > 0:
        print("Primeiras 5 colisões:")
        for i, (frame, info) in enumerate(list(colisoes_por_frame.items())[:5]):
            print(f"{i+1}. Frame {frame} - {info}")
    
    if veiculos_congelados:
        print(f"\nVeículos congelados:")
        for vid in sorted(veiculos_congelados):
            print(f"  - Veículo {vid}")
    
    pygame.quit()
    return total_colisoes, len(veiculos_congelados)

if __name__ == "__main__":
    debug_collisions_fast()
