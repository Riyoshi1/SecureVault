from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config import settings

# Convert sqlite+aiosqlite:/// to sqlite:/// so it uses Python's built-in C sqlite3 driver
# (Avoids aiosqlite thread hang on Python 3.14 while keeping async route compatibility)
sync_db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")

engine = create_engine(
    sync_db_url,
    connect_args={"check_same_thread": False} if sync_db_url.startswith("sqlite") else {},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
Base = declarative_base()


class AsyncSessionAdapter:
    """Lightweight async-compatible wrapper around SQLAlchemy Session for Python 3.14 compatibility."""
    def __init__(self, session: Session):
        self._session = session

    async def execute(self, statement, *args, **kwargs):
        return self._session.execute(statement, *args, **kwargs)

    def add(self, instance):
        self._session.add(instance)

    async def delete(self, instance):
        self._session.delete(instance)

    async def commit(self):
        self._session.commit()

    async def refresh(self, instance):
        self._session.refresh(instance)

    async def close(self):
        self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._session.rollback()
        self._session.close()


def async_session() -> AsyncSessionAdapter:
    return AsyncSessionAdapter(SessionLocal())


async def init_db():
    import app.models  # noqa: F401 - ensure models are registered on Base.metadata
    Base.metadata.create_all(bind=engine)


async def get_db():
    session = AsyncSessionAdapter(SessionLocal())
    try:
        yield session
    finally:
        await session.close()
