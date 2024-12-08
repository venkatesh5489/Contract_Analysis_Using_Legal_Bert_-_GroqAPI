from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Optional
from datetime import datetime

from schema import Base, Document, Clause, Comparison, Recommendation

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def save_document(self, filename: str, content: str, document_type: str) -> Optional[Document]:
        """Save uploaded document to database"""
        try:
            with self.get_session() as session:
                document = Document(
                    filename=filename,
                    content=content,
                    document_type=document_type
                )
                session.add(document)
                session.commit()
                session.refresh(document)
                return document
        except SQLAlchemyError as e:
            print(f"Error saving document: {e}")
            return None

    def save_clauses(self, document_id: int, clauses: List[Dict]) -> bool:
        """Save extracted clauses to database"""
        try:
            with self.get_session() as session:
                for clause_data in clauses:
                    clause = Clause(
                        document_id=document_id,
                        text=clause_data["text"],
                        category=clause_data["category"],
                        importance=clause_data["importance"]
                    )
                    session.add(clause)
                session.commit()
                return True
        except SQLAlchemyError as e:
            print(f"Error saving clauses: {e}")
            return False

    def save_comparison(
        self, 
        source_doc_id: int, 
        target_doc_id: int, 
        results: Dict,
        match_percentage: float,
        risk_score: float
    ) -> Optional[Comparison]:
        """Save comparison results to database"""
        try:
            with self.get_session() as session:
                comparison = Comparison(
                    source_doc_id=source_doc_id,
                    target_doc_id=target_doc_id,
                    results=results,
                    match_percentage=match_percentage,
                    risk_score=risk_score
                )
                session.add(comparison)
                session.commit()
                session.refresh(comparison)
                return comparison
        except SQLAlchemyError as e:
            print(f"Error saving comparison: {e}")
            return None

    def save_recommendations(self, comparison_id: int, recommendations: List[Dict]) -> bool:
        """Save recommendations to database"""
        try:
            with self.get_session() as session:
                for rec in recommendations:
                    recommendation = Recommendation(
                        comparison_id=comparison_id,
                        text=rec["text"],
                        priority=rec["priority"],
                        category=rec.get("category", "General")
                    )
                    session.add(recommendation)
                session.commit()
                return True
        except SQLAlchemyError as e:
            print(f"Error saving recommendations: {e}")
            return False

    def get_document_by_id(self, document_id: int) -> Optional[Document]:
        """Retrieve document by ID"""
        try:
            with self.get_session() as session:
                return session.query(Document).options(
                    joinedload(Document.clauses)
                ).filter(Document.id == document_id).first()
        except SQLAlchemyError as e:
            print(f"Error retrieving document: {e}")
            return None

    def get_comparison_results(self, comparison_id: int) -> Optional[Dict]:
        """Retrieve comparison results by ID"""
        try:
            with self.get_session() as session:
                comparison = session.query(Comparison).filter(
                    Comparison.id == comparison_id
                ).first()
                return comparison.results if comparison else None
        except SQLAlchemyError as e:
            print(f"Error retrieving comparison results: {e}")
            return None

    def get_recommendations(self, comparison_id: int) -> List[Dict]:
        """Retrieve recommendations for a comparison"""
        try:
            with self.get_session() as session:
                recommendations = session.query(Recommendation).filter(
                    Recommendation.comparison_id == comparison_id
                ).all()
                return [
                    {
                        "text": rec.text,
                        "priority": rec.priority,
                        "category": rec.category
                    }
                    for rec in recommendations
                ]
        except SQLAlchemyError as e:
            print(f"Error retrieving recommendations: {e}")
            return []
