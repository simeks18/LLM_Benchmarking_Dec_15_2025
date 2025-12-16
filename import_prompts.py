import sqlite3
import sys
import os

def import_prompts_from_file(filename):
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return

    conn = sqlite3.connect("llm_benchmark.db")
    cursor = conn.cursor()
    
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    count = 0
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Format: Category | Prompt OR Just Prompt
        if "|" in line:
            parts = line.split("|", 1)
            category = parts[0].strip()
            text = parts[1].strip()
        else:
            category = "General"
            text = line
            
        cursor.execute("INSERT INTO Prompts (prompt_text, category) VALUES (?, ?)", (text, category))
        count += 1
        
    conn.commit()
    conn.close()
    print(f"Imported {count} prompts from {filename}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_prompts.py <filename>")
    else:
        import_prompts_from_file(sys.argv[1])
