import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, event, String, Text, Integer, Boolean, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./vietlab-pilot.db')
engine = create_engine(DATABASE_URL, pool_pre_ping=True, **({'connect_args': {'check_same_thread': False, 'timeout': 30}} if DATABASE_URL.startswith('sqlite') else {'pool_size': 10, 'max_overflow': 10}))
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_setup(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA journal_mode=WAL')
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def now():
    return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    full_name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(30), index=True)
    dept: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(default=1)

class LoginAttempt(Base):
    __tablename__ = 'login_attempts'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), index=True)
    ip: Mapped[str] = mapped_column(String(100), index=True)
    created: Mapped[int] = mapped_column(Integer, index=True)

class AuthSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    csrf: Mapped[str] = mapped_column(String(80))
    expires: Mapped[int] = mapped_column(Integer, index=True)

class Method(Base):
    __tablename__ = 'methods'
    __table_args__ = (UniqueConstraint('code','parameter','matrix','dept','revision'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80))
    parameter: Mapped[str] = mapped_column(String(160))
    matrix: Mapped[str] = mapped_column(String(10))
    dept: Mapped[str] = mapped_column(String(50), index=True)
    revision: Mapped[str] = mapped_column(String(60))
    unit: Mapped[str] = mapped_column(String(40))
    sop: Mapped[str] = mapped_column(String(160))
    verification: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20), default='draft', index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    approver_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    approved_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    version: Mapped[int] = mapped_column(default=1)

class Sample(Base):
    __tablename__ = 'samples'
    __table_args__ = (Index('ix_sample_status_due','status','due'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    customer: Mapped[str] = mapped_column(String(200))
    contract: Mapped[str] = mapped_column(String(100))
    matrix: Mapped[str] = mapped_column(String(10))
    location: Mapped[str] = mapped_column(String(300))
    collected_at: Mapped[str] = mapped_column(String(40))
    received_at: Mapped[str] = mapped_column(String(40), default=now)
    due: Mapped[str] = mapped_column(String(10), index=True)
    condition: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default='received', index=True)
    version: Mapped[int] = mapped_column(default=1)

class Task(Base):
    __tablename__ = 'tasks'
    __table_args__ = (UniqueConstraint('sample_id', 'method_id'), Index('ix_task_assignee_status','assignee_id','status'), Index('ix_task_dept_status','dept','status'))
    id: Mapped[int] = mapped_column(primary_key=True)
    sample_id: Mapped[int] = mapped_column(ForeignKey('samples.id'), index=True)
    method_id: Mapped[int] = mapped_column(ForeignKey('methods.id'))
    dept: Mapped[str] = mapped_column(String(50), index=True)
    assignee_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    status: Mapped[str] = mapped_column(String(20), default='draft', index=True)
    value: Mapped[str] = mapped_column(String(100), default='')
    qc_note: Mapped[str] = mapped_column(String(1000), default='')
    qc_pass: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_ref: Mapped[str] = mapped_column(String(300), default='')
    author_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    version: Mapped[int] = mapped_column(default=1)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)

class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    sample_id: Mapped[int] = mapped_column(ForeignKey('samples.id'), unique=True)
    issued_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    issued_at: Mapped[str] = mapped_column(String(40), default=now)
    snapshot: Mapped[dict] = mapped_column(JSON)

class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    reason: Mapped[str] = mapped_column(String(1000))
    before: Mapped[dict] = mapped_column(JSON)
    after: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40), default=now, index=True)
