from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, String, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base


class Prompt(Base):
    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    responses   = relationship("Response", back_populates="prompt", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="prompt", cascade="all, delete-orphan")
    suggestions = relationship("Suggestion", back_populates="prompt", cascade="all, delete-orphan")
    feedback    = relationship("Feedback", back_populates="prompt", cascade="all, delete-orphan")


class Response(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String(64))
    content = Column(Text, nullable=False)
    latency_ms = Column(Integer)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    prompt = relationship("Prompt", back_populates="responses")
    evaluations = relationship("Evaluation", back_populates="response", cascade="all, delete-orphan")


class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
    response_id = Column(Integer, ForeignKey("responses.id", ondelete="SET NULL"))
    clarity_score = Column(Float)
    length_score = Column(Float)
    toxicity_score = Column(Float)
    overall_score = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_canary = Column(Boolean, nullable=False, server_default="0")

    prompt = relationship("Prompt", back_populates="evaluations")
    response = relationship("Response", back_populates="evaluations")


class Suggestion(Base):
    __tablename__ = "suggestions"
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
    suggested_text = Column(Text, nullable=False)
    rationale = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    prompt = relationship("Prompt", back_populates="suggestions")


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
    response_id = Column(Integer, ForeignKey("responses.id", ondelete="SET NULL"))
    rating = Column(Integer)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    prompt = relationship("Prompt", back_populates="feedback")


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    prompt = relationship("Prompt", backref="versions")


class PromptRelease(Base):
    __tablename__ = "prompt_releases"
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
    active_version_id = Column(Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"))
    canary_version_id = Column(Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"))
    canary_percent = Column(Integer, nullable=False, server_default="0")  # 0..100
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    prompt = relationship("Prompt")
    active_version = relationship("PromptVersion", foreign_keys=[active_version_id])
    canary_version = relationship("PromptVersion", foreign_keys=[canary_version_id])


class RollbackEvent(Base):
    __tablename__ = "rollback_events"
    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
    from_version_id = Column(Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"))
    to_version_id = Column(Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"))
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    prompt = relationship("Prompt")
    from_version = relationship("PromptVersion", foreign_keys=[from_version_id])
    to_version = relationship("PromptVersion", foreign_keys=[to_version_id])
