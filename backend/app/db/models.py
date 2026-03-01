"""SQLAlchemy models."""
from sqlalchemy import (
    Column, Integer, String, Text, Float, ForeignKey, UniqueConstraint,
    DateTime, JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class Journal(Base):
    __tablename__ = "journals"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(512), nullable=False)
    issn_online = Column(String(32), nullable=True)
    openalex_source_id = Column(String(64), nullable=True, index=True)
    papers = relationship("Paper", back_populates="journal")


class Paper(Base):
    __tablename__ = "papers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    openalex_work_id = Column(String(128), unique=True, nullable=False, index=True)
    title = Column(String(1024), nullable=False)
    year = Column(Integer, nullable=True)
    doi = Column(String(256), nullable=True)
    published_date = Column(String(32), nullable=True)
    primary_url = Column(String(512), nullable=True)
    journal_id = Column(Integer, ForeignKey("journals.id"), nullable=False)
    abstract_text = Column(Text, nullable=True)
    concepts_hint = Column(Text, nullable=True)
    raw_json = Column(JSON, nullable=True)
    best_category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    journal = relationship("Journal", back_populates="papers")
    organizations = relationship("Organization", secondary="paper_org", back_populates="papers")
    category_assignments = relationship("PaperCategory", back_populates="paper", cascade="all, delete-orphan")
    best_category = relationship("Category", foreign_keys=[best_category_id])


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    openalex_org_id = Column(String(128), unique=True, nullable=True, index=True)
    name = Column(String(512), nullable=False)
    country_code = Column(String(8), nullable=True)
    papers = relationship("Paper", secondary="paper_org", back_populates="organizations")


class PaperOrg(Base):
    __tablename__ = "paper_org"
    paper_id = Column(Integer, ForeignKey("papers.id"), primary_key=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), primary_key=True)
    __table_args__ = (UniqueConstraint("paper_id", "org_id", name="uq_paper_org"),)


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False)
    papers = relationship("PaperCategory", back_populates="category")


class PaperCategory(Base):
    __tablename__ = "paper_categories"
    paper_id = Column(Integer, ForeignKey("papers.id"), primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), primary_key=True)
    score = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=True)
    why = Column(Text, nullable=True)
    model = Column(String(64), nullable=True)
    __table_args__ = (UniqueConstraint("paper_id", "category_id", name="uq_paper_category"),)

    paper = relationship("Paper", back_populates="category_assignments")
    category = relationship("Category", back_populates="papers")
