from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Temporary SQLite database for the webhook endpoint registry.
DATABASE_URL = "sqlite:///./endpoint_registry.db"


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
