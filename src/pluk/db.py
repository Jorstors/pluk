import os
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

# Initialize the database connection pool
POOL = ConnectionPool(
  os.environ.get('PLUK_DATABASE_URL'),
  kwargs={
    "row_factory": dict_row
  }
)
