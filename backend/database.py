from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Forzar uso de variable de entorno
DATABASE_URL = os.getenv("DATABASE_URL")

# Si no encuentra la variable, usar la URL correcta de Railway (la que viste en variables)
if not DATABASE_URL:
    DATABASE_URL = "mysql://root:ASKrtcOhoVsWFugYqoHQchZgehiHGCwr@mysql.railway.internal:3306/railway"

print(f"🔗 Conectando a: {DATABASE_URL}")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
