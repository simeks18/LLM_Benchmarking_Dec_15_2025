import os
import sqlite3
import time
import glob
import gc
from datetime import datetime
from llama_cpp import Llama

# --- CONFIGURATION ---
DB_FILE = "llm_benchmark.db"
MODELS_DIR = "./models"  # Point this to your GGUF folder
N_CTX = 2048             # Context window
MAX_TOKENS = 512         # Max tokens to generate
N_GPU_LAYERS = 0         # Set to 0 for CPU only, or higher (e.g., 30) if you have a GPU
TEMPERATURE = 0.7

def init_db():
    """Initialize database if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    with open("llm_benchmark_schema.sql", "r") as f:
        conn.executescript(f.read())
    conn.close()
    print("Database initialized.")

def get_active_prompts(conn):
    """Fetch all active prompts."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, prompt_text FROM Prompts WHERE active = 1")
    return cursor.fetchall()

def register_session(conn, description, total_models, total_prompts):
    """Start a new session."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Sessions (description, total_models, total_prompts, status)
        VALUES (?, ?, ?, 'running')
    """, (description, total_models, total_prompts))
    conn.commit()
    return cursor.lastrowid

def update_session_status(conn, session_id, status):
    """Close a session."""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Sessions 
        SET status = ?, end_time = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (status, session_id))
    conn.commit()

def register_model(conn, filepath):
    """Check if model exists in DB, otherwise add it. Returns Model ID."""
    filename = os.path.basename(filepath)
    file_size = os.path.getsize(filepath) / (1024 * 1024) # MB
    
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM Models WHERE filename = ?", (filename,))
    row = cursor.fetchone()
    
    if row:
        return row[0]
    
    # Try to guess quantization from filename (e.g., "llama-2-7b.Q4_K_M.gguf")
    quant = "Unknown"
    if ".Q" in filename:
        try:
            quant = filename.split(".Q")[1].split(".")[0]
            quant = "Q" + quant
        except:
            pass

    cursor.execute("""
        INSERT INTO Models (filename, path, quantization, file_size_mb)
        VALUES (?, ?, ?, ?)
    """, (filename, filepath, quant, file_size))
    conn.commit()
    return cursor.lastrowid

class ModelLoader:
    """Context manager to ensure model is LOADED then DESTROYED properly."""
    def __init__(self, path):
        self.path = path
        self.llm = None

    def __enter__(self):
        print(f"  Loading model into RAM: {os.path.basename(self.path)}...")
        try:
            self.llm = Llama(
                model_path=self.path,
                n_ctx=N_CTX,
                n_gpu_layers=N_GPU_LAYERS,
                verbose=False # Set True for debug output
            )
            return self.llm
        except Exception as e:
            print(f"  CRITICAL ERROR loading model: {e}")
            return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.llm:
            print("  Unloading model and freeing RAM...")
            del self.llm
            self.llm = None
            gc.collect() # Force Python garbage collector

def run_benchmark():
    # 1. Setup
    if not os.path.exists(DB_FILE):
        init_db()
    
    conn = sqlite3.connect(DB_FILE)
    
    # 2. Find Models
    model_files = glob.glob(os.path.join(MODELS_DIR, "*.gguf"))
    if not model_files:
        print(f"No .gguf files found in {MODELS_DIR}")
        return

    # 3. Get Prompts
    prompts = get_active_prompts(conn)
    if not prompts:
        print("No active prompts found in DB. Please add prompts to the 'Prompts' table.")
        return

    # 4. Create Session
    session_id = register_session(conn, "Benchmark Run", len(model_files), len(prompts))
    print(f"Session {session_id} started. Found {len(model_files)} models and {len(prompts)} prompts.")

    # 5. Main Loop
    for i, model_path in enumerate(model_files):
        model_id = register_model(conn, model_path)
        model_name = os.path.basename(model_path)
        print(f"\n[{i+1}/{len(model_files)}] Processing {model_name}...")

        # --- CRITICAL: LOAD / RUN / UNLOAD CYCLE ---
        with ModelLoader(model_path) as llm:
            if llm is None:
                # Log model failure
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Results (session_id, model_id, error_message)
                    VALUES (?, ?, ?)
                """, (session_id, model_id, "Failed to load model file"))
                conn.commit()
                continue

            # Run all prompts for this model
            for p_idx, (prompt_id, prompt_text) in enumerate(prompts):
                print(f"    Prompt {p_idx+1}/{len(prompts)}...", end="\r")
                
                start_time = time.time()
                try:
                    # Run Inference
                    output = llm.create_completion(
                        prompt_text, 
                        max_tokens=MAX_TOKENS, 
                        temperature=TEMPERATURE
                    )
                    
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    text_out = output['choices'][0]['text']
                    tokens = output['usage']['completion_tokens']
                    tps = tokens / duration if duration > 0 else 0

                    # Save Result
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO Results 
                        (session_id, model_id, prompt_id, output_text, execution_time_seconds, tokens_generated, tokens_per_second)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (session_id, model_id, prompt_id, text_out, duration, tokens, tps))
                    conn.commit()

                except Exception as e:
                    print(f"\n    Error on prompt {prompt_id}: {e}")
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO Results (session_id, model_id, prompt_id, error_message)
                        VALUES (?, ?, ?, ?)
                    """, (session_id, model_id, prompt_id, str(e)))
                    conn.commit()

        # Update progress in Session table
        cursor = conn.cursor()
        cursor.execute("UPDATE Sessions SET models_completed = models_completed + 1 WHERE id = ?", (session_id,))
        conn.commit()
    
    update_session_status(conn, session_id, "completed")
    print(f"\nBenchmark Session {session_id} Complete!")
    conn.close()

if __name__ == "__main__":
    run_benchmark()
