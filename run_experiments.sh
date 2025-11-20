#!/bin/bash
# run_experiments.sh
# Script para executar bateria COMPLETA de experimentos (~10h)

# Ativa o ambiente virtual
source .venv/bin/activate

# Cria diretórios necessários
mkdir -p relatorios
mkdir -p logs

# Arquivo de log para erros
ERROR_LOG="logs/failed_experiments.log"
echo "Data: $(date)" > "$ERROR_LOG"

# Configurações Gerais
# 1, 3, 5, 7, 10 minutos
DURATIONS=(60 180 300 420 600)
GRID_SIZES=("2x2" "3x3" "4x4")

# ------------------------------------------------------------------
# Função para executar um experimento
# ------------------------------------------------------------------
run_experiment() {
    local cmd="$1"
    local name="$2"
    
    echo "----------------------------------------------------------------"
    echo "Iniciando: $name"
    echo "Comando: $cmd"
    
    # Executa o comando
    $cmd
    
    # Verifica status de saída
    if [ $? -eq 0 ]; then
        echo "✓ SUCESSO: $name"
    else
        echo "✗ FALHA: $name"
        echo "$cmd" >> "$ERROR_LOG"
    fi
}

# ------------------------------------------------------------------
# 1. Outras Heurísticas (Baseline: Random, Vertical/Horizontal, Adaptive)
# ------------------------------------------------------------------
echo ""
echo ">>> INICIANDO BATERIA BASELINES (Start)"
BASELINES=("random" "adaptive" "vertical-horizontal")

for heuristic in "${BASELINES[@]}"; do
    for duration in "${DURATIONS[@]}"; do
        for grid in "${GRID_SIZES[@]}"; do
            IFS='x' read -r rows cols <<< "$grid"
            outfile="${heuristic}_${duration}s_${grid}.json"
            
            cmd="python main.py --$heuristic $duration --rows $rows --cols $cols --output $outfile"
            run_experiment "$cmd" "Baseline $heuristic ($grid - ${duration}s)"
        done
    done
done

# ------------------------------------------------------------------
# 2. Bateria de Testes RL (Simple vs Middle vs Best)
# ------------------------------------------------------------------
echo ""
echo ">>> INICIANDO BATERIA RL (Modelos Diferentes)"
# Certifique-se que os arquivos simple.zip, middle.zip e best.zip existem em rl/models/
RL_MODELS=("simple" "middle" "best")

for model in "${RL_MODELS[@]}"; do
    for duration in "${DURATIONS[@]}"; do
        for grid in "${GRID_SIZES[@]}"; do
            IFS='x' read -r rows cols <<< "$grid"
            
            model_path="rl/models/${model}.zip"
            outfile="rl_${model}_${duration}s_${grid}.json"
            
            # Verifica se modelo existe antes de tentar
            if [ -f "$model_path" ]; then
                cmd="python main.py --rl $duration --rl-model $model_path --rows $rows --cols $cols --output $outfile"
                run_experiment "$cmd" "RL $model ($grid - ${duration}s)"
            else
                echo "⚠️  AVISO: Modelo não encontrado: $model_path (Pulando)"
            fi
        done
    done
done

# ------------------------------------------------------------------
# 3. Bateria de Testes LLM (OpenAI vs Ollama)
# ------------------------------------------------------------------
echo ""
echo ">>> INICIANDO BATERIA LLM (OpenAI vs Ollama)"
ENGINES=("ollama" "openai")

for engine in "${ENGINES[@]}"; do
    for duration in "${DURATIONS[@]}"; do
        for grid in "${GRID_SIZES[@]}"; do
            IFS='x' read -r rows cols <<< "$grid"
            outfile="llm_${engine}_${duration}s_${grid}.json"
            
            cmd="python main.py --llm $duration --engine $engine --rows $rows --cols $cols --output $outfile"
            run_experiment "$cmd" "LLM $engine ($grid - ${duration}s)"
        done
    done
done

echo ""
echo "=========================================="
echo "BATERIA DE EXPERIMENTOS CONCLUÍDA"
echo "=========================================="
echo "Verifique $ERROR_LOG para experimentos que falharam."
echo "Total de relatórios gerados: $(ls relatorios/*.json 2>/dev/null | wc -l)"