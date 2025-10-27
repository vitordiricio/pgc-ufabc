#!/bin/bash
# run_experiments.sh
# Script para executar experimentos com diferentes heurísticas

# Ativa o ambiente virtual
source .venv/bin/activate

# Cria diretório de relatórios se não existir
mkdir -p relatorios

# Configurações dos experimentos
HEURISTICS=("vertical-horizontal" "random" "adaptive" "rl")
DURATIONS=(60 120 180 240 300)  # 1min, 2min, 3min, 4min, 5min
GRID_SIZES=("2x2" "3x3" "4x4" "5x5")

# Contador de experimentos
total_experiments=$((${#HEURISTICS[@]} * ${#DURATIONS[@]} * ${#GRID_SIZES[@]}))
current_experiment=0

echo "=========================================="
echo "INICIANDO EXPERIMENTOS DE SIMULAÇÃO"
echo "=========================================="
echo "Total de experimentos: $total_experiments"
echo "Heurísticas: ${HEURISTICS[*]}"
echo "Durações: ${DURATIONS[*]}s"
echo "Grades: ${GRID_SIZES[*]}"
echo "=========================================="

for heuristic in "${HEURISTICS[@]}"; do
    for duration in "${DURATIONS[@]}"; do
        for grid in "${GRID_SIZES[@]}"; do
            current_experiment=$((current_experiment + 1))
            IFS='x' read -r rows cols <<< "$grid"
            
            echo ""
            echo "[$current_experiment/$total_experiments] Executando: $heuristic, ${duration}s, ${grid}"
            echo "Comando: python main.py --$heuristic $duration --rows $rows --cols $cols --output ${heuristic}_${duration}s_${grid}.json"
            
            # Executa o experimento
            python main.py --$heuristic $duration --rows $rows --cols $cols --output "${heuristic}_${duration}s_${grid}.json"
            
            # Verifica se o comando foi executado com sucesso
            if [ $? -eq 0 ]; then
                echo "✓ Experimento concluído com sucesso"
            else
                echo "✗ Erro no experimento"
            fi
        done
    done
done

echo ""
echo "=========================================="
echo "TODOS OS EXPERIMENTOS CONCLUÍDOS!"
echo "=========================================="
echo "Relatórios salvos em: relatorios/"
echo "Total de arquivos gerados: $(ls relatorios/*.json 2>/dev/null | wc -l)"