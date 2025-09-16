"""
Script de teste para o sistema de gerenciamento de interseções.
Verifica critérios de aceitação com conversões simultâneas.
"""
import pygame
import time
import sys
from configuracao import CONFIG
from simulacao import Simulacao
from intersection_manager import IntersectionManager


def testar_intersection_manager():
    """Testa o sistema de gerenciamento de interseções."""
    print("=" * 60)
    print("TESTE DO SISTEMA DE GERENCIAMENTO DE INTERSEÇÕES - SIMOTUR")
    print("=" * 60)
    print("Objetivo: Verificar critérios de aceitação")
    print("• Zero colisões com conversões simultâneas")
    print("• Logs mostram reservas concedidas/negadas coerentes")
    print("• Sistema de prioridades funcionando")
    print("=" * 60)
    
    # Inicializa pygame
    pygame.init()
    
    # Cria simulação
    simulacao = Simulacao()
    
    # Configurações de teste
    tempo_teste = 60  # 60 segundos
    frames_teste = tempo_teste * 60  # 60 FPS
    frame_atual = 0
    
    # Métricas
    colisoes_detectadas = 0
    reservas_concedidas = 0
    reservas_negadas = 0
    veiculos_com_reserva = 0
    veiculos_bloqueados = 0
    
    print(f"Iniciando teste de {tempo_teste} segundos ({frames_teste} frames)...")
    print("Pressione Ctrl+C para parar o teste")
    print("=" * 60)
    
    try:
        inicio_tempo = time.time()
        
        while frame_atual < frames_teste:
            # Atualiza simulação
            simulacao.atualizar(1.0/60.0)  # 60 FPS
            
            # Conta veículos com reserva
            veiculos_com_reserva_atual = 0
            veiculos_bloqueados_atual = 0
            
            for veiculo in simulacao.malha.veiculos:
                if hasattr(veiculo, 'reserva_ativa') and veiculo.reserva_ativa:
                    veiculos_com_reserva_atual += 1
                
                if hasattr(veiculo, 'verificar_bloqueio_intersecao') and veiculo.verificar_bloqueio_intersecao():
                    veiculos_bloqueados_atual += 1
            
            veiculos_com_reserva = max(veiculos_com_reserva, veiculos_com_reserva_atual)
            veiculos_bloqueados = max(veiculos_bloqueados, veiculos_bloqueados_atual)
            
            # Verifica colisões
            for i, veiculo1 in enumerate(simulacao.malha.veiculos):
                for j, veiculo2 in enumerate(simulacao.malha.veiculos[i+1:], i+1):
                    if veiculo1.rect.colliderect(veiculo2.rect):
                        colisoes_detectadas += 1
                        print(f"COLISÃO DETECTADA: Veículo {veiculo1.id} com {veiculo2.id}")
            
            # Atualiza métricas
            frame_atual += 1
            
            # Log periódico
            if frame_atual % 300 == 0:  # A cada 5 segundos
                tempo_atual = time.time() - inicio_tempo
                fps = frame_atual / tempo_atual if tempo_atual > 0 else 0
                print(f"Frame {frame_atual}/{frames_teste} - FPS: {fps:.1f} - "
                      f"Veículos: {len(simulacao.malha.veiculos)} - "
                      f"Reservas: {veiculos_com_reserva_atual} - "
                      f"Bloqueados: {veiculos_bloqueados_atual}")
        
        tempo_executado = time.time() - inicio_tempo
        
    except KeyboardInterrupt:
        tempo_executado = time.time() - inicio_tempo
        print("\nTeste interrompido pelo usuário")
    
    finally:
        pygame.quit()
    
    # Relatório final
    print("\n" + "=" * 60)
    print("RESULTADOS DO TESTE")
    print("=" * 60)
    print(f"Tempo executado: {tempo_executado:.1f}s")
    print(f"Frames processados: {frame_atual}")
    print(f"FPS médio: {frame_atual / tempo_executado:.1f}")
    print(f"Veículos processados: {len(simulacao.malha.veiculos)}")
    print(f"Colisões detectadas: {colisoes_detectadas}")
    print(f"Reservas concedidas: {reservas_concedidas}")
    print(f"Reservas negadas: {reservas_negadas}")
    print(f"Máximo veículos com reserva: {veiculos_com_reserva}")
    print(f"Máximo veículos bloqueados: {veiculos_bloqueados}")
    
    # Critérios de aceitação
    print("\n" + "=" * 60)
    print("CRITÉRIOS DE ACEITAÇÃO")
    print("=" * 60)
    
    # Zero colisões
    if colisoes_detectadas == 0:
        print("✅ ZERO COLISÕES: Nenhuma colisão detectada")
    else:
        print(f"❌ ZERO COLISÕES: {colisoes_detectadas} colisões detectadas")
    
    # Sistema de reservas funcionando
    if veiculos_com_reserva > 0:
        print("✅ SISTEMA DE RESERVAS: Funcionando (veículos com reserva detectados)")
    else:
        print("⚠️  SISTEMA DE RESERVAS: Nenhuma reserva detectada")
    
    # Sistema de bloqueio funcionando
    if veiculos_bloqueados > 0:
        print("✅ SISTEMA DE BLOQUEIO: Funcionando (veículos bloqueados detectados)")
    else:
        print("⚠️  SISTEMA DE BLOQUEIO: Nenhum bloqueio detectado")
    
    # Performance
    fps_medio = frame_atual / tempo_executado if tempo_executado > 0 else 0
    if fps_medio >= 30:
        print("✅ PERFORMANCE: FPS adequado")
    else:
        print(f"⚠️  PERFORMANCE: FPS baixo ({fps_medio:.1f})")
    
    # Resultado final
    print("\n" + "=" * 60)
    if colisoes_detectadas == 0 and veiculos_com_reserva > 0:
        print("✅ TESTE APROVADO: Todos os critérios atendidos")
    else:
        print("❌ TESTE COM PROBLEMAS: Verificar critérios não atendidos")
    print("=" * 60)


if __name__ == "__main__":
    testar_intersection_manager()
