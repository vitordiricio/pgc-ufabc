# Simulação para Otimização de Tráfego Urbano

Este projeto constitui o Projeto de Graduação em Computação (PGC) para a Universidade Federal do ABC (UFABC), implementando uma simulação de tráfego urbano com foco na dinâmica de cruzamentos controlados por semáforos, visando o estudo e otimização dos fluxos de veículos no ambiente urbano.

## Autores

- **Vitor Bobig Diricio**
- **Thiago Schwartz Machado**

## Objetivo

O objetivo deste projeto é desenvolver um sistema de simulação que permita analisar, avaliar e otimizar a dinâmica do tráfego urbano através da implementação de diferentes estratégias de controle de semáforos. A simulação possibilita a experimentação com diversos parâmetros para identificar configurações ótimas que minimizem congestionamentos e otimizem o fluxo de veículos.

## Descrição

A simulação modela um cruzamento de tráfego urbano com duas vias principais (Norte e Leste), controladas por semáforos sincronizados. Os veículos são gerados nas extremidades das vias e navegam pelo cruzamento respeitando os sinais de trânsito, adaptando sua velocidade conforme as condições do tráfego e presença de outros veículos.

O sistema permite analisar e otimizar parâmetros como:

- Temporização dos semáforos
- Taxas de fluxo de veículos
- Comportamento de aceleração e frenagem
- Impacto de diferentes configurações no fluxo geral do tráfego

## Funcionalidades

- **Semáforos sincronizados** - Sistema inteligente que coordena os semáforos para otimizar o fluxo
- **Física realista de veículos** - Aceleração, frenagem e comportamento natural dos veículos
- **Detecção de colisão** - Veículos reagem à presença de outros veículos à frente
- **Interface visual interativa** - Visualização em tempo real do sistema de tráfego
- **Configuração flexível** - Parâmetros ajustáveis para experimentação
- **Estatísticas em tempo real** - Contagem de veículos, tempos de espera e fluxo

## Instalação

1. Clone o repositório:

2. Instale as dependências usando o arquivo requirements.txt:

```bash
pip install -r requirements.txt
```

## Execução

Execute o simulador a partir do arquivo principal:

```bash
python main.py
```

### Controles

- **ESC** - Sair da simulação
- **ESPAÇO** - Pausar/Continuar
- **R** - Reiniciar simulação
- **+/-** - Alterar velocidade da simulação
