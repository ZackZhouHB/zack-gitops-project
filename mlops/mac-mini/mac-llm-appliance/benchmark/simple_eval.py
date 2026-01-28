import time
import requests
import json
import sys

# Usage: python3 simple_eval.py [model_name]
# Example: python3 simple_eval.py llama3.1:8b

def benchmark_model(model_name):
    url = "http://localhost:11434/api/generate"
    
    # A prompt that requires some generation but isn't too creative/random
    prompt = "Write a concise executive summary about the benefits of local AI deployment for data privacy. approx 200 words."
    
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }
    
    print(f"Benchmarking {model_name}...")
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error calling API: {e}")
        return

    end_time = time.time()
    
    total_duration = data.get("total_duration") / 1e9 # Convert nanoseconds to seconds
    eval_count = data.get("eval_count", 0) # Number of tokens generated
    eval_duration = data.get("eval_duration") / 1e9
    
    tokens_per_sec = eval_count / eval_duration if eval_duration > 0 else 0
    
    print("-" * 30)
    print(f"Model: {model_name}")
    print(f"Tokens Generated: {eval_count}")
    print(f"Total Time: {total_duration:.2f}s")
    print(f"Generation Speed: {tokens_per_sec:.2f} tokens/sec")
    print("-" * 30)
    
    # Simple pass/fail based on usability threshold (e.g., human reading speed is ~5-10 t/s)
    if tokens_per_sec > 10:
        print("Status: EXCELLENT (Suitable for real-time chat)")
    elif tokens_per_sec > 5:
        print("Status: GOOD (Acceptable for most uses)")
    else:
        print("Status: SLOW (Better for background tasks)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide a model name.")
        sys.exit(1)
    
    model = sys.argv[1]
    benchmark_model(model)
