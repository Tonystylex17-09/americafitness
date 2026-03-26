from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Obtener la URL de Railway
DATABASE_URL = os.getenv("DATABASE_URL")

# Si no hay variable, usar la URL con el driver correcto
if not DATABASE_URL:
    DATABASE_URL = "mysql+pymysql://root:ASKrtcOhoVsWFugYqoHQchZgehiHGCwr@mysql.railway.internal:3306/railway"
else:
    # Si la URL no tiene el driver, agregarlo
    if not DATABASE_URL.startswith("mysql+pymysql"):
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://")

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
