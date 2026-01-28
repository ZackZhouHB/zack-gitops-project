#!/bin/bash
# Model Management & Quantization Script

set -e

echo "=========================================="
echo "Model Management & Optimization"
echo "=========================================="

# Function to show available models
list_models() {
    echo "Currently installed models:"
    ollama list
    echo ""
}

# Function to pull model with specific quantization
pull_model() {
    local model=$1
    local quant=$2
    echo "Pulling ${model} with ${quant} quantization..."
    ollama pull "${model}:${quant}" || ollama pull "${model}"
}

# Function to create custom quantized model from GGUF
create_quantized_model() {
    local name=$1
    local gguf_path=$2
    
    cat > "/tmp/${name}.Modelfile" << EOF
FROM ${gguf_path}
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
SYSTEM You are a helpful AI assistant.
EOF
    
    ollama create "$name" -f "/tmp/${name}.Modelfile"
    rm "/tmp/${name}.Modelfile"
    echo "Created model: $name"
}

# Function to create optimized model variant
create_optimized_variant() {
    local base_model=$1
    local new_name=$2
    local system_prompt=$3
    local ctx_size=${4:-4096}
    
    cat > "/tmp/${new_name}.Modelfile" << EOF
FROM ${base_model}
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx ${ctx_size}
PARAMETER repeat_penalty 1.1
SYSTEM ${system_prompt}
EOF
    
    ollama create "$new_name" -f "/tmp/${new_name}.Modelfile"
    rm "/tmp/${new_name}.Modelfile"
    echo "Created optimized variant: $new_name"
}

# Preset model configurations for different use cases
setup_legal_models() {
    echo "Setting up legal-focused models..."
    create_optimized_variant "llama3.1:8b" "legal-assistant" \
        "You are a legal assistant. Provide accurate, well-reasoned analysis. Always cite relevant considerations. Never provide actual legal advice - recommend consulting a qualified attorney for specific situations." \
        8192
}

setup_coding_models() {
    echo "Setting up coding-focused models..."
    create_optimized_variant "deepseek-coder:6.7b" "code-assistant" \
        "You are an expert programmer. Write clean, efficient, well-documented code. Explain your reasoning. Follow best practices and security guidelines." \
        8192
}

setup_medical_models() {
    echo "Setting up medical documentation models..."
    create_optimized_variant "qwen2.5:7b" "medical-notes" \
        "You are a medical documentation assistant. Help organize and summarize clinical notes. Use proper medical terminology. Never provide medical diagnoses or treatment recommendations." \
        8192
}

setup_customer_service_models() {
    echo "Setting up customer service models..."
    create_optimized_variant "mistral:7b" "support-agent" \
        "You are a helpful customer support agent. Be polite, professional, and solution-oriented. Acknowledge customer concerns and provide clear, actionable responses." \
        4096
}

# Download GGUF and create model (for custom quantization)
download_and_quantize() {
    local hf_repo=$1
    local gguf_file=$2
    local model_name=$3
    
    echo "This requires huggingface-cli. Installing if needed..."
    pip3 install -q huggingface_hub
    
    local download_dir="$HOME/.ollama/gguf"
    mkdir -p "$download_dir"
    
    echo "Downloading ${gguf_file} from ${hf_repo}..."
    huggingface-cli download "$hf_repo" "$gguf_file" --local-dir "$download_dir"
    
    create_quantized_model "$model_name" "${download_dir}/${gguf_file}"
}

# Menu
show_menu() {
    echo ""
    echo "Select an option:"
    echo "1) List installed models"
    echo "2) Pull recommended models for this hardware"
    echo "3) Setup legal assistant models"
    echo "4) Setup coding assistant models"
    echo "5) Setup medical documentation models"
    echo "6) Setup customer service models"
    echo "7) Create custom model variant"
    echo "8) Download custom GGUF model"
    echo "9) Remove a model"
    echo "0) Exit"
    echo ""
}

# Interactive mode
if [ "$1" == "--interactive" ] || [ -z "$1" ]; then
    while true; do
        show_menu
        read -p "Choice: " choice
        
        case $choice in
            1) list_models ;;
            2) 
                MEMORY_GB=$(( $(sysctl -n hw.memsize) / 1073741824 ))
                echo "Detected ${MEMORY_GB}GB - pulling appropriate models..."
                if [ "$MEMORY_GB" -ge 48 ]; then
                    pull_model "llama3.1" "70b-instruct-q3_K_M"
                    pull_model "qwen2.5" "32b"
                elif [ "$MEMORY_GB" -ge 24 ]; then
                    pull_model "llama3.1" "8b"
                    pull_model "mistral-nemo" "12b"
                else
                    pull_model "llama3.2" "3b"
                    pull_model "phi3" "mini"
                fi
                ;;
            3) setup_legal_models ;;
            4) setup_coding_models ;;
            5) setup_medical_models ;;
            6) setup_customer_service_models ;;
            7)
                read -p "Base model (e.g., llama3.1:8b): " base
                read -p "New model name: " name
                read -p "System prompt: " prompt
                read -p "Context size (default 4096): " ctx
                create_optimized_variant "$base" "$name" "$prompt" "${ctx:-4096}"
                ;;
            8)
                read -p "HuggingFace repo (e.g., TheBloke/Llama-2-7B-GGUF): " repo
                read -p "GGUF filename: " file
                read -p "Model name to create: " name
                download_and_quantize "$repo" "$file" "$name"
                ;;
            9)
                list_models
                read -p "Model to remove: " model
                ollama rm "$model"
                ;;
            0) exit 0 ;;
            *) echo "Invalid option" ;;
        esac
    done
fi

# Command line mode
case $1 in
    --list) list_models ;;
    --legal) setup_legal_models ;;
    --coding) setup_coding_models ;;
    --medical) setup_medical_models ;;
    --support) setup_customer_service_models ;;
    --pull) pull_model "$2" "$3" ;;
    *)
        echo "Usage: $0 [--interactive|--list|--legal|--coding|--medical|--support|--pull model quant]"
        ;;
esac
