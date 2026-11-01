from database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, default="Cuộc hội thoại mới")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    jobs = relationship(
        "AIJob",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


class AIJob(Base):
    __tablename__ = "ai_jobs"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    job_type = Column(String(50), nullable=False, default="summary")
    mode = Column(String(20), nullable=False, default="background")
    status = Column(String(20), nullable=False, default="pending")
    input_text = Column(Text, nullable=False)
    result_text = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    conversation = relationship("Conversation", back_populates="jobs")
