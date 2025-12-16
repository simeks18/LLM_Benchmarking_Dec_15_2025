CREATE TABLE IF NOT EXISTS Models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    path TEXT NOT NULL,
    quantization TEXT,
    file_size_mb REAL,
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS Prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_text TEXT NOT NULL,
    category TEXT DEFAULT 'General',
    expected_output TEXT,
    date_added DATETIME DEFAULT CURRENT_TIMESTAMP,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS Sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    status TEXT DEFAULT 'running',
    total_models INTEGER,
    total_prompts INTEGER,
    models_completed INTEGER DEFAULT 0,
    prompts_completed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS Results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    model_id INTEGER,
    prompt_id INTEGER,
    output_text TEXT,
    execution_time_seconds REAL,
    tokens_generated INTEGER,
    tokens_per_second REAL,
    error_message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES Sessions(id),
    FOREIGN KEY(model_id) REFERENCES Models(id),
    FOREIGN KEY(prompt_id) REFERENCES Prompts(id)
);

CREATE VIEW IF NOT EXISTS ResultsSummary AS
SELECT 
    r.id,
    s.description AS Session,
    m.filename AS Model,
    p.category AS Category,
    p.prompt_text,
    r.output_text,
    r.execution_time_seconds,
    r.tokens_per_second,
    r.error_message
FROM Results r
JOIN Sessions s ON r.session_id = s.id
JOIN Models m ON r.model_id = m.id
JOIN Prompts p ON r.prompt_id = p.id;
