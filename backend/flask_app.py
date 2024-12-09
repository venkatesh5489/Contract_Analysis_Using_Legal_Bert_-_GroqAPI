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
import json
import re

from nlp import ContractAnalyzer
from db import DatabaseManager
from schema import Document, Clause, Comparison, Recommendation

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
app.config['UPLOAD_EXTENSIONS'] = ['.pdf', '.txt', '.doc', '.docx']
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['CORS_HEADERS'] = 'Content-Type'

# Initialize our components
db = DatabaseManager(os.getenv('DATABASE_URL'))
analyzer = ContractAnalyzer()

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def serialize_document(document):
    """Serialize document object to dict"""
    try:
        return {
            'id': document.id,
            'name': document.filename,
            'type': document.document_type
        }
    except Exception as e:
        print(f"Error serializing document: {e}")
        return {
            'id': getattr(document, 'id', None),
            'name': getattr(document, 'filename', 'Unknown'),
            'type': getattr(document, 'document_type', 'unknown')
        }

def extract_text_from_file(file_path: str) -> str:
    """Extract text from uploaded file"""
    print(f"\nAttempting to extract text from: {file_path}")
    
    if file_path.endswith('.pdf'):
        text = ""
        try:
            with open(file_path, 'rb') as file:
                print("Successfully opened PDF file")
                pdf_reader = PdfReader(file)
                print(f"PDF has {len(pdf_reader.pages)} pages")
                
                for i, page in enumerate(pdf_reader.pages):
                    extracted = page.extract_text()
                    if extracted:
                        # Clean up excessive whitespace and line breaks
                        cleaned = ' '.join(
                            line.strip() 
                            for line in extracted.splitlines() 
                            if line.strip()
                        )
                        text += cleaned + "\n"
                        print(f"\nPage {i+1} cleaned text sample: {cleaned[:100]}")
                    else:
                        print(f"Warning: No text extracted from page {i+1}")
                
                # Final cleanup of double spaces and normalize line endings
                text = re.sub(r'\s+', ' ', text)
                text = re.sub(r'[\r\n]+', '\n', text)
                
            print(f"\nTotal extracted text length: {len(text)}")
            print(f"Sample of final cleaned text: {text[:200]}")
            return text.strip()
            
        except Exception as e:
            print(f"Error extracting PDF text: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return ""
            
    elif file_path.endswith('.txt'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
                print(f"\nExtracted text length from TXT: {len(text)}")
                return text
        except Exception as e:
            print(f"Error reading TXT file: {str(e)}")
            return ""
            
    print(f"Unsupported file type: {file_path}")
    return ""

@app.route('/api/upload/expected-terms', methods=['POST'])
def upload_expected_terms():
    """Upload and process expected terms document"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'state': {
                    'expectedTerms': None,
                    'contracts': [],
                    'loading': False,
                    'error': 'No file part'
                }
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'state': {
                    'expectedTerms': None,
                    'contracts': [],
                    'loading': False,
                    'error': 'No selected file'
                }
            }), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            text = extract_text_from_file(file_path)
            document = db.save_document(filename, text, 'expected_terms')
            
            if not document:
                return jsonify({
                    'state': {
                        'expectedTerms': None,
                        'contracts': [],
                        'loading': False,
                        'error': 'Failed to save document'
                    }
                }), 500
            
            clauses = analyzer.extract_clauses(text)
            
            if not db.save_clauses(document.id, clauses):
                return jsonify({
                    'state': {
                        'expectedTerms': None,
                        'contracts': [],
                        'loading': False,
                        'error': 'Failed to save clauses'
                    }
                }), 500
            
            doc_data = serialize_document(document)
            doc_data['clauses'] = clauses
            
            return jsonify({
                'state': {
                    'expectedTerms': doc_data,
                    'contracts': [],
                    'loading': False,
                    'error': None
                }
            })
        
        return jsonify({
            'state': {
                'expectedTerms': None,
                'contracts': [],
                'loading': False,
                'error': 'Invalid file type'
            }
        }), 400
        
    except Exception as e:
        print(f"Error processing upload: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'state': {
                'expectedTerms': None,
                'contracts': [],
                'loading': False,
                'error': str(e)
            }
        }), 500

@app.route('/api/upload/contracts', methods=['POST'])
def upload_contracts():
    """Upload and process multiple contract documents"""
    if 'files' not in request.files:
        return jsonify({
            'state': {
                'expectedTerms': None,
                'contracts': [],
                'loading': False,
                'error': 'No files part'
            }
        }), 400
    
    files = request.files.getlist('files')
    if len(files) > 5:
        return jsonify({
            'state': {
                'expectedTerms': None,
                'contracts': [],
                'loading': False,
                'error': 'Maximum 5 contracts allowed'
            }
        }), 400
    
    results = []
    for file in files:
        if file.filename == '':
            continue
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            text = extract_text_from_file(file_path)
            document = db.save_document(filename, text, 'contract')
            
            if not document:
                continue
            
            clauses = analyzer.extract_clauses(text)
            
            if db.save_clauses(document.id, clauses):
                doc_data = serialize_document(document)
                doc_data['clauses'] = clauses
                results.append(doc_data)
    
    if not results:
        return jsonify({
            'state': {
                'expectedTerms': None,
                'contracts': [],
                'loading': False,
                'error': 'No valid contracts processed'
            }
        }), 400
    
    return jsonify({
        'state': {
            'expectedTerms': None,
            'contracts': results,
            'loading': False,
            'error': None
        }
    })

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
def compare_documents():
    """Compare expected terms with actual contracts"""
    try:
        print("Received comparison request")
        data = request.get_json()
        print("Request data:", data)
        
        expected_terms_id = data.get('expected_terms_id')
        contract_ids = data.get('contract_ids', [])
        
        if not expected_terms_id or not contract_ids:
            return jsonify({
                'error': 'Missing required fields',
                'message': 'Both expected_terms_id and contract_ids are required'
            }), 400
            
        print(f"Processing comparison - Expected Terms ID: {expected_terms_id}, Contract IDs: {contract_ids}")
        
        # Get expected terms document
        expected_doc = db.get_document_by_id(expected_terms_id)
        if not expected_doc:
            return jsonify({
                'error': 'Document not found',
                'message': f'Expected terms document {expected_terms_id} not found'
            }), 404
            
        if not hasattr(expected_doc, 'document_type') or expected_doc.document_type != 'expected_terms':
            return jsonify({
                'error': 'Invalid document type',
                'message': 'Document is not an expected terms document'
            }), 400
        
        results = []
        for contract_id in contract_ids:
            try:
                # Get contract document
                contract_doc = db.get_document_by_id(contract_id)
                if not contract_doc:
                    print(f"Contract document not found: {contract_id}")
                    continue
                    
                if not hasattr(contract_doc, 'document_type') or contract_doc.document_type != 'contract':
                    print(f"Invalid contract document type: {contract_id}")
                    continue
                
                print(f"Processing contract: {contract_id}")
                
                # Get document metadata safely
                expected_doc_data = {
                    'id': expected_doc.id,
                    'filename': getattr(expected_doc, 'filename', 'Unknown'),
                    'document_type': expected_doc.document_type,
                    'clauses': [
                        {
                            'number': str(i + 1),
                            'text': getattr(c, 'text', ''),
                            'category': getattr(c, 'category', 'Unknown'),
                            'importance': getattr(c, 'importance', 'Medium')
                        }
                        for i, c in enumerate(getattr(expected_doc, 'clauses', []))
                    ]
                }
                
                contract_doc_data = {
                    'id': contract_doc.id,
                    'filename': getattr(contract_doc, 'filename', 'Unknown'),
                    'document_type': contract_doc.document_type,
                    'clauses': [
                        {
                            'number': str(i + 1),
                            'text': getattr(c, 'text', ''),
                            'category': getattr(c, 'category', 'Unknown'),
                            'importance': getattr(c, 'importance', 'Medium')
                        }
                        for i, c in enumerate(getattr(contract_doc, 'clauses', []))
                    ]
                }
                
                print(f"Comparing {len(expected_doc_data['clauses'])} expected clauses with {len(contract_doc_data['clauses'])} contract clauses")
                
                # Perform comparison with enhanced analysis
                comparison_results = analyzer.compare_contracts(
                    expected_doc_data['clauses'],
                    contract_doc_data['clauses']
                )
                
                print("Comparison results:", comparison_results)
                
                # Calculate metrics
                match_percentage = comparison_results['summary']['overall_similarity']
                
                # Calculate risk score based on actual risk assessment
                risk_points = analyzer._assess_change_risk(comparison_results['differences'])
                
                # Map risk points to valid risk levels
                if risk_points >= 70:
                    risk_level = 'High'
                elif risk_points >= 40:
                    risk_level = 'Medium'
                else:
                    risk_level = 'Low'  # Default to Low instead of Minimal
                
                print(f"Analysis complete - Match: {match_percentage:.1f}%, Risk Level: {risk_level}")
                
                # Create comparison record
                comparison = Comparison(
                    source_doc_id=expected_terms_id,
                    target_doc_id=contract_id,
                    results=comparison_results,
                    match_percentage=match_percentage,
                    risk_score=risk_points,
                    risk_level=risk_level,
                    critical_issues_count=comparison_results['summary']['critical_issues_count'],
                    total_clauses=len(expected_doc_data['clauses']),
                    matched_clauses=comparison_results['summary']['match_count'],
                    partial_matches=comparison_results['summary']['partial_match_count'],
                    mismatches=comparison_results['summary']['mismatch_count']
                )
                
                # Save comparison to database
                with db.get_session() as session:
                    session.add(comparison)
                    session.flush()  # Flush to get the ID
                    comparison_id = comparison.id
                    
                    # Save recommendations
                    for rec in comparison_results.get('recommendations', []):
                        recommendation = Recommendation(
                            comparison_id=comparison_id,
                            text=rec['message'],
                            priority=rec['priority'],
                            category=rec.get('type', 'General'),
                            details=rec.get('details', {})
                        )
                        session.add(recommendation)
                    
                    session.commit()
                    print(f"Saved comparison with ID: {comparison_id}")
                    
                    # Format response data
                    results.append({
                        'id': comparison_id,
                        'expected_terms': {
                            'id': expected_doc_data['id'],
                            'name': expected_doc_data['filename'],
                            'clauses': expected_doc_data['clauses']
                        },
                        'contract': {
                            'id': contract_doc_data['id'],
                            'name': contract_doc_data['filename'],
                            'clauses': contract_doc_data['clauses']
                        },
                        'match_percentage': match_percentage,
                        'risk_score': risk_points,
                        'risk_level': risk_level,
                        'results': {
                            'matches': comparison_results['matches'],
                            'partial_matches': comparison_results['partial_matches'],
                            'mismatches': comparison_results['mismatches'],
                            'component_scores': comparison_results['component_scores'],
                            'critical_analysis': comparison_results['critical_analysis'],
                            'differences': comparison_results['differences']
                        },
                        'recommendations': comparison_results.get('recommendations', [])
                    })
            
            except Exception as e:
                print(f"Error processing contract {contract_id}: {str(e)}")
                traceback.print_exc()
                continue
        
        if not results:
            return jsonify({
                'error': 'Processing failed',
                'message': 'No valid comparisons could be created'
            }), 400
        
        print(f"Successfully processed {len(results)} comparisons")
        return jsonify({'comparisons': results}), 200
            
    except Exception as e:
        print(f"Error in comparison: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

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

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify server is running"""
    return jsonify({'status': 'ok', 'message': 'Server is running'})

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    try:
        # Create upload folder if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        print("Starting Flask application...")
        # Remove use_reloader=False to allow normal development server behavior
        app.run(debug=True, port=5000)
    except KeyboardInterrupt:
        print("Shutting down Flask application...")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise
