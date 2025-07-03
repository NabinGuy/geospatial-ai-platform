from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from backend.config import Config

Base = declarative_base()

class GeospatialJob(Base):
    __tablename__ = "geospatial_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_query = Column(Text, nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    plan = Column(JSON)
    code = Column(Text)
    result = Column(JSON)
    error_message = Column(Text)
    is_completed = Column(Boolean, default=False)

class GeospatialData(Base):
    __tablename__ = "geospatial_data"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    data_type = Column(String(50))  # vector, raster
    file_path = Column(String(500))
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database setup
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()