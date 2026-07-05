import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from internly.db.database import Base
from internly.db import models  # noqa: F401


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = Session()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        Base.metadata.drop_all(engine)

