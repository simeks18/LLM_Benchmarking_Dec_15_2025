Markdown

# Local LLM Benchmark

Automated benchmarking tool for local LLMs (GGUF format) using `llama-cpp-python` and SQLite.

## Setup

1. **Install Requirements:**
   ```bash
   pip install -r requirements.txt
(Note: For GPU support, install llama-cpp-python with CUDA enabled)

Add Models: Place .gguf files in the models/ directory.

Add Prompts: Create a text file (e.g., prompts.txt) and run:

'''Bash

python import_prompts.py prompts.txt
Usage
Run the benchmark:

'''Bash

python llm_benchmark.py
Results
Results are stored in llm_benchmark.db. You can view them using any SQLite viewer or export them to CSV.


---

### Part 3: Pushing to GitHub

Once you have those 6 files created/updated in your folder, run these commands to push to GitHub:

```bash
# 1. Initialize Git
git init

# 2. Add the files (The .gitignore will make sure models don't get added)
git add .

# 3. Commit
git commit -m "Initial commit of LLM Benchmarking Suite"

# 4. Connect to your GitHub Repo (Create a new empty repo on GitHub.com first)
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 5. Push
git push -u origin main
