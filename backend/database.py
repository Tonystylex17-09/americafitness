from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Usar variable de entorno de Railway, o fallback a local
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:admin123@localhost/americafitness_db")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# redeploy
