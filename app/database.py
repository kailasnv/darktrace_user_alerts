from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# TODO (team integration):
# Replace local PostgreSQL connection with the shared project database.

DATABASE_URL = "postgresql+psycopg://cyart:cyart_dev_password@127.0.0.1:5433/cyart_darktrace"


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
