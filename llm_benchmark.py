import os
import sqlite3
import time
import glob
import gc
import argparse
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

def run_benchmark(mode="all"):
    if not os.path.exists(DB_FILE):
        init_db()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Prompts
    try:
        cursor.execute("SELECT id, prompt_text FROM Prompts WHERE active = 1")
        prompts = cursor.fetchall()
    except sqlite3.OperationalError:
        print("Error: Database tables missing. Running init_db...")
        conn.close()
        init_db()
        return

    if not prompts:
        print("No active prompts found.")
        return

    # Models on disk
    model_files = glob.glob(os.path.join(MODELS_DIR, "*.gguf"))
    if not model_files:
        print(f"No .gguf models found in {MODELS_DIR}")
        return

    # --- FILTER MODELS IF MODE == "new" ---
    if mode == "new":
        cursor.execute("SELECT DISTINCT model_id FROM Results")
        seen_model_ids = {row[0] for row in cursor.fetchall()}

        if seen_model_ids:
            placeholders = ",".join("?" for _ in seen_model_ids)
            cursor.execute(
                f"SELECT filename FROM Models WHERE id IN ({placeholders})",
                tuple(seen_model_ids)
            )
            seen_filenames = {row[0] for row in cursor.fetchall()}
            model_files = [
                m for m in model_files
                if os.path.basename(m) not in seen_filenames
            ]

        if not model_files:
            print("No new models to benchmark.")
            conn.close()
            return

    # Session
    cursor.execute(
        "INSERT INTO Sessions (description, total_models, total_prompts) VALUES (?, ?, ?)",
        ("Benchmark Run", len(model_files), len(prompts))
    )
    session_id = cursor.lastrowid
    conn.commit()

    print(f"--- Starting Session {session_id} ({mode} mode) ---")

    for model_path in model_files:
        filename = os.path.basename(model_path)
        print(f"Loading: {filename}...")

        # Register model
        cursor.execute(
            "INSERT OR IGNORE INTO Models (filename, path) VALUES (?, ?)",
            (filename, model_path)
        )
        cursor.execute(
            "SELECT id, quantization FROM Models WHERE filename = ?",
            (filename,)
        )
        model_id, existing_quant = cursor.fetchone()

        try:
            # Load model
            llm = Llama(
                model_path=model_path,
                n_ctx=N_CTX,
                n_gpu_layers=N_GPU_LAYERS,
                verbose=False
            )

            # --- DETECT & STORE QUANTIZATION ---
            if existing_quant is None:
                quant = llm.metadata.get("general.file_type", "unknown")
                cursor.execute(
                    "UPDATE Models SET quantization = ? WHERE id = ?",
                    (quant, model_id)
                )
                conn.commit()
                print(f"  Quantization detected: {quant}")

            # Run prompts
            for prompt_id, prompt_text in prompts:
                start = time.time()
                output = llm.create_completion(
                    prompt_text,
                    max_tokens=MAX_TOKENS
                )
                duration = time.time() - start

                text_out = output["choices"][0]["text"]
                tokens = output["usage"]["completion_tokens"]
                tps = tokens / duration if duration > 0 else 0

                cursor.execute("""
                    INSERT INTO Results (
                        session_id,
                        model_id,
                        prompt_id,
                        output_text,
                        execution_time_seconds,
                        tokens_per_second
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, model_id, prompt_id, text_out, duration, tps))
                conn.commit()

                print(f" > Prompt {prompt_id} done ({tps:.2f} t/s)")

            del llm
            gc.collect()

        except Exception as e:
            print(f"Error processing {filename}: {e}")
            cursor.execute(
                "INSERT INTO Results (session_id, model_id, error_message) VALUES (?, ?, ?)",
                (session_id, model_id, str(e))
            )
            conn.commit()

    print("Benchmark Complete.")
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["all", "new"],
        default="all",
        help="Run all models or only new models"
    )
    args = parser.parse_args()
    run_benchmark(args.mode)
