import os

# Unit tests that do not exercise PostgreSQL use SQLite so test collection
# does not require a running database or the PostgreSQL driver.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
