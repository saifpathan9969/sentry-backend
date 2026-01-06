"""
Scan model
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Numeric, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM as PG_ENUM
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class ScanMode(str, enum.Enum):
    """Scan mode options"""
    COMMON = "common"
    FAST = "fast"
    FULL = "full"
    STEALTH = "stealth"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class ExecutionMode(str, enum.Enum):
    """Execution mode options"""
    REPORT_ONLY = "report_only"
    DRY_RUN = "dry_run"
    APPLY_FIXES = "apply_fixes"


class ScanStatus(str, enum.Enum):
    """Scan status options"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Scan(Base):
    """
    Scan model for security assessments
    """
    __tablename__ = "scans"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Scan configuration
    target = Column(String(500), nullable=False)
    scan_mode = Column(
        PG_ENUM('common', 'fast', 'full', 'stealth', 'aggressive', 'custom', name='scan_mode', create_type=False),
        default='common',
        nullable=False
    )
    execution_mode = Column(
        PG_ENUM('report_only', 'dry_run', 'apply_fixes', name='execution_mode', create_type=False),
        default='report_only',
        nullable=False
    )
    
    # Scan status - use PostgreSQL native enum with lowercase values
    status = Column(
        PG_ENUM('queued', 'running', 'completed', 'failed', 'cancelled', name='scan_status', create_type=False),
        default='queued',
        nullable=False,
        index=True
    )
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Results summary
    vulnerabilities_found = Column(Integer, default=0, nullable=False)
    critical_count = Column(Integer, default=0, nullable=False)
    high_count = Column(Integer, default=0, nullable=False)
    medium_count = Column(Integer, default=0, nullable=False)
    low_count = Column(Integer, default=0, nullable=False)
    
    # Platform detection
    platform_detected = Column(String(100), nullable=True)
    confidence = Column(Numeric(3, 2), nullable=True)
    
    # Reports (stored as JSON and TEXT)
    report_json = Column(JSONB, nullable=True)
    report_text = Column(Text, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="scans")
    
    def __repr__(self):
        return f"<Scan(id={self.id}, target={self.target}, status={self.status})>"
