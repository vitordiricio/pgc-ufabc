#!/bin/bash

# Create directories
mkdir -p rl/models

echo "=================================================="
echo "Training Simple Model (Fast, basic parameters)"
echo "=================================================="
python train_rl.py \
    --timesteps 50000 \
    --save-path rl/models/simple.zip \
    --n-steps 1024 \
    --batch-size 32 \
    --n-epochs 5 \
    --learning-rate 0.0005

echo ""
echo "=================================================="
echo "Training Middle Model (Balanced)"
echo "=================================================="
python train_rl.py \
    --timesteps 150000 \
    --save-path rl/models/middle.zip \
    --n-steps 2048 \
    --batch-size 64 \
    --n-epochs 10 \
    --learning-rate 0.0003

echo ""
echo "=================================================="
echo "Training Best Model (Optimized for performance)"
echo "=================================================="
python train_rl.py \
    --timesteps 300000 \
    --save-path rl/models/best.zip \
    --n-steps 4096 \
    --batch-size 128 \
    --n-epochs 20 \
    --learning-rate 0.0001 \
    --gamma 0.995

echo ""
echo "=================================================="
echo "Training Complete!"
echo "=================================================="

