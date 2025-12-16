import sqlite3
import pandas as pd

conn = sqlite3.connect("llm_benchmark.db")

# Read the easy-to-read View we created in the schema
df = pd.read_sql_query("SELECT * FROM ResultsSummary", conn)

# Save to CSV
df.to_csv("benchmark_results.csv", index=False)
print("Exported results to benchmark_results.csv")
