from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from datetime import datetime

Base = declarative_base()

class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False)  # 'contract' or 'expected_terms'
    upload_date = Column(DateTime, default=datetime.utcnow)
    content = Column(String, nullable=False)
    
    # Relationships
    clauses = relationship("Clause", back_populates="document")
    comparisons_as_source = relationship("Comparison", 
                                       foreign_keys="Comparison.source_doc_id",
                                       back_populates="source_document")
    comparisons_as_target = relationship("Comparison", 
                                       foreign_keys="Comparison.target_doc_id",
                                       back_populates="target_document")

class Clause(Base):
    __tablename__ = 'clauses'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'))
    text = Column(String, nullable=False)
    category = Column(String(50))
    importance = Column(String(20))  # High, Medium, Low
    
    # Relationships
    document = relationship("Document", back_populates="clauses")

class Comparison(Base):
    __tablename__ = 'comparisons'

    id = Column(Integer, primary_key=True)
    source_doc_id = Column(Integer, ForeignKey('documents.id'))
    target_doc_id = Column(Integer, ForeignKey('documents.id'))
    comparison_date = Column(DateTime, default=datetime.utcnow)
    
    # Enhanced results storage
    results = Column(JSON)  # Stores detailed comparison results
    
    # Overall metrics
    match_percentage = Column(Float)
    risk_score = Column(Float)
    
    # New fields from migration
    critical_issues_count = Column(Integer, default=0)
    risk_level = Column(String(20))  # High, Medium, Low
    total_clauses = Column(Integer)
    matched_clauses = Column(Integer)
    partial_matches = Column(Integer)
    mismatches = Column(Integer)
    
    # Relationships
    recommendations = relationship("Recommendation", back_populates="comparison")
    source_document = relationship("Document", 
                                 foreign_keys=[source_doc_id],
                                 back_populates="comparisons_as_source")
    target_document = relationship("Document", 
                                 foreign_keys=[target_doc_id],
                                 back_populates="comparisons_as_target")

    @validates('risk_level')
    def validate_risk_level(self, key, value):
        valid_levels = ['High', 'Medium', 'Low']
        if value not in valid_levels:
            raise ValueError(f"Risk level must be one of: {', '.join(valid_levels)}")
        return value

    @validates('results')
    def validate_results(self, key, value):
        required_keys = ['summary', 'matches', 'partial_matches', 'mismatches', 'critical_analysis']
        if not isinstance(value, dict):
            raise ValueError("Results must be a dictionary")
        if not all(k in value for k in required_keys):
            raise ValueError(f"Results must contain all required keys: {', '.join(required_keys)}")
        return value

    def to_dict(self):
        """Convert comparison results to a structured dictionary."""
        return {
            'id': self.id,
            'comparison_date': self.comparison_date.isoformat(),
            'summary': {
                'match_percentage': self.match_percentage,
                'risk_level': self.risk_level,
                'critical_issues_count': self.critical_issues_count,
                'total_clauses': self.total_clauses,
                'matched_clauses': self.matched_clauses,
                'partial_matches': self.partial_matches,
                'mismatches': self.mismatches
            },
            'results': self.results,
            'recommendations': [rec.to_dict() for rec in self.recommendations]
        }

class Recommendation(Base):
    __tablename__ = 'recommendations'

    id = Column(Integer, primary_key=True)
    comparison_id = Column(Integer, ForeignKey('comparisons.id'))
    text = Column(String, nullable=False)
    priority = Column(String(20))  # High, Medium, Low
    category = Column(String(50))  # Legal, Financial, Operational, etc.
    details = Column(JSON)  # Store detailed information about the recommendation
    
    # Relationship
    comparison = relationship("Comparison", back_populates="recommendations")

    @validates('priority')
    def validate_priority(self, key, value):
        valid_priorities = ['High', 'Medium', 'Low']
        if value not in valid_priorities:
            raise ValueError(f"Priority must be one of: {', '.join(valid_priorities)}")
        return value

    def to_dict(self):
        """Convert recommendation to dictionary."""
        return {
            'id': self.id,
            'text': self.text,
            'priority': self.priority,
            'category': self.category,
            'details': self.details
        }
