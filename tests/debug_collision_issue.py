"""
Script de debug para identificar o problema de colisões no simulador.
Este script executa a simulação e monitora quando veículos colidem e congelam.
"""
import pygame
import sys
import os
import time
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configuracao import CONFIG
from simulacao import Simulacao
from veiculo import Veiculo
from cruzamento import MalhaViaria


class CollisionDebugger:
    """Debugger para monitorar colisões em tempo real."""
    
    def __init__(self):
        self.collision_log = []
        self.frozen_vehicles = set()
        self.frame_count = 0
        
    def log_collision(self, veiculo1, veiculo2, frame):
        """Registra uma colisão detectada."""
        collision_info = {
            'frame': frame,
            'timestamp': datetime.now().strftime("%H:%M:%S.%f")[:-3],
            'veiculo1': {
                'id': veiculo1.id,
                'posicao': veiculo1.posicao.copy(),
                'velocidade': veiculo1.velocidade,
                'direcao': veiculo1.direcao.name,
                'faixa': getattr(veiculo1, 'faixa_id', 'N/A'),
                'em_curva': getattr(veiculo1, 'em_curva', False),
                'em_troca_faixa': getattr(veiculo1, 'em_troca_faixa', False)
            },
            'veiculo2': {
                'id': veiculo2.id,
                'posicao': veiculo2.posicao.copy(),
                'velocidade': veiculo2.velocidade,
                'direcao': veiculo2.direcao.name,
                'faixa': getattr(veiculo2, 'faixa_id', 'N/A'),
                'em_curva': getattr(veiculo2, 'em_curva', False),
                'em_troca_faixa': getattr(veiculo2, 'em_troca_faixa', False)
            }
        }
        self.collision_log.append(collision_info)
        print(f"🚨 COLISÃO DETECTADA no frame {frame}:")
        print(f"   Veículo {veiculo1.id} ({veiculo1.direcao.name}) em {veiculo1.posicao}")
        print(f"   Veículo {veiculo2.id} ({veiculo2.direcao.name}) em {veiculo2.posicao}")
        print(f"   Distância: {self._calcular_distancia(veiculo1.posicao, veiculo2.posicao):.2f}")
        print()
    
    def log_frozen_vehicle(self, veiculo, frame):
        """Registra um veículo que congelou."""
        if veiculo.id not in self.frozen_vehicles:
            self.frozen_vehicles.add(veiculo.id)
            print(f"❄️ VEÍCULO CONGELADO no frame {frame}:")
            print(f"   ID: {veiculo.id}, Posição: {veiculo.posicao}")
            print(f"   Velocidade: {veiculo.velocidade}, Aceleração: {veiculo.aceleracao_atual}")
            print(f"   Direção: {veiculo.direcao.name}, Faixa: {getattr(veiculo, 'faixa_id', 'N/A')}")
            print()
    
    def _calcular_distancia(self, pos1, pos2):
        """Calcula distância euclidiana entre duas posições."""
        return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5
    
    def check_collisions(self, veiculos, frame):
        """Verifica colisões entre todos os veículos."""
        for i, veiculo1 in enumerate(veiculos):
            if not veiculo1.ativo:
                continue
                
            for j, veiculo2 in enumerate(veiculos[i+1:], i+1):
                if not veiculo2.ativo:
                    continue
                
                # Verifica colisão usando o método do veículo
                if veiculo1.verificar_colisao_completa([veiculo2]):
                    self.log_collision(veiculo1, veiculo2, frame)
                
                # Verifica se veículos estão muito próximos (possível congelamento)
                distancia = self._calcular_distancia(veiculo1.posicao, veiculo2.posicao)
                if distancia < 30 and veiculo1.velocidade < 0.1 and veiculo2.velocidade < 0.1:
                    self.log_frozen_vehicle(veiculo1, frame)
                    self.log_frozen_vehicle(veiculo2, frame)
    
    def print_summary(self):
        """Imprime resumo das colisões detectadas."""
        print("\n" + "="*60)
        print("RESUMO DE COLISÕES DETECTADAS")
        print("="*60)
        print(f"Total de colisões: {len(self.collision_log)}")
        print(f"Veículos congelados: {len(self.frozen_vehicles)}")
        
        if self.collision_log:
            print("\nPrimeiras 5 colisões:")
            for i, col in enumerate(self.collision_log[:5]):
                print(f"{i+1}. Frame {col['frame']} - Veículos {col['veiculo1']['id']} e {col['veiculo2']['id']}")
        
        print("\nVeículos congelados:")
        for veiculo_id in list(self.frozen_vehicles)[:10]:
            print(f"  - Veículo {veiculo_id}")


def run_collision_debug():
    """Executa a simulação com debug de colisões."""
    print("Iniciando debug de colisões...")
    print("Pressione Ctrl+C para parar e ver o resumo")
    
    # Inicializa Pygame
    pygame.init()
    
    try:
        # Cria simulação
        simulacao = Simulacao(linhas=2, colunas=2)
        debugger = CollisionDebugger()
        
        # Configurações para debug
        CONFIG.MOSTRAR_INFO_VEICULO = True
        CONFIG.TAXA_GERACAO_VEICULO = 0.05  # Mais veículos para testar
        
        clock = pygame.time.Clock()
        frame_count = 0
        max_frames = 3000  # Limite de frames para debug
        
        print(f"Executando por {max_frames} frames...")
        
        while simulacao.rodando and frame_count < max_frames:
            # Processa eventos
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    simulacao.rodando = False
                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        simulacao.rodando = False
            
            # Atualiza simulação
            if not simulacao.pausado:
                simulacao.atualizar(1.0 / CONFIG.FPS)
                
                # Verifica colisões
                debugger.check_collisions(simulacao.malha.veiculos, frame_count)
                
                frame_count += 1
                
                # Mostra progresso a cada 500 frames
                if frame_count % 500 == 0:
                    print(f"Frame {frame_count}: {len(simulacao.malha.veiculos)} veículos ativos")
            
            # Renderiza
            simulacao.renderizar()
            clock.tick(CONFIG.FPS)
        
        # Imprime resumo
        debugger.print_summary()
        
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário")
        debugger.print_summary()
    except Exception as e:
        print(f"Erro durante execução: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pygame.quit()


def test_vehicle_creation_and_movement():
    """Testa criação e movimento básico de veículos."""
    print("Testando criação e movimento de veículos...")
    
    pygame.init()
    
    try:
        # Cria veículos de teste
        veiculo1 = Veiculo(CONFIG.DIRECOES_PERMITIDAS[0], (100, 100), (0, 0))
        veiculo2 = Veiculo(CONFIG.DIRECOES_PERMITIDAS[0], (100, 150), (0, 0))
        
        print(f"Veículo 1: posição {veiculo1.posicao}, velocidade {veiculo1.velocidade}")
        print(f"Veículo 2: posição {veiculo2.posicao}, velocidade {veiculo2.velocidade}")
        
        # Testa detecção de colisão
        veiculo1._atualizar_rect()
        veiculo2._atualizar_rect()
        
        colisao = veiculo1.verificar_colisao_completa([veiculo2])
        print(f"Colisão detectada: {colisao}")
        
        # Testa movimento
        veiculo1.velocidade = 1.0
        veiculo1.aceleracao_atual = 0.1
        
        print("Movendo veículo 1...")
        for i in range(10):
            veiculo1.atualizar(1.0, [veiculo2])
            print(f"  Frame {i+1}: posição {veiculo1.posicao}, velocidade {veiculo1.velocidade}")
            
            # Verifica colisão a cada frame
            veiculo1._atualizar_rect()
            colisao = veiculo1.verificar_colisao_completa([veiculo2])
            if colisao:
                print(f"  🚨 COLISÃO detectada no frame {i+1}!")
                break
        
    except Exception as e:
        print(f"Erro no teste: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pygame.quit()


if __name__ == "__main__":
    print("Escolha o teste:")
    print("1. Debug de colisões em tempo real")
    print("2. Teste básico de criação e movimento")
    
    escolha = input("Digite 1 ou 2: ").strip()
    
    if escolha == "1":
        run_collision_debug()
    elif escolha == "2":
        test_vehicle_creation_and_movement()
    else:
        print("Opção inválida")
