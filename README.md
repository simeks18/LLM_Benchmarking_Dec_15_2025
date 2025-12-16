# Local LLM Benchmark

Automated benchmarking tool for local LLMs (GGUF format) using `llama-cpp-python` and SQLite.

## Setup

### 1. Install Requirements

```bash
pip install -r requirements.txt
```

> **Note:** For GPU support, install `llama-cpp-python` with CUDA enabled.

### 2. Add Models

Place `.gguf` files in the `models/` directory.

### 3. Add Prompts

Create a text file (e.g., `prompts.txt`) and run:

```bash
python import_prompts.py prompts.txt
```

## Usage

Run the benchmark:

```bash
python llm_benchmark.py
```

## Results

Results are stored in `llm_benchmark.db`. You can view them using any SQLite viewer or export them to CSV.

---

## Part 3: Pushing to GitHub

Once you have the required files created or updated in your folder, run the following commands to push to GitHub:

```bash
# 1. Initialize Git
git init

# 2. Add the files (.gitignore will prevent models from being added)
git add .

# 3. Commit
git commit -m "Initial commit of LLM Benchmarking Suite"

# 4. Connect to your GitHub repo (create a new empty repo on GitHub first)
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 5. Push
git push -u origin main
```
