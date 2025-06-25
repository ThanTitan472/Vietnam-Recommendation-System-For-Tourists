from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Database setup
DATABASE_URL = "sqlite:///./travel_chatbot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChatHistory(Base):
    """Model để lưu lịch sử chat"""
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    extracted_features = Column(Text)  # JSON string của các đặc trưng được trích xuất
    recommended_locations = Column(Text)  # JSON string của các địa điểm được gợi ý
    user_ip = Column(String(50))
    session_id = Column(String(100))

def create_tables():
    """Tạo các bảng trong database"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency để lấy database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
