#!/bin/bash
# Performance Benchmarking Script

set -e

echo "=========================================="
echo "LLM Performance Benchmark"
echo "=========================================="

RESULTS_DIR="$HOME/llm-benchmarks"
mkdir -p "$RESULTS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="$RESULTS_DIR/benchmark_${TIMESTAMP}.txt"

# System info
echo "=== System Information ===" | tee "$RESULTS_FILE"
echo "Date: $(date)" | tee -a "$RESULTS_FILE"
echo "macOS: $(sw_vers -productVersion)" | tee -a "$RESULTS_FILE"
echo "Chip: $(sysctl -n machdep.cpu.brand_string)" | tee -a "$RESULTS_FILE"
echo "Memory: $(( $(sysctl -n hw.memsize) / 1073741824 ))GB" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# Get installed models
MODELS=$(ollama list | tail -n +2 | awk '{print $1}')

if [ -z "$MODELS" ]; then
    echo "No models installed. Run provisioning first."
    exit 1
fi

# Benchmark prompts
SHORT_PROMPT="What is 2+2?"
MEDIUM_PROMPT="Explain the concept of machine learning in 3 sentences."
LONG_PROMPT="Write a detailed explanation of how neural networks work, including the concepts of layers, weights, biases, activation functions, and backpropagation. Include a simple example."
CODE_PROMPT="Write a Python function that implements binary search on a sorted list."

benchmark_model() {
    local model=$1
    local prompt=$2
    local label=$3
    
    echo "Testing $model - $label..." | tee -a "$RESULTS_FILE"
    
    # Warm up (first run is slower)
    ollama run "$model" "Hi" --verbose 2>/dev/null | head -1 > /dev/null
    
    # Actual benchmark
    START=$(date +%s.%N)
    RESPONSE=$(ollama run "$model" "$prompt" --verbose 2>&1)
    END=$(date +%s.%N)
    
    # Extract metrics
    TOTAL_TIME=$(echo "$END - $START" | bc)
    EVAL_COUNT=$(echo "$RESPONSE" | grep -o 'eval_count: [0-9]*' | awk '{print $2}' || echo "N/A")
    EVAL_DURATION=$(echo "$RESPONSE" | grep -o 'eval_duration: [0-9.]*' | awk '{print $2}' || echo "N/A")
    
    if [ "$EVAL_COUNT" != "N/A" ] && [ "$EVAL_DURATION" != "N/A" ]; then
        # Convert nanoseconds to seconds and calculate tokens/sec
        EVAL_SEC=$(echo "scale=3; $EVAL_DURATION / 1000000000" | bc)
        TOKENS_SEC=$(echo "scale=2; $EVAL_COUNT / $EVAL_SEC" | bc 2>/dev/null || echo "N/A")
    else
        TOKENS_SEC="N/A"
    fi
    
    echo "  Tokens: $EVAL_COUNT | Time: ${TOTAL_TIME}s | Speed: ${TOKENS_SEC} tok/s" | tee -a "$RESULTS_FILE"
}

# Run benchmarks
echo "=== Benchmark Results ===" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

for model in $MODELS; do
    echo "--- $model ---" | tee -a "$RESULTS_FILE"
    benchmark_model "$model" "$SHORT_PROMPT" "Short"
    benchmark_model "$model" "$MEDIUM_PROMPT" "Medium"
    benchmark_model "$model" "$LONG_PROMPT" "Long"
    benchmark_model "$model" "$CODE_PROMPT" "Code"
    echo "" | tee -a "$RESULTS_FILE"
done

# Memory usage
echo "=== Memory Usage ===" | tee -a "$RESULTS_FILE"
ps aux | grep -E "(ollama|open-webui)" | grep -v grep | awk '{print $11, $4"%"}' | tee -a "$RESULTS_FILE"

# Concurrent user simulation
echo "" | tee -a "$RESULTS_FILE"
echo "=== Concurrent Load Test ===" | tee -a "$RESULTS_FILE"

concurrent_test() {
    local model=$1
    local concurrent=$2
    
    echo "Testing $model with $concurrent concurrent requests..." | tee -a "$RESULTS_FILE"
    
    START=$(date +%s.%N)
    for i in $(seq 1 $concurrent); do
        ollama run "$model" "Count from 1 to 10" &
    done
    wait
    END=$(date +%s.%N)
    
    TOTAL=$(echo "$END - $START" | bc)
    echo "  $concurrent requests completed in ${TOTAL}s" | tee -a "$RESULTS_FILE"
}

# Test with first available model
FIRST_MODEL=$(echo "$MODELS" | head -1)
concurrent_test "$FIRST_MODEL" 2
concurrent_test "$FIRST_MODEL" 5

echo "" | tee -a "$RESULTS_FILE"
echo "=========================================="
echo "Benchmark complete. Results saved to:"
echo "$RESULTS_FILE"
echo "=========================================="
