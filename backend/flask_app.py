from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from typing import List, Dict
from PyPDF2 import PdfReader
from datetime import datetime, timedelta
from sqlalchemy.sql import func
from sqlalchemy.exc import SQLAlchemyError
from flask_cors import CORS
from sqlalchemy.orm import joinedload
import traceback

from nlp import ContractAnalyzer
from db import DatabaseManager
from schema import Document, Clause, Comparison, Recommendation

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize our components
db = DatabaseManager(os.getenv('DATABASE_URL'))
analyzer = ContractAnalyzer()

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_date(date):
    """Format datetime to ISO 8601 string"""
    if date is None:
        return None
    return date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

def serialize_document(document):
    """Serialize document object to dict"""
    return {
        'id': document.id,
        'name': document.filename,
        'type': document.document_type,
        'uploadDate': format_date(document.upload_date)
    }

def extract_text_from_file(file_path: str) -> str:
    """Extract text from uploaded file"""
    if file_path.endswith('.pdf'):
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    elif file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ""

@app.route('/api/upload/expected-terms', methods=['POST'])
def upload_expected_terms():
    """Upload and process expected terms document"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Extract text from file
        text = extract_text_from_file(file_path)
        
        # Save document to database
        document = db.save_document(filename, text, 'expected_terms')
        if not document:
            return jsonify({'error': 'Failed to save document'}), 500
        
        # Extract clauses
        clauses = analyzer.extract_clauses(text)
        
        # Save clauses to database
        if not db.save_clauses(document.id, clauses):
            return jsonify({'error': 'Failed to save clauses'}), 500
        
        response_data = serialize_document(document)
        response_data['clauses'] = clauses
        return jsonify(response_data)
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/upload/contracts', methods=['POST'])
def upload_contracts():
    """Upload and process multiple contract documents"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('files')
    if len(files) > 5:
        return jsonify({'error': 'Maximum 5 contracts allowed'}), 400
    
    results = []
    for file in files:
        if file.filename == '':
            continue
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Extract text from file
            text = extract_text_from_file(file_path)
            
            # Save document to database
            document = db.save_document(filename, text, 'contract')
            if not document:
                continue
            
            # Extract clauses
            clauses = analyzer.extract_clauses(text)
            
            # Save clauses to database
            if db.save_clauses(document.id, clauses):
                doc_data = serialize_document(document)
                doc_data['clauses'] = clauses
                results.append(doc_data)
    
    if not results:
        return jsonify({'error': 'No valid contracts processed'}), 400
    
    return jsonify({'contracts': results})

@app.route('/api/documents/<int:doc_id>/clauses', methods=['GET'])
def get_document_clauses(doc_id):
    """Get extracted clauses for a specific document"""
    try:
        with db.get_session() as session:
            document = session.query(Document).options(
                joinedload(Document.clauses)
            ).filter_by(id=doc_id).first()
            
            if not document:
                return jsonify({'error': 'Document not found'}), 404
            
            return jsonify({
                'document_type': document.document_type,
                'filename': document.filename,
                'clauses': [
                    {
                        'text': clause.text,
                        'category': clause.category,
                        'importance': clause.importance
                    }
                    for clause in document.clauses
                ]
            })
    except Exception as e:
        print("Error fetching clauses:", str(e))
        return jsonify({'error': 'Failed to fetch clauses'}), 500

@app.route('/api/compare', methods=['POST'])
def compare_contracts():
    """Compare expected terms with actual contracts"""
    data = request.json
    expected_terms_id = data.get('expected_terms_id')
    contract_ids = data.get('contract_ids', [])
    
    if not expected_terms_id or not contract_ids:
        return jsonify({'error': 'Missing document IDs'}), 400
    
    try:
        expected_doc = db.get_document_by_id(expected_terms_id)
        if not expected_doc or expected_doc.document_type != 'expected_terms':
            return jsonify({'error': 'Invalid expected terms document'}), 400
        
        results = []
        for contract_id in contract_ids:
            try:
                contract_doc = db.get_document_by_id(contract_id)
                if not contract_doc or contract_doc.document_type != 'contract':
                    print(f"Invalid contract document: {contract_id}")
                    continue
                
                # Get clauses for both documents
                expected_clauses = [
                    {
                        'number': str(i + 1),
                        'text': c.text,
                        'category': c.category,
                        'importance': c.importance
                    }
                    for i, c in enumerate(expected_doc.clauses)
                ]
                contract_clauses = [
                    {
                        'number': str(i + 1),
                        'text': c.text,
                        'category': c.category,
                        'importance': c.importance
                    }
                    for i, c in enumerate(contract_doc.clauses)
                ]
                
                # Perform comparison with enhanced analysis
                comparison_results = analyzer.compare_contracts(expected_clauses, contract_clauses)
                
                # Calculate metrics
                match_percentage = comparison_results['summary']['overall_similarity'] * 100
                risk_level = comparison_results['summary'].get('risk_level', 'Medium')  # Default to Medium if not set
                
                # Ensure risk_level is valid
                if risk_level not in ['High', 'Medium', 'Low']:
                    risk_level = 'Medium'  # Default to Medium if invalid
                
                # Map risk level to score
                risk_score_mapping = {'High': 80, 'Medium': 50, 'Low': 20}
                risk_score = risk_score_mapping.get(risk_level, 50)
                
                # Create comparison record
                comparison = Comparison(
                    source_doc_id=expected_terms_id,
                    target_doc_id=contract_id,
                    results=comparison_results,
                    match_percentage=match_percentage,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    critical_issues_count=comparison_results['summary'].get('critical_issues_count', 0),
                    total_clauses=len(expected_clauses),
                    matched_clauses=comparison_results['summary'].get('match_count', 0),
                    partial_matches=comparison_results['summary'].get('partial_match_count', 0),
                    mismatches=comparison_results['summary'].get('mismatch_count', 0)
                )
                
                # Save comparison to database
                with db.get_session() as session:
                    session.add(comparison)
                    session.flush()  # Flush to get the ID
                    comparison_id = comparison.id
                    
                    # Save recommendations
                    for rec in comparison_results.get('recommendations', []):
                        recommendation = Recommendation(
                            comparison_id=comparison_id,  # Use the ID we got from flush
                            text=rec['message'],
                            priority=rec['priority'],
                            category=rec.get('type', 'General'),
                            details=rec.get('details', {})
                        )
                        session.add(recommendation)
                    
                    session.commit()
                    
                    # Add comparison result to results list
                    results.append({
                        'comparison_id': comparison_id,
                        'contract_id': contract_id,
                        'results': comparison_results
                    })
                
            except Exception as e:
                print(f"Error processing contract {contract_id}: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
                continue
        
        if not results:
            return jsonify({'error': 'No valid comparisons created'}), 400
        
        return jsonify({'comparisons': results})
        
    except Exception as e:
        print(f"Error in compare_contracts: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/comparison/<int:comparison_id>', methods=['GET'])
def get_comparison_results(comparison_id):
    """Get detailed results for a specific comparison"""
    try:
        print(f"Fetching comparison results for ID: {comparison_id}")
        with db.get_session() as session:
            # First try to find the comparison
            comparison = session.query(Comparison).filter_by(id=comparison_id).first()
            if not comparison:
                print(f"No comparison found with ID: {comparison_id}")
                return jsonify({'error': 'Comparison not found'}), 404
            
            print(f"Found comparison with ID {comparison_id}")
            print(f"Source doc: {comparison.source_doc_id}, Target doc: {comparison.target_doc_id}")
            
            # Get recommendations
            recommendations = db.get_recommendations(comparison_id)
            print(f"Found {len(recommendations)} recommendations")
            
            # Prepare response
            response_data = {
                'comparison_id': comparison.id,
                'source_doc_id': comparison.source_doc_id,
                'target_doc_id': comparison.target_doc_id,
                'match_percentage': comparison.match_percentage,
                'risk_score': comparison.risk_score,
                'results': comparison.results,
                'recommendations': recommendations
            }
            
            print(f"Returning comparison data: {response_data}")
            return jsonify(response_data)
            
    except SQLAlchemyError as e:
        error_msg = f"Database error retrieving comparison {comparison_id}: {str(e)}"
        print(error_msg)
        return jsonify({'error': 'Failed to retrieve comparison'}), 500
    except Exception as e:
        error_msg = f"Unexpected error retrieving comparison {comparison_id}: {str(e)}"
        print(error_msg)
        return jsonify({'error': 'Failed to retrieve comparison'}), 500

# Admin Dashboard Endpoints

@app.route('/api/admin/statistics', methods=['GET'])
def get_admin_statistics():
    """Get overall system statistics"""
    try:
        with db.get_session() as session:
            total_documents = session.query(Document).count()
            total_comparisons = session.query(Comparison).count()
            
            # Get documents processed in last 24 hours
            recent_docs = session.query(Document).filter(
                Document.upload_date >= datetime.utcnow() - timedelta(days=1)
            ).count()
            
            # Average match percentage and risk score
            avg_metrics = session.query(
                func.avg(Comparison.match_percentage).label('avg_match'),
                func.avg(Comparison.risk_score).label('avg_risk')
            ).first()
            
            # Document type distribution
            doc_types = session.query(
                Document.document_type,
                func.count(Document.id)
            ).group_by(Document.document_type).all()
            
            return jsonify({
                'total_documents': total_documents,
                'total_comparisons': total_comparisons,
                'recent_documents': recent_docs,
                'average_match_percentage': round(avg_metrics.avg_match or 0, 2),
                'average_risk_score': round(avg_metrics.avg_risk or 0, 2),
                'document_distribution': dict(doc_types)
            })
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/recent-activity', methods=['GET'])
def get_recent_activity():
    """Get recent system activity"""
    try:
        with db.get_session() as session:
            # Get recent comparisons with related documents
            recent_comparisons = session.query(Comparison)\
                .order_by(Comparison.comparison_date.desc())\
                .limit(10)\
                .all()
            
            activity = []
            for comp in recent_comparisons:
                source_doc = session.query(Document).get(comp.source_doc_id)
                target_doc = session.query(Document).get(comp.target_doc_id)
                
                activity.append({
                    'type': 'comparison',
                    'date': comp.comparison_date.isoformat(),
                    'source_document': source_doc.filename,
                    'target_document': target_doc.filename,
                    'match_percentage': comp.match_percentage,
                    'risk_score': comp.risk_score
                })
            
            return jsonify({'recent_activity': activity})
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/high-risk-contracts', methods=['GET'])
def get_high_risk_contracts():
    """Get contracts with high risk scores"""
    try:
        with db.get_session() as session:
            high_risk = session.query(Comparison)\
                .filter(Comparison.risk_score >= 70)\
                .order_by(Comparison.risk_score.desc())\
                .limit(5)\
                .all()
            
            results = []
            for comp in high_risk:
                source_doc = session.query(Document).get(comp.source_doc_id)
                target_doc = session.query(Document).get(comp.target_doc_id)
                
                results.append({
                    'comparison_id': comp.id,
                    'source_document': source_doc.filename,
                    'target_document': target_doc.filename,
                    'risk_score': comp.risk_score,
                    'comparison_date': comp.comparison_date.isoformat()
                })
            
            return jsonify({'high_risk_contracts': results})
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/performance-metrics', methods=['GET'])
def get_performance_metrics():
    """Get system performance metrics"""
    try:
        with db.get_session() as session:
            # Get average processing times
            processing_times = session.query(
                func.avg(Comparison.comparison_date - Document.upload_date)
            ).join(Document, Document.id == Comparison.source_doc_id).first()
            
            # Get success rates
            total_uploads = session.query(Document).count()
            successful_comparisons = session.query(Comparison).count()
            
            # Get clause extraction statistics
            clause_stats = session.query(
                func.avg(func.array_length(Document.clauses, 1)),
                func.max(func.array_length(Document.clauses, 1))
            ).first()
            
            return jsonify({
                'avg_processing_time_seconds': float(processing_times[0].total_seconds()) if processing_times[0] else 0,
                'success_rate': (successful_comparisons / total_uploads * 100) if total_uploads > 0 else 0,
                'avg_clauses_per_document': round(float(clause_stats[0] or 0), 2),
                'max_clauses_in_document': int(clause_stats[1] or 0)
            })
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
