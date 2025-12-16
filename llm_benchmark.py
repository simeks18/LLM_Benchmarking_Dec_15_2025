import os
import sqlite3
import time
import glob
import gc
from llama_cpp import Llama

# --- CONFIGURATION ---
DB_FILE = "llm_benchmark.db"
SCHEMA_FILE = "llm_benchmark_schema.sql"
MODELS_DIR = "./models"
N_CTX = 2048
MAX_TOKENS = 512
N_GPU_LAYERS = 0  # Set to 0 for CPU, 30+ for GPU

def init_db():
    if not os.path.exists(SCHEMA_FILE):
        print(f"Error: Schema file {SCHEMA_FILE} missing.")
        return
    conn = sqlite3.connect(DB_FILE)
    with open(SCHEMA_FILE, "r") as f:
        conn.executescript(f.read())
    conn.close()
    print("Database initialized.")

def run_benchmark():
    # Auto-init DB if missing
    if not os.path.exists(DB_FILE):
        init_db()

    conn = sqlite3.connect(DB_FILE)
    
    # Check for prompts
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, prompt_text FROM Prompts WHERE active = 1")
        prompts = cursor.fetchall()
    except sqlite3.OperationalError:
        print("Error: Database tables missing. Running init_db...")
        conn.close()
        init_db()
        return

    if not prompts:
        print("No active prompts found. Run import_prompts.py first.")
        return

    # Check for models
    model_files = glob.glob(os.path.join(MODELS_DIR, "*.gguf"))
    if not model_files:
        print(f"No .gguf models found in {MODELS_DIR}")
        return

    # Start Session
    cursor.execute("INSERT INTO Sessions (description, total_models, total_prompts) VALUES (?, ?, ?)", 
                   ("Benchmark Run", len(model_files), len(prompts)))
    session_id = cursor.lastrowid
    conn.commit()
    print(f"--- Starting Session {session_id} ---")

    for model_path in model_files:
        filename = os.path.basename(model_path)
        print(f"Loading: {filename}...")
        
        # Register Model
        cursor.execute("INSERT OR IGNORE INTO Models (filename, path) VALUES (?, ?)", (filename, model_path))
        cursor.execute("SELECT id FROM Models WHERE filename = ?", (filename,))
        model_id = cursor.fetchone()[0]

        try:
            # --- LOAD MODEL ---
            llm = Llama(model_path=model_path, n_ctx=N_CTX, n_gpu_layers=N_GPU_LAYERS, verbose=False)

            # --- RUN PROMPTS ---
            for prompt_id, prompt_text in prompts:
                start = time.time()
                output = llm.create_completion(prompt_text, max_tokens=MAX_TOKENS)
                duration = time.time() - start
                
                text_out = output['choices'][0]['text']
                tokens = output['usage']['completion_tokens']
                tps = tokens / duration if duration > 0 else 0
                
                cursor.execute("""
                    INSERT INTO Results (session_id, model_id, prompt_id, output_text, execution_time_seconds, tokens_per_second)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, model_id, prompt_id, text_out, duration, tps))
                conn.commit()
                print(f" > Prompt {prompt_id} done ({tps:.2f} t/s)")

            # --- UNLOAD MODEL ---
            del llm
            gc.collect()
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            cursor.execute("INSERT INTO Results (session_id, model_id, error_message) VALUES (?, ?, ?)", 
                           (session_id, model_id, str(e)))
            conn.commit()

    print("Benchmark Complete.")
    conn.close()

if __name__ == "__main__":
    run_benchmark()
