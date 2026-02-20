-- D1 Database Schema for EyeExam Waitlist

CREATE TABLE IF NOT EXISTS waitlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    referrer TEXT
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_email ON waitlist(email);
CREATE INDEX IF NOT EXISTS idx_created_at ON waitlist(created_at);
