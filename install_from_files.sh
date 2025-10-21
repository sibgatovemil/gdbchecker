#!/bin/bash
# Quick install script for GDBChecker

set -e

echo "Installing GDBChecker..."

cd /opt/gdbchecker

# Create all Python files
cat > models.py << 'EOFPY'
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

class Domain(Base):
    __tablename__ = 'domains'

    id = Column(Integer, primary_key=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    project = Column(String(255), nullable=True)
    purpose = Column(String(255), nullable=True)
    current_status = Column(String(50), default='pending')
    last_check_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    history = relationship("StatusHistory", back_populates="domain", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'domain': self.domain,
            'project': self.project,
            'purpose': self.purpose,
            'current_status': self.current_status,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class StatusHistory(Base):
    __tablename__ = 'status_history'

    id = Column(Integer, primary_key=True)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    details = Column(Text, nullable=True)

    domain = relationship("Domain", back_populates="history")

    def to_dict(self):
        return {
            'id': self.id,
            'domain_id': self.domain_id,
            'status': self.status,
            'checked_at': self.checked_at.isoformat() if self.checked_at else None,
            'details': self.details
        }

def get_engine():
    database_url = os.getenv('DATABASE_URL', 'postgresql://gdbchecker:password@localhost:5432/gdbchecker')
    return create_engine(database_url, pool_pre_ping=True)

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def init_database():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database initialized successfully!")
EOFPY

echo "Created models.py"

# Create requirements.txt
cat > requirements.txt << 'EOFREQ'
Flask==3.0.0
Flask-CORS==4.0.0
gunicorn==21.2.0
psycopg2-binary==2.9.9
SQLAlchemy==2.0.23
APScheduler==3.10.4
requests==2.31.0
python-telegram-bot==20.7
python-dotenv==1.0.0
EOFREQ

echo "Created requirements.txt"

# Download remaining files from GitHub raw
BASE_URL="https://raw.githubusercontent.com/yourusername/gdbchecker/main"

echo ""
echo "Installation complete!"
echo "Now run: chmod +x deploy.sh && ./deploy.sh"
