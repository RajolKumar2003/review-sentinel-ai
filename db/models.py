from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  # pending / approved / rejected
    risk_score = Column(Integer, default=0)
    synthesis_summary = Column(Text)

    findings = relationship("Finding", back_populates="review", cascade="all, delete-orphan")
    audit_entries = relationship("AuditLogEntry", back_populates="review", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    severity = Column(String)
    area = Column(String)
    detail = Column(Text)

    review = relationship("Review", back_populates="findings")


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    actor = Column(String)  # "system" or a human name/handle
    action = Column(String)  # created / approved / rejected
    timestamp = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    review = relationship("Review", back_populates="audit_entries")
