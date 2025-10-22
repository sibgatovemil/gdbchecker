from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

Base = declarative_base()

class Domain(Base):
    __tablename__ = 'domains'

    id = Column(Integer, primary_key=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    project = Column(String(255), nullable=True)
    purpose = Column(String(255), nullable=True)
    current_status = Column(String(50), default='pending')  # ok, banned, error, pending
    ssl_status = Column(String(50), default='pending')  # valid, expired, invalid, missing, pending
    last_check_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    added_by = Column(String(50), nullable=True)  # Username who added the domain
    expire_date = Column(DateTime, nullable=True)  # Domain expiration date
    autorenew = Column(String(20), nullable=True)  # enabled, disabled, unknown

    # Relationship
    history = relationship("StatusHistory", back_populates="domain", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'domain': self.domain,
            'project': self.project,
            'purpose': self.purpose,
            'current_status': self.current_status,
            'ssl_status': self.ssl_status,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'added_by': self.added_by,
            'expire_date': self.expire_date.isoformat() if self.expire_date else None,
            'autorenew': self.autorenew
        }

class StatusHistory(Base):
    __tablename__ = 'status_history'

    id = Column(Integer, primary_key=True)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False, index=True)
    status = Column(String(50), nullable=False)  # ok, banned, error
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    details = Column(Text, nullable=True)  # JSON string with additional info

    # Relationship
    domain = relationship("Domain", back_populates="history")

    def to_dict(self):
        return {
            'id': self.id,
            'domain_id': self.domain_id,
            'status': self.status,
            'checked_at': self.checked_at.isoformat() if self.checked_at else None,
            'details': self.details
        }

# Database setup
def get_engine():
    database_url = os.getenv('DATABASE_URL', 'postgresql://gdbchecker:password@localhost:5432/gdbchecker')
    return create_engine(database_url, pool_pre_ping=True)

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)

    # Flask-Login required methods
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

def init_database():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Database initialized successfully!")
