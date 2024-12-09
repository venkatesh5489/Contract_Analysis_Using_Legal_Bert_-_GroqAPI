# Standard library imports
import os
import re
import sys
import json
import traceback
from typing import List, Dict, Tuple, Optional, Set
from nltk.tokenize import sent_tokenize
import nltk
# Third-party imports
import spacy
import groq
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Initialize logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download required NLTK data
def download_nltk_data():
    """Download required NLTK data with error handling"""
    try:
        # Download both punkt and punkt_tab
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        logging.info("Successfully downloaded NLTK data")
    except Exception as e:
        logging.error(f"Error downloading NLTK data: {e}")
        logging.error(traceback.format_exc())
        # Create fallback tokenizer if download fails
        global sent_tokenize
        sent_tokenize = lambda text: text.split('.')

# Download NLTK data on module import
download_nltk_data()

class ContractAnalyzer:
    def __init__(self):
        # Initialize Legal model for semantic similarity
        try:
            # Using InLegalBERT - trained on 42GB of legal documents including contracts
            self.similarity_model = SentenceTransformer('law-ai/InLegalBERT')
            logging.info("Successfully loaded Legal model")
            
            # Verify model is working
            test_text = "This is a test sentence."
            try:
                _ = self.similarity_model.encode([test_text])[0]
                logging.info("Legal model successfully verified")
            except Exception as e:
                logging.error(f"Legal model verification failed: {e}")
                raise
                
        except Exception as e:
            logging.error(f"Error loading Legal model: {e}")
            # Fallback to a smaller, general-purpose model if Legal model fails
            try:
                self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
                logging.warning("Falling back to MiniLM model")
                
                # Verify fallback model
                test_text = "This is a test sentence."
                _ = self.similarity_model.encode([test_text])[0]
                logging.info("Fallback model successfully verified")
            except Exception as e:
                logging.error(f"Critical error: Both models failed to load: {e}")
                raise RuntimeError("No similarity model available")
        
        # Initialize spaCy NLP model for NER
        try:
            self.nlp = spacy.load('en_core_web_sm')
            logging.info("Successfully loaded spaCy model")
        except OSError:
            logging.warning("Downloading spaCy model...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load('en_core_web_sm')
            logging.info("Successfully downloaded and loaded spaCy model")
        except Exception as e:
            logging.error(f"Error loading spaCy model: {e}")
            raise
        
        # Initialize Groq client with proper error handling
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            logging.warning("GROQ_API_KEY not found in environment variables")
            self.groq_client = None
        else:
            try:
                self.groq_client = groq.Groq(
                    api_key=api_key,
                    base_url="https://api.groq.com/v1"
                )
                logging.info("Successfully initialized Groq client")
            except Exception as e:
                logging.error(f"Error initializing Groq client: {e}")
                self.groq_client = None

        # Initialize TF-IDF vectorizer for text comparison
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.tfidf = TfidfVectorizer(
            stop_words='english',
            max_features=10000,
            ngram_range=(1, 3)
        )
        
        
        # Compile regex patterns for numeric matching
        self.numeric_patterns = {
            'date': re.compile(
                r'\b(?:' +
                # Standard date formats (DD/MM/YYYY, MM/DD/YYYY, YYYY/MM/DD)
                r'\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|' +
                # Written month formats
                r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|' +
                r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
                r'\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|' +
                # ISO format
                r'\d{4}-\d{2}-\d{2}|' +
                # Relative dates
                r'(?:today|tomorrow|yesterday)|' +
                # Quarter format
                r'Q[1-4]\s+\d{4}' +
                r')\b'
            ),
            'money': re.compile(
                r'\b(?:' +
                # Currency symbols with amounts
                r'(?:USD|€|£|\$|¥)\s*\d+(?:,\d{3})*(?:\.\d{2})?|' +
                # Amounts with currency codes
                r'\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|JPY|dollars?|euros?|pounds?)|' +
                # Written amounts
                r'(?:zero|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:hundred|thousand|million|billion)?\s*(?:dollars?|euros?|pounds?)|' +
                # Ranges
                r'(?:USD|€|£|\$|¥)\s*\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:-|to)\s*(?:USD|€|£|\$|¥)\s*\d+(?:,\d{3})*(?:\.\d{2})?' +
                r')\b'
            ),
            'percentage': re.compile(
                r'\b(?:' +
                # Standard percentage
                r'\d+(?:\.\d+)?%|' +
                # Written percentage
                r'(?:zero|one|two|three|four|five|six|seven|eight|nine|ten)\s+percent(?:age)?|' +
                # Fractional percentage
                r'\d+/\d+\s*percent(?:age)?' +
                r')\b'
            ),
            'duration': re.compile(
                r'\b(?:' +
                # Standard duration with units
                r'\d+(?:\.\d+)?\s*(?:second|minute|hour|day|week|month|quarter|year|decade)s?|' +
                # Written duration
                r'(?:zero|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:second|minute|hour|day|week|month|quarter|year|decade)s?|' +
                # Time ranges
                r'\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?\s*(?:second|minute|hour|day|week|month|quarter|year|decade)s?|' +
                # Duration with multiple units
                r'\d+\s*(?:year|yr)s?\s*(?:and)?\s*\d+\s*(?:month|mo)s?|' +
                # Specific period mentions
                r'(?:annual(?:ly)?|monthly|weekly|daily|quarterly|bi-annual(?:ly)?|semi-annual(?:ly)?)' +
                r')\b'
            )
        }

        # Enhanced domain keywords with more specific terms and subcategories
        self.domain_keywords = {
            'employment': {
                'core_terms': [
                    'employee', 'employer', 'employment', 'work', 'worker', 'staff',
                    'personnel', 'hire', 'hiring', 'recruit', 'recruitment'
                ],
                'compensation': [
                    'salary', 'wage', 'compensation', 'pay', 'payroll', 'bonus',
                    'commission', 'incentive', 'remuneration', 'stock option',
                    'equity', 'benefits', 'allowance', 'reimbursement'
                ],
                'benefits': [
                    'health insurance', 'life insurance', 'dental', 'vision',
                    'retirement', '401k', 'pension', 'paid time off', 'pto',
                    'vacation', 'sick leave', 'parental leave', 'medical leave'
                ],
                'termination': [
                    'termination', 'resignation', 'dismissal', 'severance',
                    'notice period', 'layoff', 'redundancy', 'cause',
                    'separation', 'exit', 'final settlement'
                ],
                'workplace': [
                    'workplace', 'office', 'remote work', 'hybrid', 'location',
                    'work hours', 'schedule', 'overtime', 'flexible hours',
                    'workspace', 'facilities', 'equipment'
                ]
            },
            'lease': {
                'core_terms': [
                    'lease', 'rent', 'tenancy', 'landlord', 'tenant', 'lessee',
                    'lessor', 'occupancy', 'premises', 'property'
                ],
                'property_details': [
                    'commercial space', 'residential', 'building', 'unit',
                    'square feet', 'floor', 'parking', 'common areas',
                    'facilities', 'amenities', 'improvements'
                ],
                'financial': [
                    'rent payment', 'security deposit', 'advance rent',
                    'maintenance fee', 'utilities', 'property tax',
                    'insurance', 'late fee', 'escalation'
                ],
                'maintenance': [
                    'repairs', 'maintenance', 'alterations', 'renovations',
                    'improvements', 'fixtures', 'equipment', 'utilities',
                    'services', 'cleaning', 'waste disposal'
                ],
                'compliance': [
                    'zoning', 'permits', 'licenses', 'regulations', 'codes',
                    'safety', 'environmental', 'inspection', 'certificate of occupancy'
                ]
            },
            'nda': {
                'core_terms': [
                    'confidential', 'confidentiality', 'non-disclosure',
                    'proprietary', 'secret', 'private', 'sensitive'
                ],
                'information_types': [
                    'trade secret', 'intellectual property', 'business plan',
                    'customer data', 'financial data', 'technical data',
                    'research', 'development', 'source code', 'formula'
                ],
                'obligations': [
                    'protect', 'safeguard', 'secure', 'restrict', 'limit',
                    'prevent disclosure', 'maintain secrecy', 'return',
                    'destroy', 'notify'
                ],
                'exceptions': [
                    'public domain', 'prior knowledge', 'third party',
                    'court order', 'regulatory requirement', 'permitted disclosure'
                ],
                'duration': [
                    'term', 'period', 'survival', 'perpetual', 'expiration',
                    'termination', 'duration', 'time limit'
                ]
            },
            'sla': {
                'core_terms': [
                    'service level', 'performance', 'quality', 'standard',
                    'metric', 'measurement', 'target', 'threshold'
                ],
                'metrics': [
                    'uptime', 'availability', 'reliability', 'response time',
                    'resolution time', 'throughput', 'capacity', 'error rate',
                    'accuracy', 'quality score'
                ],
                'support': [
                    'technical support', 'customer support', 'help desk',
                    'maintenance', 'troubleshooting', 'incident response',
                    'problem resolution', 'bug fix', 'patch'
                ],
                'reporting': [
                    'monitoring', 'reporting', 'measurement', 'tracking',
                    'audit', 'review', 'assessment', 'evaluation',
                    'dashboard', 'analytics'
                ],
                'remedies': [
                    'penalty', 'credit', 'refund', 'compensation',
                    'termination right', 'cure period', 'remedy',
                    'service credit', 'liquidated damages'
                ]
            },
            'vendor': {
                'core_terms': [
                    'vendor', 'supplier', 'provider', 'contractor',
                    'manufacturer', 'distributor', 'seller', 'service provider'
                ],
                'deliverables': [
                    'goods', 'products', 'services', 'materials',
                    'deliverables', 'specifications', 'requirements',
                    'scope of work', 'statement of work'
                ],
                'quality': [
                    'quality control', 'inspection', 'testing', 'acceptance',
                    'rejection', 'warranty', 'guarantee', 'compliance',
                    'standards', 'certification'
                ],
                'logistics': [
                    'delivery', 'shipping', 'transportation', 'packaging',
                    'inventory', 'storage', 'warehouse', 'lead time',
                    'schedule', 'timeline'
                ],
                'payment': [
                    'price', 'payment terms', 'invoice', 'billing',
                    'discount', 'credit terms', 'purchase order',
                    'taxes', 'fees', 'expenses'
                ]
            },
            'partnership': {
                'core_terms': [
                    'partner', 'partnership', 'joint venture', 'collaboration',
                    'alliance', 'cooperative', 'consortium', 'association'
                ],
                'structure': [
                    'ownership', 'equity', 'shares', 'voting rights',
                    'management rights', 'control', 'governance',
                    'board', 'committee'
                ],
                'financial': [
                    'capital contribution', 'profit sharing', 'loss sharing',
                    'distribution', 'dividend', 'investment', 'funding',
                    'accounting', 'audit'
                ],
                'operations': [
                    'management', 'decision making', 'authority', 'responsibility',
                    'duties', 'obligations', 'restrictions', 'limitations'
                ],
                'exit': [
                    'dissolution', 'termination', 'withdrawal', 'buyout',
                    'transfer', 'sale', 'right of first refusal',
                    'valuation', 'liquidation'
                ]
            }
        }

        # Legal term normalizations for better matching
        self.legal_term_normalizations = {
            # Obligation terms
            'shall': [
                'must', 'will', 'is required to', 'is obligated to', 
                'is duty-bound to', 'has a duty to', 'is bound to',
                'agrees to', 'commits to', 'is responsible for'
            ],
            'shall not': [
                'must not', 'will not', 'is not permitted to', 
                'is prohibited from', 'is not allowed to',
                'may not', 'is forbidden from', 'cannot'
            ],
            
            # Action terms
            'terminate': [
                'end', 'cancel', 'discontinue', 'cease', 'conclude',
                'stop', 'finish', 'break off', 'dissolve', 'rescind',
                'void', 'nullify', 'revoke'
            ],
            'execute': [
                'sign', 'complete', 'perform', 'carry out', 'accomplish',
                'fulfill', 'implement', 'effect', 'consummate'
            ],
            'warrant': [
                'guarantee', 'assure', 'pledge', 'promise', 'certify',
                'represent', 'declare', 'confirm', 'verify', 'attest'
            ],
            
            # Protection terms
            'indemnify': [
                'hold harmless', 'protect against loss', 'compensate for loss',
                'reimburse', 'make whole', 'shield from liability',
                'defend', 'save harmless', 'secure against loss'
            ],
            'safeguard': [
                'protect', 'secure', 'shield', 'preserve', 'guard',
                'keep safe', 'maintain', 'defend', 'conserve'
            ],
            
            # Time-related terms
            'forthwith': [
                'immediately', 'without delay', 'at once', 'promptly',
                'right away', 'instantly', 'directly', 'straightaway'
            ],
            'hereinafter': [
                'later in this document', 'below', 'subsequently',
                'following this', 'afterward', 'later described'
            ],
            
            # Reference terms
            'herein': [
                'in this agreement', 'in this document', 'in these terms',
                'in this contract', 'within this agreement'
            ],
            'thereof': [
                'of that', 'of it', 'of the same', 'connected with it',
                'related to it', 'of the aforementioned'
            ],
            'thereto': [
                'to that', 'to it', 'to the same', 'in relation to',
                'in connection with', 'regarding that'
            ],
            
            # Condition terms
            'force majeure': [
                'act of god', 'unforeseen circumstances', 'superior force',
                'unavoidable accident', 'unforeseeable circumstances',
                'exceptional circumstances', 'uncontrollable events'
            ],
            'condition precedent': [
                'prerequisite', 'prior condition', 'precondition',
                'requirement', 'necessary condition', 'contingency'
            ],
            
            # Legal reference terms
            'pursuant to': [
                'according to', 'in accordance with', 'as per',
                'in compliance with', 'under', 'following',
                'in conformity with', 'as specified in'
            ],
            'notwithstanding': [
                'despite', 'regardless of', 'even if', 'although',
                'in spite of', 'without regard to', 'nevertheless'
            ],
            
            # Modification terms
            'amend': [
                'modify', 'change', 'alter', 'revise', 'update',
                'adjust', 'edit', 'correct', 'reform'
            ],
            'waive': [
                'give up', 'relinquish', 'forfeit', 'abandon',
                'surrender', 'renounce', 'disclaim', 'forgo'
            ],
            
            # Interpretation terms
            'reasonable': [
                'fair', 'sensible', 'rational', 'appropriate',
                'suitable', 'moderate', 'just', 'equitable'
            ],
            'material': [
                'significant', 'substantial', 'important', 'relevant',
                'crucial', 'essential', 'key', 'fundamental'
            ],
            
            # Modern additions
            'click-wrap': [
                'click-through', 'click-accept', 'electronic consent',
                'digital agreement', 'online acceptance'
            ],
            'electronic signature': [
                'digital signature', 'e-signature', 'electronic execution',
                'digital authorization', 'electronic authentication'
            ]
        }

        # Add domain-specific entity patterns for spaCy
        self.entity_patterns = {
            'employment': [
                # Position and Role patterns
                {'label': 'POSITION', 'pattern': [{'LOWER': {'IN': ['position', 'role', 'title', 'job']}}, {'POS': 'NOUN'}]},
                {'label': 'POSITION', 'pattern': [{'POS': 'NOUN'}, {'LOWER': 'position'}]},
                {'label': 'POSITION', 'pattern': [{'ENT_TYPE': 'PERSON'}, {'LOWER': {'IN': ['shall', 'will', 'to']}}]},
                
                # Compensation patterns
                {'label': 'SALARY', 'pattern': [{'LOWER': {'IN': ['salary', 'compensation', 'wage', 'pay', 'remuneration']}}]},
                {'label': 'SALARY', 'pattern': [{'LIKE_NUM': True}, {'LOWER': {'IN': ['dollars', 'usd', 'per']}}]},
                {'label': 'BONUS', 'pattern': [{'LOWER': {'IN': ['bonus', 'commission', 'incentive']}}, {'LOWER': {'IN': ['payment', 'structure', 'plan']}}]},
                
                # Time and Duration patterns
                {'label': 'DURATION', 'pattern': [{'LIKE_NUM': True}, {'LOWER': {'IN': ['year', 'month', 'week', 'day', 'hour']}}]},
                {'label': 'DURATION', 'pattern': [{'LOWER': {'IN': ['term', 'period', 'duration']}}, {'LOWER': 'of'}, {'LOWER': {'IN': ['employment', 'contract', 'agreement']}}]},
                
                # Benefits patterns
                {'label': 'BENEFIT', 'pattern': [{'LOWER': {'IN': ['health', 'dental', 'vision', 'life']}}, {'LOWER': 'insurance'}]},
                {'label': 'BENEFIT', 'pattern': [{'LOWER': {'IN': ['vacation', 'sick', 'personal']}}, {'LOWER': {'IN': ['leave', 'time', 'days']}}]},
            ],
            
            'lease': [
                # Property patterns
                {'label': 'PROPERTY', 'pattern': [{'LOWER': {'IN': ['property', 'premises', 'building', 'space', 'unit']}}, {'POS': 'NOUN'}]},
                {'label': 'PROPERTY', 'pattern': [{'ENT_TYPE': 'GPE'}, {'LOWER': {'IN': ['property', 'location', 'address']}}]},
                {'label': 'PROPERTY_TYPE', 'pattern': [{'LOWER': {'IN': ['commercial', 'residential', 'industrial', 'retail']}}, {'LOWER': {'IN': ['property', 'space', 'unit']}}]},
                
                # Payment patterns
                {'label': 'RENT', 'pattern': [{'LOWER': {'IN': ['rent', 'lease', 'payment']}}, {'LIKE_NUM': True}]},
                {'label': 'RENT', 'pattern': [{'SYMBOL': {'IN': ['$', '€', '£']}}, {'LIKE_NUM': True}, {'LOWER': {'IN': ['per', 'monthly', 'annually']}}]},
                {'label': 'DEPOSIT', 'pattern': [{'LOWER': {'IN': ['security', 'damage']}}, {'LOWER': 'deposit'}]},
                
                # Term patterns
                {'label': 'TERM', 'pattern': [{'LOWER': {'IN': ['term', 'period', 'duration']}}, {'LOWER': 'of'}, {'LOWER': {'IN': ['lease', 'tenancy', 'rental']}}]},
                {'label': 'TERM', 'pattern': [{'LIKE_NUM': True}, {'LOWER': {'IN': ['year', 'month']}}]},
                
                # Area patterns
                {'label': 'AREA', 'pattern': [{'LIKE_NUM': True}, {'LOWER': {'IN': ['square', 'sq']}}, {'LOWER': {'IN': ['feet', 'ft', 'meters', 'm']}}]},
            ],
        
            
            'nda': [
                # Confidential Information patterns
                {'label': 'CONFIDENTIAL_INFO', 'pattern': [{'LOWER': {'IN': ['confidential', 'proprietary', 'secret']}}, {'LOWER': 'information'}]},
                {'label': 'CONFIDENTIAL_INFO', 'pattern': [{'LOWER': 'trade'}, {'LOWER': 'secrets'}]},
                {'label': 'CONFIDENTIAL_INFO', 'pattern': [{'LOWER': {'IN': ['technical', 'business', 'financial']}}, {'LOWER': 'data'}]},
                
                # Duration patterns
                {'label': 'DURATION', 'pattern': [{'LOWER': {'IN': ['term', 'period', 'duration']}}, {'LOWER': 'of'}, {'LOWER': 'confidentiality'}]},
                {'label': 'DURATION', 'pattern': [{'LIKE_NUM': True}, {'LOWER': {'IN': ['year', 'month']}}]},
                
                # Party patterns
                {'label': 'PARTY', 'pattern': [{'LOWER': {'IN': ['disclosing', 'receiving']}}, {'LOWER': 'party'}]},
                {'label': 'PARTY', 'pattern': [{'ENT_TYPE': 'ORG'}, {'LOWER': {'IN': ['party', 'entity', 'company']}}]},
            ],
            
            
            
        
            'sla': [
                # Service Level patterns
                {'label': 'SERVICE_LEVEL', 'pattern': [{'LOWER': {'IN': ['availability', 'uptime', 'performance']}}, {'LOWER': {'IN': ['level', 'target', 'requirement']}}]},
                {'label': 'SERVICE_LEVEL', 'pattern': [{'LIKE_NUM': True}, {'LOWER': '%'}, {'LOWER': {'IN': ['availability', 'uptime']}}]},
                
                # Response Time patterns
                {'label': 'RESPONSE_TIME', 'pattern': [{'LOWER': {'IN': ['response', 'resolution']}}, {'LOWER': 'time'}]},
                {'label': 'RESPONSE_TIME', 'pattern': [{'LIKE_NUM': True}, {'LOWER': {'IN': ['hour', 'minute', 'second']}}]},
                
                # Penalty patterns
                {'label': 'PENALTY', 'pattern': [{'LOWER': {'IN': ['penalty', 'credit', 'refund']}}, {'LOWER': {'IN': ['amount', 'calculation', 'rate']}}]},
                {'label': 'PENALTY', 'pattern': [{'LOWER': 'service'}, {'LOWER': 'credit'}]},
                
                # Timeline patterns
                {'label': 'TIMELINE', 'pattern': [{'LOWER': {'IN': ['delivery', 'completion', 'milestone']}}, {'LOWER': {'IN': ['date', 'schedule', 'timeline']}}]},
                {'label': 'TIMELINE', 'pattern': [{'LIKE_NUM': True}, {'LOWER': {'IN': ['day', 'week', 'month']}}]},
            ],


            
            'vendor': [
                # Deliverable patterns
                {'label': 'DELIVERABLE', 'pattern': [{'LOWER': {'IN': ['product', 'service', 'good', 'deliverable']}}, {'POS': 'NOUN'}]},
                {'label': 'DELIVERABLE', 'pattern': [{'LOWER': 'scope'}, {'LOWER': 'of'}, {'LOWER': 'work'}]},
                
                # Payment patterns
                {'label': 'PAYMENT', 'pattern': [{'LOWER': {'IN': ['payment', 'price', 'fee']}}, {'LOWER': {'IN': ['terms', 'schedule', 'structure']}}]},
                {'label': 'PAYMENT', 'pattern': [{'SYMBOL': {'IN': ['$', '€', '£']}}, {'LIKE_NUM': True}]},
                
                # Timeline patterns
                {'label': 'TIMELINE', 'pattern': [{'LOWER': {'IN': ['delivery', 'completion', 'milestone']}}, {'LOWER': {'IN': ['date', 'schedule', 'timeline']}}]},
                {'label': 'TIMELINE', 'pattern': [{'LIKE_NUM': True}, {'LOWER': {'IN': ['day', 'week', 'month']}}]},
            ],
            
            'partnership': [
                # Structure patterns
                {'label': 'STRUCTURE', 'pattern': [{'LOWER': {'IN': ['partnership', 'joint', 'venture']}}, {'LOWER': {'IN': ['structure', 'type', 'form']}}]},
                {'label': 'STRUCTURE', 'pattern': [{'LOWER': {'IN': ['general', 'limited']}}, {'LOWER': 'partnership'}]},
                
                # Contribution patterns
                {'label': 'CONTRIBUTION', 'pattern': [{'LOWER': {'IN': ['capital', 'initial']}}, {'LOWER': 'contribution'}]},
                {'label': 'CONTRIBUTION', 'pattern': [{'SYMBOL': {'IN': ['$', '€', '£']}}, {'LIKE_NUM': True}]},
                
                # Profit/Loss patterns
                {'label': 'PROFIT_LOSS', 'pattern': [{'LOWER': {'IN': ['profit', 'loss']}}, {'LOWER': {'IN': ['sharing', 'distribution', 'allocation']}}]},
                {'label': 'PROFIT_LOSS', 'pattern': [{'LIKE_NUM': True}, {'LOWER': '%'}, {'LOWER': {'IN': ['share', 'interest', 'stake']}}]},
            ]
        }

        # Add entity patterns to spaCy pipeline
        if 'entity_ruler' not in self.nlp.pipe_names:
            ruler = self.nlp.add_pipe('entity_ruler', before='ner')
            patterns = []
            for domain_patterns in self.entity_patterns.values():
                for pattern in domain_patterns:
                    # Skip patterns with LIKE_NUM
                    if isinstance(pattern['pattern'], list) and any('LIKE_NUM' in token for token in pattern['pattern']):
                        continue
                    patterns.append(pattern)
            ruler.add_patterns(patterns)

        # Define critical clause patterns with enhanced categorization and importance levels
        self.critical_clause_patterns = {
            'payment': {
                'patterns': [
                    # Core payment terms
                    r'payment\s+(?:terms?|schedule|amount|method)',
                    r'compensation\s+(?:terms?|schedule|amount|structure)',
                    r'fees?\s+(?:and|&)\s+charges?',
                    r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?',
                    # Payment schedule
                    r'(?:monthly|annual|quarterly|weekly)\s+payments?',
                    r'installment\s+(?:plan|schedule|payment)',
                    # Late payment terms
                    r'late\s+(?:payment|fee|charge)',
                    r'interest\s+(?:rate|charge)',
                    # Payment conditions
                    r'payment\s+(?:condition|prerequisite|requirement)',
                    r'(?:invoice|billing)\s+(?:terms?|procedure|process)'
                ],
                'importance': 'High',
                'category': 'Financial',
                'risk_level': 'High',
                'validation_required': True
            },
            
            'termination': {
                'patterns': [
                    # Core termination terms
                    r'termination\s+(?:clause|provision|terms?|rights?)',
                    r'right\s+to\s+terminate',
                    r'grounds?\s+for\s+termination',
                    # Notice periods
                    r'notice\s+(?:period|requirement)',
                    r'(?:written|advance)\s+notice',
                    # Termination conditions
                    r'termination\s+(?:with|without)\s+cause',
                    r'immediate\s+termination',
                    # Post-termination obligations
                    r'post.?termination\s+(?:obligations?|duties?|requirements?)',
                    r'(?:effect|consequence)\s+of\s+termination',
                    # Survival clauses
                    r'survival?\s+(?:clause|provision|terms?)',
                    r'survive\s+termination'
                ],
                'importance': 'High',
                'category': 'Legal',
                'risk_level': 'High',
                'validation_required': True
            },
            
            'liability': {
                'patterns': [
                    # Core liability terms
                    r'liability\s+(?:clause|provision|terms?|limitation)',
                    r'limitation\s+of\s+liability',
                    r'limited\s+liability',
                    # Indemnification
                    r'indemnification?\s+(?:clause|provision|terms?)',
                    r'indemnify\s+(?:and|&)\s+hold\s+harmless',
                    r'defend,?\s+indemnify',
                    # Exclusions and limitations
                    r'exclusion\s+of\s+(?:liability|damages)',
                    r'liability\s+(?:cap|limit|threshold)',
                    # Specific damages
                    r'(?:direct|indirect|consequential|special|punitive)\s+damages?',
                    r'loss\s+(?:of|&)\s+(?:profit|revenue|business|data)',
                    # Insurance requirements
                    r'insurance\s+(?:requirement|coverage|policy)',
                    r'minimum\s+insurance'
                ],
                'importance': 'High',
                'category': 'Legal',
                'risk_level': 'High',
                'validation_required': True
            },
            
            'confidentiality': {
                'patterns': [
                    # Core confidentiality terms
                    r'confidentiality\s+(?:clause|provision|terms?|obligations?)',
                    r'non.?disclosure',
                    r'confidential\s+information',
                    # Information types
                    r'proprietary\s+(?:information|data|material)',
                    r'trade\s+secrets?',
                    r'sensitive\s+(?:information|data)',
                    # Usage restrictions
                    r'use\s+(?:restriction|limitation)',
                    r'permitted\s+(?:use|purpose)',
                    # Protection measures
                    r'protection\s+(?:measures?|standards?)',
                    r'security\s+(?:measures?|requirements?)',
                    # Duration and survival
                    r'confidentiality\s+(?:period|duration|term)',
                    r'survive\s+termination'
                ],
                'importance': 'High',
                'category': 'Legal',
                'risk_level': 'High',
                'validation_required': True
            },
            
            'intellectual_property': {
                'patterns': [
                    # Core IP terms
                    r'intellectual\s+property\s+(?:rights?|ownership)',
                    r'(?:patent|copyright|trademark)',
                    r'(?:IP|IPR)\s+(?:rights?|ownership)',
                    # Ownership and rights
                    r'ownership\s+(?:of|&)\s+(?:IP|rights?|materials?)',
                    r'rights?\s+(?:assignment|transfer)',
                    # License terms
                    r'license\s+(?:grant|terms?|rights?)',
                    r'right\s+to\s+use',
                    # Restrictions
                    r'use\s+(?:restriction|limitation)',
                    r'prohibited\s+(?:use|activity)',
                    # Protection
                    r'IP\s+protection',
                    r'infringement\s+(?:clause|protection)'
                ],
                'importance': 'High',
                'category': 'Legal',
                'risk_level': 'High',
                'validation_required': True
            },
            
            'dispute_resolution': {
                'patterns': [
                    # Core dispute terms
                    r'dispute\s+(?:resolution|settlement)',
                    r'conflict\s+resolution',
                    r'(?:resolution|settlement)\s+procedure',
                    # Mediation and arbitration
                    r'(?:mediation|arbitration)\s+(?:clause|provision|procedure)',
                    r'alternative\s+dispute\s+resolution',
                    r'ADR\s+(?:clause|provision)',
                    # Jurisdiction
                    r'governing\s+(?:law|jurisdiction)',
                    r'choice\s+of\s+(?:law|forum)',
                    # Procedures
                    r'(?:legal|court)\s+proceedings?',
                    r'(?:venue|forum)\s+selection',
                    # Costs
                    r'(?:legal|attorney)\s+fees?',
                    r'costs?\s+of\s+(?:proceedings?|arbitration)'
                ],
                'importance': 'High',
                'category': 'Legal',
                'risk_level': 'High',
                'validation_required': True
            },
            
            'force_majeure': {
                'patterns': [
                    # Core force majeure terms
                    r'force\s+majeure',
                    r'act\s+of\s+god',
                    # Events and circumstances
                    r'(?:natural|unavoidable)\s+(?:disaster|catastrophe|event)',
                    r'(?:war|terrorism|pandemic|epidemic)',
                    # Effects and procedures
                    r'(?:suspension|interruption)\s+of\s+(?:service|performance)',
                    r'(?:delay|prevention)\s+of\s+performance',  # Fixed the pattern here
                    # Notice requirements
                    r'force\s+majeure\s+notice',
                    r'notification\s+of\s+force\s+majeure'
                ],
                'importance': 'High',
                'category': 'Legal',
                'risk_level': 'High',
                'validation_required': True
            }
        }

        # Update section patterns to match the actual document structure
        self.section_patterns = {
            'main_section': r'(?:^|\n)(\d+)\.\s*([^●\d]+?)(?=\s*●|\s*\d+\.|$)',  # Matches main sections with proper boundaries
            'sub_section': r'●\s*([^:]+):\s*([^●\n][^●]*?)(?=\s*●|$)',  # Matches bullet points with content
        }

        # Initialize obligation patterns for consistent use across methods
        self.obligation_patterns = [
            r'shall\s+\w+',
            r'must\s+\w+',
            r'will\s+\w+',
            r'is\s+(?:required|obligated|duty-bound)\s+to\s+\w+',
            r'has\s+(?:a\s+)?duty\s+to\s+\w+',
            r'agrees\s+to\s+\w+',
            r'undertakes\s+to\s+\w+',
            r'commits\s+to\s+\w+',
            r'is\s+bound\s+to\s+\w+',
            r'is\s+responsible\s+for\s+\w+',
            r'is\s+obliged\s+to\s+\w+',
            r'guarantees\s+to\s+\w+',
            r'warrants\s+(?:to|that)\s+\w+',
            r'represents\s+(?:to|that)\s+\w+',
            r'covenants\s+to\s+\w+',
            r'pledges\s+to\s+\w+'
        ]

    def safe_extract_clauses(self, text: str) -> List[Dict]:
        """Safe wrapper for extract_clauses with error handling."""
        try:
            return self.extract_clauses(text) or []
        except Exception as e:
            print(f"\nError in safe_extract_clauses: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            print(f"Traceback: {traceback.format_exc()}")
            return []

    def safe_parse_json(self, content: str) -> Optional[List[Dict]]:
        """Safely parse JSON with multiple fallback attempts."""
        try:
            # First attempt: direct JSON parsing
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                # Second attempt: clean up common issues
                cleaned = content.strip()
                cleaned = cleaned.replace('\n', '\\n')
                cleaned = cleaned.replace('\\n\\n', '\\n')
                cleaned = cleaned.replace('""', '"')
                cleaned = re.sub(r'(?<!\\)"(?!,|\s*}|\s*])', '\\"', cleaned)
                return json.loads(cleaned)
            except json.JSONDecodeError:
                try:
                    # Third attempt: handle markdown blocks
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1]
                    content = content.strip()
                    return json.loads(content)
                except json.JSONDecodeError:
                    return None

    def normalize_legal_terms(self, text: str) -> str:
        """Normalize legal terms in text for better matching"""
        try:
            normalized = text.lower()
            
            # Replace common variations
            replacements = {
                'shall not': ['must not', 'will not', 'is not permitted to', 'may not', 'cannot'],
                'shall': ['must', 'will', 'is required to', 'is obligated to', 'agrees to'],
                'terminate': ['end', 'cancel', 'discontinue', 'cease'],
                'immediately': ['forthwith', 'without delay', 'at once', 'promptly'],
                'including': ['including but not limited to', 'including without limitation'],
                'represents': ['warrants', 'certifies', 'confirms', 'declares'],
                'indemnify': ['hold harmless', 'protect against loss', 'compensate for loss']
            }
            
            for term, variants in replacements.items():
                for variant in variants:
                    normalized = normalized.replace(variant, term)
            
            return normalized
            
        except Exception as e:
            logging.error(f"Error normalizing text: {str(e)}")
            return text

    def detect_domain_with_ner(self, text: str) -> Tuple[str, float]:
        """Detect contract domain using NER and keyword analysis."""
        doc = self.nlp(text)
        
        # Count domain-specific entities and keywords
        domain_scores = {domain: 0.0 for domain in self.domain_keywords.keys()}
        
        # NER scoring
        for ent in doc.ents:
            for domain, patterns in self.entity_patterns.items():
                if any(pattern['label'] == ent.label_ for pattern in patterns):
                    domain_scores[domain] += 1.0

        # Keyword scoring
        for domain, keywords in self.domain_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    domain_scores[domain] += 0.5

        # Normalize scores
        total_score = sum(domain_scores.values())
        if total_score > 0:
            domain_scores = {k: v/total_score for k, v in domain_scores.items()}
        
        # Get domain with highest score
        detected_domain = max(domain_scores.items(), key=lambda x: x[1])
        return detected_domain[0], detected_domain[1]

    def get_domain_specific_prompt(self, domain: str, text: str) -> str:
        """
        Get domain-specific prompt for clause extraction.
        """
        base_prompt = f"""Analyze the following service agreement and extract ALL clauses, including numbered sections.
Pay special attention to the document structure and ensure ALL numbered sections are captured.

For each clause, provide:
1. The text field MUST be in the format "Title: Content" where:
   - Title is the exact section title from the document (e.g., "Scope of Services", "Term and Termination")
   - Content is the complete text under that section
2. Category (Legal, Financial, Operational)
3. Importance (High, Medium, Low)

Important Instructions:
- Extract ALL numbered sections from 1 to the last number
- Include the complete text for each section
- Maintain the exact titles as they appear in the document
- Do not skip any sections, even if they seem less important

Example clause format:
{{
    "text": "Scope of Services: The Service Provider shall deliver software development and testing services to the Client...",
    "category": "Operational",
    "importance": "High"
}}
"""
        
        domain_specific_instructions = {
            'service': """Pay special attention to:
- Scope of services and deliverables
- Payment terms and conditions
- Service level requirements
- Term and termination conditions
- Liability and indemnification""",
            'nda': """Pay special attention to:
- Definition of confidential information
- Permitted use and disclosure
- Duration of confidentiality
- Return of confidential materials
- Breach and remedies""",
            'employment': """Pay special attention to:
- Compensation and benefits terms
- Work hours and conditions
- Termination clauses
- Non-compete and confidentiality
- Employee obligations and responsibilities""",
            'lease': """Pay special attention to:
- Rent and payment terms
- Property description and use
- Maintenance responsibilities
- Term and renewal conditions
- Security deposit terms""",
            'sla': """Pay special attention to:
- Service level definitions
- Performance metrics
- Response time commitments
- Maintenance windows
- Penalty and credit terms""",
            'vendor': """Pay special attention to:
- Scope of services/goods
- Pricing and payment terms
- Delivery conditions
- Quality standards
- Warranty terms""",
            'partnership': """Pay special attention to:
- Profit sharing arrangements
- Decision making authority
- Resource contributions
- Exit provisions
- Intellectual property rights""",
            'general': """Pay special attention to:
- Key obligations of all parties
- Payment and financial terms
- Term and termination
- Liability and indemnification
- Governing law"""
        }

        # Combine all parts of the prompt with proper text inclusion
        full_prompt = f"""{base_prompt}

{domain_specific_instructions.get(domain, domain_specific_instructions.get('service', ''))}

Here is the contract text to analyze:
{text}

Return the results in this format:
[
    {{
        "text": "Title: Full content with all details",
        "category": "category",
        "importance": "importance"
    }}
]

Make sure to extract ALL numbered sections from the document."""

        return full_prompt

    def get_clause_text(self, clause: Dict) -> str:
        """Helper function to get clause text, handling both 'text' and 'clause' fields."""
        if not clause:
            return ""
        return clause.get("text", clause.get("clause", ""))

    def extract_clauses(self, text: str) -> List[Dict]:
        try:
            print("\n=== Starting Clause Extraction ===")
            print(f"Input text length: {len(text)}")
            
            # Print text structure for debugging
            print("\nDocument Structure Sample:")
            lines = text.split('\n')
            for i, line in enumerate(lines[:5]):
                print(f"Line {i+1}: {line}")
            
            # Detect domain using NER (needed for processing)
            domain, confidence = self.detect_domain_with_ner(text)
            print(f"\nDetected Domain: {domain} (confidence: {confidence:.2f})")
            
            # Pre-process text to ensure proper section breaks
            text = re.sub(r'(\d+\.)', r'\n\1', text)  # Ensure section numbers start on new lines
            
            validated_clauses = []
            
            # First pass: Find main sections
            main_sections = list(re.finditer(self.section_patterns['main_section'], text))
            
            print(f"\nFound {len(main_sections)} main sections")
            
            # Process each main section
            for i, main_match in enumerate(main_sections):
                section_number = main_match.group(1)
                section_title = main_match.group(2).strip()
                
                # Get section content (up to next main section or end)
                start_pos = main_match.end()
                end_pos = main_sections[i + 1].start() if i + 1 < len(main_sections) else len(text)
                section_content = text[start_pos:end_pos].strip()
                
                print(f"\nProcessing main section {section_number}: {section_title}")
                print(f"Content length: {len(section_content)}")
                
                # Process main section
                main_clause = self._process_clause(
                    section_number,
                    section_title,
                    section_content,
                    domain,
                    confidence
                )
                
                if main_clause:
                    main_clause['sub_clauses'] = []
                    validated_clauses.append(main_clause)
                    
                    # Find sub-sections within this main section
                    sub_matches = re.finditer(self.section_patterns['sub_section'], section_content)
                    sub_clauses = []
                    
                    for sub_match in sub_matches:
                        sub_title = sub_match.group(1).strip()
                        sub_content = sub_match.group(2).strip()
                        
                        print(f"\nProcessing sub-section: {sub_title}")
                        print(f"Content length: {len(sub_content)}")
                        
                        sub_clause = self._process_clause(
                            f"{section_number}.{len(sub_clauses)+1}",
                            sub_title,
                            sub_content,
                            domain,
                            confidence
                        )
                        
                        if sub_clause:
                            sub_clauses.append(sub_clause)
                    
                    main_clause['sub_clauses'] = sub_clauses
            
            print(f"\nTotal main sections extracted: {len(validated_clauses)}")
            return validated_clauses

        except Exception as e:
            print(f"\nError in extract_clauses: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return []

    def _process_clause(self, number: str, title: str, content: str, domain: str, confidence: float) -> Optional[Dict]:
        """Process a single clause and return structured data."""
        try:
            print(f"\n=== Processing Clause {number} ===")
            print(f"Title: {title}")
            print(f"Content preview: {content[:100]}...")
            
            # Basic validation
            if not content.strip():
                print("Warning: Empty content, skipping clause")
                return None
            
            # Process with spaCy for entity extraction
            doc = self.nlp(content)
            entities = [{'text': ent.text, 'label': ent.label_} for ent in doc.ents]
            print(f"Found {len(entities)} entities")
            
            # Determine clause characteristics
            is_critical, clause_type, importance = self.is_critical_clause(content)
            print(f"Clause analysis: Critical={is_critical}, Type={clause_type}, Importance={importance}")
            
            category = self.determine_clause_category(content, domain) or "General"
            print(f"Determined category: {category}")
            
            # Validate critical clauses
            validation_status = None
            if is_critical:
                validation_status = self.validate_critical_clause(content)
                print(f"Critical clause validation: {validation_status}")
            
            clause_data = {
                'number': number,
                'title': title,
                'text': content,
                'category': category,
                'importance': importance or "Medium",
                'domain': domain,
                'confidence': confidence,
                'entities': entities,
                'is_critical': is_critical,
                'clause_type': clause_type,
                'validation_status': validation_status
            }
            
            print("Successfully processed clause")
            return clause_data
            
        except Exception as e:
            print(f"Error processing clause: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return None

    def _extract_with_llm(self, text: str, domain: str, confidence: float) -> List[Dict]:
        """Extract clauses using LLM when pattern matching fails."""
        try:
            domain_prompt = self.get_domain_specific_prompt(domain, text)
            response = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": """Extract clauses with exact titles and content. Return in JSON format:
                        [
                            {
                                "number": "1",
                                "title": "Exact section title",
                                "text": "Complete section content",
                                "category": "Legal/Financial/Operational",
                                "importance": "High/Medium/Low"
                            }
                        ]"""
                    },
                    {"role": "user", "content": domain_prompt}
                ],
                model="gemma-7b-it",
                temperature=0.1,
            )
            
            content = response.choices[0].message.content
            clauses = self.safe_parse_json(content)
            
            if not clauses:
                return []
            
            validated_clauses = []
            for clause in clauses:
                if isinstance(clause, dict) and 'text' in clause:
                    processed_clause = self._process_clause(
                        clause.get('number', str(len(validated_clauses) + 1)),
                        clause.get('title', ''),
                        clause['text'],
                        domain,
                        confidence * 0.8  # Lower confidence for LLM extraction
                    )
                    if processed_clause:
                        validated_clauses.append(processed_clause)
            
            return validated_clauses
            
        except Exception as e:
            print(f"Error in LLM extraction: {str(e)}")
            return []

    def determine_clause_category(self, text: str, domain: str) -> Optional[str]:
        """Determine clause category based on content and domain context."""
        text_lower = text.lower()
        
        # Financial indicators
        if any(term in text_lower for term in ['payment', 'cost', 'fee', 'price', 'compensation', 'amount', '$']):
            return 'Financial'
        
        # Legal indicators
        if any(term in text_lower for term in ['law', 'jurisdiction', 'liability', 'indemnity', 'warrant', 'rights', 'obligation']):
            return 'Legal'
        
        # Operational indicators
        if any(term in text_lower for term in ['process', 'procedure', 'delivery', 'service', 'maintenance', 'support']):
            return 'Operational'
        
        return None

    def determine_clause_importance(self, text: str, domain: str) -> Optional[str]:
        """Determine clause importance based on content and domain context."""
        text_lower = text.lower()
        
        # High importance indicators
        high_importance_terms = [
            'terminate', 'breach', 'liability', 'indemnity', 'confidential',
            'payment', 'intellectual property', 'warranty', 'material'
        ]
        if any(term in text_lower for term in high_importance_terms):
            return 'High'
        
        # Low importance indicators
        low_importance_terms = [
            'notice', 'administrative', 'formatting', 'heading'
        ]
        if any(term in text_lower for term in low_importance_terms):
            return 'Low'
        
        return None

    def calculate_similarity_score(self, text1: str, text2: str) -> float:
        """Calculate similarity score between legal texts with specialized legal term weighting"""
        try:
            # Log input texts for debugging
            logging.info(f"Calculating similarity between texts:")
            logging.info(f"Text 1 (first 100 chars): {text1[:100]}")
            logging.info(f"Text 2 (first 100 chars): {text2[:100]}")
            
            # Clean and normalize texts
            text1 = ' '.join(text1.split())
            text2 = ' '.join(text2.split())
            
            # 1. Legal Term Weight (40% of total score)
            logging.info("Calculating legal term similarity...")
            legal_term_score = self._calculate_legal_term_similarity(text1, text2)
            logging.info(f"Legal term score: {legal_term_score}")
            
            # 2. Obligation Pattern Weight (25% of total score)
            logging.info("Calculating obligation similarity...")
            obligation_score = self._calculate_obligation_similarity(text1, text2)
            logging.info(f"Obligation score: {obligation_score}")
            
            # 3. Numeric Value Weight (20% of total score)
            logging.info("Calculating numeric similarity...")
            numeric_score = self._calculate_numeric_similarity(text1, text2)
            logging.info(f"Numeric score: {numeric_score}")
            
            # 4. General Semantic Weight (15% of total score)
            logging.info("Calculating semantic similarity...")
            embedding1 = self.similarity_model.encode([text1])[0]
            embedding2 = self.similarity_model.encode([text2])[0]
            semantic_score = float(cosine_similarity([embedding1], [embedding2])[0][0]) * 100
            logging.info(f"Semantic score: {semantic_score}")
            
            # Calculate weighted final score
            final_score = (
                (legal_term_score * 0.40) +
                (obligation_score * 0.25) +
                (numeric_score * 0.20) +
                (semantic_score * 0.15)
            )
            
            logging.info(f"Final weighted score: {final_score}")
            
            return round(min(max(final_score, 0), 100), 2)
            
        except Exception as e:
            logging.error(f"Error calculating similarity: {str(e)}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            return 0.0

    def _calculate_legal_term_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity based on legal terms and their context"""
        try:
            # Log input texts
            logging.info("Calculating legal term similarity for texts:")
            logging.info(f"Text 1 (first 100 chars): {text1[:100]}")
            logging.info(f"Text 2 (first 100 chars): {text2[:100]}")
            
            # Normalize both texts
            text1 = self.normalize_legal_terms(text1.lower())
            text2 = self.normalize_legal_terms(text2.lower())
            
            # Extract legal terms and their context
            legal_terms1 = set()
            legal_terms2 = set()
            
            # Check for critical legal phrases and their context
            for term, variants in self.legal_term_normalizations.items():
                # Check original term
                if term in text1:
                    context = self._get_term_context(text1, term)
                    legal_terms1.add((term, context))
                    logging.info(f"Found legal term in text1: {term} with context: {context}")
                if term in text2:
                    context = self._get_term_context(text2, term)
                    legal_terms2.add((term, context))
                    logging.info(f"Found legal term in text2: {term} with context: {context}")
                
                # Check variants
                for variant in variants:
                    if variant in text1:
                        context = self._get_term_context(text1, variant)
                        legal_terms1.add((term, context))
                        logging.info(f"Found variant in text1: {variant} -> {term} with context: {context}")
                    if variant in text2:
                        context = self._get_term_context(text2, variant)
                        legal_terms2.add((term, context))
                        logging.info(f"Found variant in text2: {variant} -> {term} with context: {context}")
            
            logging.info(f"Found {len(legal_terms1)} legal terms in text1")
            logging.info(f"Found {len(legal_terms2)} legal terms in text2")
            
            # Calculate similarity considering both terms and their context
            if not legal_terms1 and not legal_terms2:
                logging.info("No legal terms found in either text")
                return 100.0  # Both texts have no legal terms
            
            matches = 0
            total_terms = max(len(legal_terms1), len(legal_terms2))
            
            for term1, context1 in legal_terms1:
                for term2, context2 in legal_terms2:
                    if term1 == term2:
                        context_similarity = self._calculate_context_similarity(context1, context2)
                        logging.info(f"Comparing contexts for term {term1}:")
                        logging.info(f"Context1: {context1}")
                        logging.info(f"Context2: {context2}")
                        logging.info(f"Context similarity: {context_similarity}")
                        if context_similarity > 0.5:  # More lenient threshold for real-world variations
                            matches += context_similarity
                            logging.info(f"Match found with similarity: {context_similarity}")
            
            final_score = (matches / total_terms) * 100 if total_terms > 0 else 0.0
            logging.info(f"Final legal term similarity score: {final_score}")
            return final_score
            
        except Exception as e:
            logging.error(f"Error in legal term similarity: {str(e)}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            return 0.0

    def _calculate_obligation_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity based on obligation patterns"""
        try:
            logging.info("Calculating obligation similarity for texts:")
            logging.info(f"Text 1 (first 100 chars): {text1[:100]}")
            logging.info(f"Text 2 (first 100 chars): {text2[:100]}")
            
            # Extract obligations
            obligations1 = set()
            obligations2 = set()
            
            for pattern in self.obligation_patterns:
                matches1 = re.finditer(pattern, text1.lower())
                matches2 = re.finditer(pattern, text2.lower())
                
                for match in matches1:
                    obligations1.add(match.group())
                    logging.info(f"Found obligation in text1: {match.group()}")
                for match in matches2:
                    obligations2.add(match.group())
                    logging.info(f"Found obligation in text2: {match.group()}")
            
            logging.info(f"Found {len(obligations1)} obligations in text1")
            logging.info(f"Found {len(obligations2)} obligations in text2")
            
            if not obligations1 and not obligations2:
                logging.info("No obligations found in either text")
                return 100.0  # Both texts have no obligations
            
            total_obligations = max(len(obligations1), len(obligations2))
            
            logging.info(f"Matching obligations: {len(obligations1.intersection(obligations2))}")
            logging.info(f"Total obligations: {total_obligations}")
            
            final_score = (len(obligations1.intersection(obligations2)) / total_obligations) * 100 if total_obligations > 0 else 0.0
            logging.info(f"Final obligation similarity score: {final_score}")
            return final_score
            
        except Exception as e:
            logging.error(f"Error in obligation similarity: {str(e)}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            return 0.0

    def _calculate_numeric_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity based on numeric values"""
        try:
            logging.info("Calculating numeric similarity for texts:")
            logging.info(f"Text 1 (first 100 chars): {text1[:100]}")
            logging.info(f"Text 2 (first 100 chars): {text2[:100]}")
            
            # Extract numeric patterns
            patterns = {
                'amount': r'\$\s*[\d,]+(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD)',
                'percentage': r'\d+(?:\.\d+)?\s*%',
                'quantity': r'\b\d+(?:,\d{3})*\b(?!\s*%|\s*(?:dollars?|USD))',
                'date': r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'
            }
            
            matches1 = []
            matches2 = []
            
            # Extract all numeric values with their types
            for value_type, pattern in patterns.items():
                for match in re.finditer(pattern, text1, re.IGNORECASE):
                    matches1.append((value_type, match.group()))
                    logging.info(f"Found numeric value in text1: {value_type} - {match.group()}")
                for match in re.finditer(pattern, text2, re.IGNORECASE):
                    matches2.append((value_type, match.group()))
                    logging.info(f"Found numeric value in text2: {value_type} - {match.group()}")
            
            logging.info(f"Found {len(matches1)} numeric values in text1")
            logging.info(f"Found {len(matches2)} numeric values in text2")
            
            if not matches1 and not matches2:
                logging.info("No numeric values found in either text")
                return 100.0  # Both texts have no numeric values
                
            if not matches1 or not matches2:
                logging.info("Numeric values found in only one text")
                return 0.0  # One text has numeric values while other doesn't
            
            # Compare numeric values with type-specific weights
            weights = {
                'amount': 0.4,
                'percentage': 0.3,
                'quantity': 0.2,
                'date': 0.1
            }
            
            total_score = 0.0
            total_weight = 0.0
            
            for type1, value1 in matches1:
                best_match_score = 0.0
                for type2, value2 in matches2:
                    if type1 == type2:
                        logging.info(f"Comparing {type1} values: {value1} vs {value2}")
                        if type1 == 'date':
                            # For dates, check exact match
                            if value1 == value2:
                                best_match_score = 1.0
                                logging.info("Exact date match found")
                            else:
                                relative_diff = abs(float(value1.replace(',', '')) - float(value2.replace(',', ''))) / max(float(value1.replace(',', '')), float(value2.replace(',', '')))
                                best_match_score = max(best_match_score, 1.0 - relative_diff)
                                logging.info(f"Relative difference: {relative_diff}, match score: {best_match_score}")
                    else:
                        # For numeric values, calculate similarity based on relative difference
                        num1 = float(''.join(filter(str.isdigit, value1.replace(',', ''))))
                        num2 = float(''.join(filter(str.isdigit, value2.replace(',', ''))))
                        if num1 == num2:
                                best_match_score = 1.0
                                logging.info("Exact numeric match found")
                        else:
                            relative_diff = abs(num1 - num2) / max(num1, num2)
                            best_match_score = max(best_match_score, 1.0 - relative_diff)
                            logging.info(f"Relative difference: {relative_diff}, match score: {best_match_score}")
                
                total_score += best_match_score * weights[type1]
                total_weight += weights[type1]
            
            final_score = (total_score / total_weight * 100) if total_weight > 0 else 100.0
            logging.info(f"Final numeric similarity score: {final_score}")
            return final_score
            
        except Exception as e:
            logging.error(f"Error in numeric similarity: {str(e)}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            return 0.0

    def _get_term_context(self, text: str, term: str, context_words: int = 5) -> str:
        """Get surrounding context for a legal term"""
        try:
            words = text.split()
            start = 0  # Initialize start with default value
            end = 0    # Initialize end with default value
            
            for i, word in enumerate(words):
                if term in word:
                    start = max(0, i - context_words)
                    end = min(len(words), i + context_words + 1)
            return ' '.join(words[start:end])  # Use initialized values if term not found
        except Exception as e:
            logging.error(f"Error getting term context: {str(e)}")
            return ""

    def _calculate_context_similarity(self, context1: str, context2: str) -> float:
        """Calculate similarity between two context strings"""
        try:
            if not context1 or not context2:
                return 0.0
            
            # Normalize text
            words1 = set(word.lower() for word in context1.split())
            words2 = set(word.lower() for word in context2.split())
            
            # Calculate Jaccard similarity with more lenient threshold
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            # Add partial word matching for better real-world matching
            if union > 0:
                base_score = intersection / union
                
                # Check for partial word matches
                remaining1 = words1 - words2
                remaining2 = words2 - words1
                partial_matches = 0
                
                for w1 in remaining1:
                    for w2 in remaining2:
                        if (w1 in w2 or w2 in w1) and len(min(w1, w2, key=len)) > 3:
                            partial_matches += 0.5
                
                return min(1.0, base_score + (partial_matches / union))
            
            return 0.0
            
        except Exception as e:
            logging.error(f"Error calculating context similarity: {str(e)}")
            return 0.0

    def _extract_numeric_values(self, text: str) -> List[Dict]:
        """Extract numeric values with their type and context"""
        numeric_values = []
        
        try:
            # Check each numeric pattern
            for value_type, pattern in self.numeric_patterns.items():
                matches = pattern.finditer(text)
                for match in matches:
                    value = match.group()
                    numeric_values.append({
                        'type': value_type,
                        'value': value,
                        'context': self._get_term_context(text, value)
                    })
            
            return numeric_values
            
        except Exception as e:
            logging.error(f"Error extracting numeric values: {str(e)}")
            return []

    def _is_similar_value(self, value1: str, value2: str, value_type: str) -> bool:
        """Check if two numeric values are similar based on their type"""
        try:
            # Extract digits, handling empty strings
            digits1 = ''.join(filter(str.isdigit, value1.replace(',', '')))
            digits2 = ''.join(filter(str.isdigit, value2.replace(',', '')))
            
            # If either string has no digits, they can't be similar
            if not digits1 or not digits2:
                return False
                
            # Convert to float now that we know we have digits
            num1 = float(digits1)
            num2 = float(digits2)
            
            if value_type == 'money':
                # Allow 1% difference for monetary values
                return abs(num1 - num2) / max(num1, num2) <= 0.01
            elif value_type == 'percentage':
                # Allow 0.5% difference for percentages
                return abs(num1 - num2) <= 0.5
            elif value_type == 'duration':
                # Allow no difference for durations
                return num1 == num2
            else:
                return num1 == num2
                
        except Exception as e:
            logging.error(f"Error comparing numeric values: {str(e)}")
            return False

    def compare_texts(self, text1: str, text2: str) -> Dict:
        """Compare two texts and return detailed similarity analysis"""
        try:
            # Calculate component scores first
            legal_term_score = self._calculate_legal_term_similarity(text1, text2)
            obligation_score = self._calculate_obligation_similarity(text1, text2)
            numeric_score = self._calculate_numeric_similarity(text1, text2)
            
            # Calculate semantic score
            embedding1 = self.similarity_model.encode([text1])[0]
            embedding2 = self.similarity_model.encode([text2])[0]
            semantic_score = float(cosine_similarity([embedding1], [embedding2])[0][0]) * 100
            
            # Calculate weighted final score
            similarity_score = (
                (legal_term_score * 0.40) +
                (obligation_score * 0.25) +
                (numeric_score * 0.20) +
                (semantic_score * 0.15)
            )
            
            # Get differences
            try:
                differences = {
                    'legal_terms': self._get_legal_term_differences(text1, text2),
                    'numeric_values': self._get_numeric_differences(text1, text2),
                    'obligations': self._get_obligation_differences(text1, text2),
                    'critical_changes': []
                }
            except Exception as e:
                logging.error(f"Error getting differences: {str(e)}")
                differences = {
                    'legal_terms': {},
                    'numeric_values': [],
                    'obligations': [],
                    'critical_changes': []
                }
            
            # Structure the result
            result = {
                'similarity_score': round(similarity_score, 2),
                'component_scores': {
                    'legal_term_score': round(legal_term_score, 2),
                    'numeric_score': round(numeric_score, 2),
                    'obligation_score': round(obligation_score, 2),
                    'semantic_score': round(semantic_score, 2)
                },
                'differences': differences
            }
            
            return result
            
        except Exception as e:
            logging.error(f"Error in compare_texts: {str(e)}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            
            # Even if there's an error, try to return any scores we calculated
            return {
                'similarity_score': round(locals().get('similarity_score', 0.0), 2),
                'component_scores': {
                    'legal_term_score': round(locals().get('legal_term_score', 0.0), 2),
                    'numeric_score': round(locals().get('numeric_score', 0.0), 2),
                    'obligation_score': round(locals().get('obligation_score', 0.0), 2),
                    'semantic_score': round(locals().get('semantic_score', 0.0), 2)
                },
                'differences': locals().get('differences', {
                    'legal_terms': {},
                    'numeric_values': [],
                    'obligations': [],
                    'critical_changes': []
                })
            }

    def _determine_match_category(self, similarity_score: float, critical_issues: int) -> str:
        """Determine the match category based on similarity score and critical issues"""
        if similarity_score >= 95 and critical_issues == 0:
            return 'EXACT MATCH'
        elif similarity_score >= 80:
            return 'CLOSE MATCH'
        elif similarity_score >= 60:
            return 'PARTIAL MATCH'
        elif similarity_score >= 40:
            return 'LOW MATCH'
        else:
            return 'NO MATCH'

    def _analyze_differences(self, text1: str, text2: str) -> Dict:
        """Analyze differences between two texts"""
        try:
            # Initialize default structure
            default_differences = {
                'legal_terms': {
                    'added': [],
                    'removed': [],
                    'modified': []
                },
                'numeric_values': [],
                'obligations': [],
                'critical_changes': {
                    'missing': [],
                    'modified': [],
                    'matched': []
                }
            }

            # If either text is empty, return default structure
            if not text1 or not text2:
                return default_differences

            # Minimal cleaning while preserving structure
            text1 = self.clean_text(text1)
            text2 = self.clean_text(text2)
            
            # Legal Term Analysis
            legal_terms1 = self._extract_legal_terms_with_context(text1)
            legal_terms2 = self._extract_legal_terms_with_context(text2)
            legal_term_differences = self._analyze_legal_term_differences(legal_terms1, legal_terms2)
            
            # Ensure legal_terms has all required keys
            if 'legal_terms' not in legal_term_differences:
                legal_term_differences = default_differences['legal_terms']
            else:
                for key in ['added', 'removed', 'modified']:
                    if key not in legal_term_differences:
                        legal_term_differences[key] = []
            
            # Numeric Analysis
            numeric_values1 = self._extract_numeric_values(text1)
            numeric_values2 = self._extract_numeric_values(text2)
            numeric_changes = self._compare_numeric_values(numeric_values1, numeric_values2)
            
            # Obligation Analysis
            obligations1 = self._extract_obligations(text1)
            obligations2 = self._extract_obligations(text2)
            obligation_changes = self._analyze_obligation_changes(obligations1, obligations2)
            
            # Critical Changes Analysis
            critical_changes = self._identify_critical_changes(text1, text2)
            
            return {
                'legal_terms': legal_term_differences,
                'numeric_values': numeric_changes or [],
                'obligations': obligation_changes or [],
                'critical_changes': critical_changes or {
                    'missing': [],
                    'modified': [],
                    'matched': []
                }
            }
        except Exception as e:
            logging.error(f"Error in _analyze_differences: {str(e)}")
            return default_differences

    def _extract_legal_terms_with_context(self, text: str) -> List[Dict]:
        """Extract legal terms with their surrounding context"""
        terms = []
        for term, variants in self.legal_term_normalizations.items():
            for match in re.finditer(r'\b' + re.escape(term) + r'\b', text.lower()):
                start = max(0, match.start() - 50)  # Add context before
                end = min(len(text), match.end() + 50)  # Add context after
                terms.append({
                    'term': term,
                    'context': text[start:end],
                    'position': match.start()
                })
        return terms

    def _compare_legal_terms(self, terms1: List[Dict], terms2: List[Dict]) -> float:
        """Compare legal terms considering their context"""
        if not terms1 and not terms2:
            return 100.0
        
        if not terms1 or not terms2:
            return 0.0
        
        matches = 0
        total_comparisons = len(terms1)
        
        for term1 in terms1:
            best_match_score = 0
            for term2 in terms2:
                if term1['term'] == term2['term']:
                    context_similarity = self._calculate_context_similarity(
                        term1['context'], 
                        term2['context']
                    )
                    best_match_score = max(best_match_score, context_similarity)
        
        
        if best_match_score > 0.5:  # More lenient threshold
            matches += best_match_score
        
        return (matches / total_comparisons * 100) if total_comparisons > 0 else 100.0

    def _analyze_legal_term_differences(self, terms1: List[Dict], terms2: List[Dict]) -> Dict:
        """Analyze differences in legal terms"""
        terms1_set = {(t['term'], t['context']) for t in terms1}
        terms2_set = {(t['term'], t['context']) for t in terms2}
        
        return {
            'added': list(terms2_set - terms1_set),
            'removed': list(terms1_set - terms2_set),
            'modified': self._find_modified_terms(terms1, terms2)
        }

    def _find_modified_terms(self, terms1: List[Dict], terms2: List[Dict]) -> List[Dict]:
        """Find terms that exist in both texts but with different context"""
        modified = []
        for term1 in terms1:
            for term2 in terms2:
                if (term1['term'] == term2['term'] and 
                    term1['context'] != term2['context']):
                    modified.append({
                        'term': term1['term'],
                        'original_context': term1['context'],
                        'new_context': term2['context']
                    })
        return modified

    def _assess_change_risk(self, differences: Dict) -> float:
        """Assess risk level based on changes found"""
        try:
            risk_points = 0
            
            # Ensure critical_changes is a dictionary
            critical_changes = differences.get('critical_changes', {})
            if isinstance(critical_changes, list):
                critical_changes = {
                    'missing': [x for x in critical_changes if x.get('type') == 'missing'],
                    'modified': [x for x in critical_changes if x.get('type') == 'modified'],
                    'matched': [x for x in critical_changes if x.get('type') == 'matched']
                }
            
            # Get differences with proper default values
            legal_terms = differences.get('legal_terms', {})
            numeric_values = differences.get('numeric_values', [])
            obligations = differences.get('obligations', [])
            
            # Log the analysis steps
            logging.info("Starting risk assessment...")
            
            # 1. Analyze Critical Changes (Highest Impact)
            missing_critical = len(critical_changes.get('missing', []))
            modified_critical = len(critical_changes.get('modified', []))
            risk_points += missing_critical * 30
            risk_points += modified_critical * 20
            logging.info(f"Critical changes risk points: {risk_points} (Missing: {missing_critical}, Modified: {modified_critical})")
            
            # 2. Analyze Legal Term Changes
            removed_terms = len(legal_terms.get('removed', []))
            modified_terms = len(legal_terms.get('modified', []))
            added_terms = len(legal_terms.get('added', []))
            
            risk_points += removed_terms * 10
            risk_points += modified_terms * 8
            risk_points += added_terms * 5
            logging.info(f"Legal terms risk points: {risk_points} (Removed: {removed_terms}, Modified: {modified_terms}, Added: {added_terms})")
            
            # 3. Analyze Numeric Changes
            for change in numeric_values:
                value_type = change.get('value_type', '').lower()
                if value_type == 'amount':
                    risk_points += 15
                elif value_type == 'percentage':
                    risk_points += 10
                else:
                    risk_points += 5
            logging.info(f"After numeric changes risk points: {risk_points}")
            
            # 4. Analyze Obligation Changes
            for change in obligations:
                change_type = change.get('type', '').lower()
                if change_type == 'removed':
                    risk_points += 12
                elif change_type == 'modified':
                    risk_points += 8
                elif change_type == 'added':
                    risk_points += 5
            logging.info(f"Final risk points: {risk_points}")
            
            return risk_points
            
        except Exception as e:
            logging.error(f"Error in risk assessment: {str(e)}")
            logging.error(f"Differences structure that caused error: {differences}")
            return 100  # Return high risk score on error to be safe
            
    def _assess_risk_level(self, differences: Dict) -> str:
        """Convert risk points to risk level"""
        try:
            risk_points = self._assess_change_risk(differences)
            
            if risk_points >= 100:
                return 'Critical'
            elif risk_points >= 70:
                return 'High'
            elif risk_points >= 40:
                return 'Medium'
            elif risk_points >= 20:
                return 'Low'
            else:
                return 'Minimal'
                
        except Exception as e:
            logging.error(f"Error determining risk level: {str(e)}")
            return 'Unknown'

    def _generate_change_summary(self, differences: Dict) -> str:
        """Generate human-readable summary of changes"""
        summary_parts = []
        
        if differences['legal_terms']['modified']:
            summary_parts.append(
                f"Modified {len(differences['legal_terms']['modified'])} legal terms"
            )
        if differences['legal_terms']['removed']:
            summary_parts.append(
                f"Removed {len(differences['legal_terms']['removed'])} legal terms"
            )
        if differences['numeric_values']:
            summary_parts.append(
                f"Changed {len(differences['numeric_values'])} numeric values"
            )
        if differences['obligations']:
            summary_parts.append(
                f"Modified {len(differences['obligations'])} obligations"
            )
            
        return '. '.join(summary_parts) if summary_parts else "No significant changes detected"

    def clean_text(self, text: str) -> str:
        """Minimal text cleaning while preserving document structure"""
        try:
            if not text:
                return ""
                
            # Only remove problematic characters that could break analysis
            text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\xFF]', '', text)
            
            # Keep original line breaks and spacing
            # Only normalize if there are excessive spaces (more than 2)
            text = re.sub(r' {3,}', '  ', text)
            
            return text
            
        except Exception as e:
            logging.error(f"Error in minimal cleaning: {str(e)}")
            return text

    def format_clause_text(self, text: str) -> str:
        """Format clause text while preserving legal document structure"""
        try:
            if not text:
                return ""

            # Only handle basic cleaning of control characters
            text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\xFF]', '', text)
            
            # Split into lines while preserving original spacing
            lines = text.splitlines()
            formatted_lines = []
            
            for i, line in enumerate(lines):
                # Preserve original indentation
                leading_space = re.match(r'^(\s*)', line).group(1)
                
                # Keep original capitalization
                content = line[len(leading_space):]
                
                # Only add minimal formatting for completely unformatted text
                if i == 0 and not re.match(r'^[\d\.\(\)A-Z]', content):
                    content = content[0].upper() + content[1:] if content else ""
                
                formatted_lines.append(leading_space + content)
            
            # Preserve original line breaks and structure
            return '\n'.join(formatted_lines)
            
        except Exception as e:
            logging.error(f"Error in minimal formatting: {str(e)}")
            return text  # Return original if formatting fails

    def format_comparison_result(self, result: Dict) -> Dict:
        """Format comparison result for better frontend display"""
        try:
            formatted_result = {
                'summary': {
                    'overall_similarity': min(max(result.get('similarity_score', 0), 0), 100),
                    'risk_level': result.get('risk_level', 'Unknown'),
                    'quick_summary': result.get('change_summary', ''),
                    'status': self._get_comparison_status(result.get('similarity_score', 0))
                },
                
                'detailed_scores': {
                    'legal_terms': {
                        'score': result.get('component_scores', {}).get('legal_term_score', 0),
                        'weight': '40%',
                        'description': 'Analysis of legal terminology and context'
                    },
                    'numeric_values': {
                        'score': result.get('component_scores', {}).get('numeric_score', 0),
                        'weight': '25%',
                        'description': 'Comparison of dates, amounts, and durations'
                    },
                    'obligations': {
                        'score': result.get('component_scores', {}).get('obligation_score', 0),
                        'weight': '20%',
                        'description': 'Analysis of legal obligations and requirements'
                    },
                    'semantic': {
                        'score': result.get('component_scores', {}).get('semantic_score', 0),
                        'weight': '15%',
                        'description': 'General meaning and context comparison'
                    }
                },

                'changes': {
                    'critical_changes': self._format_critical_changes(result.get('differences', {}).get('legal_terms', {})),
                    'numeric_changes': self._format_numeric_changes(result.get('differences', {}).get('numeric_values', [])),
                    'obligation_changes': self._format_obligation_changes(result.get('differences', {}).get('obligations', [])),
                },

                'risk_analysis': {
                    'level': result.get('risk_level', 'Unknown'),
                    'factors': self._get_risk_factors(result.get('differences', {})),
                    'recommendations': self._get_recommendations(result.get('differences', {}))
                },

                'visual_data': {
                    'similarity_chart': {
                        'labels': ['Legal Terms', 'Numeric Values', 'Obligations', 'Semantic'],
                        'values': [
                            result.get('component_scores', {}).get('legal_term_score', 0),
                            result.get('component_scores', {}).get('numeric_score', 0),
                            result.get('component_scores', {}).get('obligation_score', 0),
                            result.get('component_scores', {}).get('semantic_score', 0)
                        ]
                    }
                }
            }

            return formatted_result

        except Exception as e:
            logging.error(f"Error formatting comparison result: {str(e)}")
            return {
                'error': str(e),
                'summary': {
                    'overall_similarity': 0,
                    'risk_level': 'Error',
                    'quick_summary': 'Error in formatting results',
                    'status': 'Error'
                }
            }

    def _get_comparison_status(self, similarity_score: float) -> str:
        """Get a user-friendly status based on similarity score"""
        if similarity_score >= 95:
            return 'Nearly Identical'
        elif similarity_score >= 85:
            return 'Very Similar'
        elif similarity_score >= 70:
            return 'Similar with Notable Changes'
        elif similarity_score >= 50:
            return 'Significantly Different'
        else:
            return 'Substantially Different'

    def _format_critical_changes(self, legal_terms: Dict) -> List[Dict]:
        """Format critical legal term changes for frontend display"""
        critical_changes = []
        
        # Handle modified terms
        for change in legal_terms.get('modified', []):
            critical_changes.append({
                'type': 'Modified Term',
                'term': change['term'],
                'original': change['original_context'],
                'new': change['new_context'],
                'importance': 'High' if change['term'] in ['shall', 'must', 'will'] else 'Medium'
            })
        
        # Handle removed terms
        for term in legal_terms.get('removed', []):
            critical_changes.append({
                'type': 'Removed Term',
                'term': term[0],  # term is a tuple of (term, context)
                'context': term[1],
                'importance': 'High'
            })
        
        return critical_changes

    def _format_numeric_changes(self, numeric_values: List[Dict]) -> List[Dict]:
        """Format numeric value changes for frontend display"""
        return [{
            'type': change['type'],
            'original': change.get('from', 'N/A'),
            'new': change.get('to', 'N/A'),
            'difference': self._calculate_difference(change.get('from', '0'), change.get('to', '0')),
            'importance': 'High' if change['type'] in ['money', 'percentage'] else 'Medium'
        } for change in numeric_values]
    

    def _format_obligation_changes(self, obligations: List[Dict]) -> List[Dict]:
        """Format obligation changes for frontend display"""
        return [{
            'type': 'Obligation Change',
            'original': obligation.get('from', 'N/A'),
            'new': obligation.get('to', 'N/A'),
            'importance': 'High'
        } for obligation in obligations]

    def _get_risk_factors(self, differences: Dict) -> List[Dict]:
        """Generate risk factors based on differences"""
        risk_factors = []
        
        # Check legal term changes
        if differences.get('legal_terms', {}).get('modified'):
            risk_factors.append({
                'factor': 'Legal Term Modifications',
                'importance': 'High',
                'description': 'Critical legal terms have been modified'
            })
        
        # Check numeric changes
        numeric_changes = differences.get('numeric_values', [])
        if any(c['type'] in ['money', 'percentage'] for c in numeric_changes):
            risk_factors.append({
                'factor': 'Financial Changes',
                'importance': 'High',
                'description': 'Monetary or percentage values have been modified'
            })
        
        return risk_factors

    def _get_recommendations(self, differences: Dict) -> List[str]:
        """Generate recommendations based on differences"""
        recommendations = []
        
        # Legal term recommendations
        if differences.get('legal_terms', {}).get('modified'):
            recommendations.append(
                'Review all modified legal terms with legal counsel'
            )
        
        # Numeric value recommendations
        if differences.get('numeric_values'):
            recommendations.append(
                'Verify all changed numeric values, especially monetary amounts'
            )
        
        # Obligation recommendations
        if differences.get('obligations'):
            recommendations.append(
                'Review changes in obligations and responsibilities'
            )
        
        return recommendations or ['No specific recommendations']

    def _calculate_difference(self, original: str, new: str) -> str:
        """Calculate and format the difference between numeric values"""
        try:
            # Extract numeric values
            orig_num = float(''.join(filter(str.isdigit, original.replace(',', ''))))
            new_num = float(''.join(filter(str.isdigit, new.replace(',', ''))))
            
            # Calculate percentage difference
            if orig_num != 0:
                diff_percent = ((new_num - orig_num) / orig_num) * 100
                return f"{diff_percent:+.1f}%"
            return "N/A"
        except:
            return "N/A"

    def generate_recommendations(self, comparison_results: Dict) -> List[Dict]:
        """Generate comprehensive recommendations with actionable insights."""
        try:
            recommendations = []
            
            # 1. Process Critical Legal Term Changes
            legal_changes = comparison_results.get('differences', {}).get('legal_terms', {})
            if legal_changes.get('modified') or legal_changes.get('removed'):
                recommendations.append({
                    'priority': 'High',
                    'category': 'Legal',
                    'title': 'Legal Term Modifications',
                    'description': self._format_legal_changes_description(legal_changes),
                    'action': 'Review with legal counsel',
                    'impact': 'May affect legal obligations and rights',
                    'details': legal_changes
                })

            # 2. Process Financial Changes
            numeric_changes = comparison_results.get('differences', {}).get('numeric_values', [])
            financial_changes = [c for c in numeric_changes if c['type'] in ['money', 'percentage']]
            if financial_changes:
                recommendations.append({
                    'priority': 'High',
                    'category': 'Financial',
                    'title': 'Financial Term Changes',
                    'description': self._format_financial_changes_description(financial_changes),
                    'action': 'Verify all financial changes and their implications',
                    'impact': 'Direct monetary impact',
                    'details': financial_changes
                })

            # 3. Process Timeline Changes
            timeline_changes = [c for c in numeric_changes if c['type'] in ['date', 'duration']]
            if timeline_changes:
                recommendations.append({
                    'priority': 'Medium',
                    'category': 'Timeline',
                    'title': 'Timeline Modifications',
                    'description': self._format_timeline_changes_description(timeline_changes),
                    'action': 'Review all timeline changes and their feasibility',
                    'impact': 'May affect project schedules and deadlines',
                    'details': timeline_changes
                })

            # 4. Process Obligation Changes
            obligation_changes = comparison_results.get('differences', {}).get('obligations', [])
            if obligation_changes:
                recommendations.append({
                    'priority': 'High',
                    'category': 'Obligations',
                    'title': 'Changed Obligations',
                    'description': self._format_obligation_changes_description(obligation_changes),
                    'action': 'Review all modified obligations and responsibilities',
                    'impact': 'May affect party responsibilities and requirements',
                    'details': obligation_changes
                })

            # 5. Risk Level Based Recommendations
            risk_level = comparison_results.get('risk_level', 'Unknown')
            if risk_level == 'High':
                recommendations.append({
                    'priority': 'High',
                    'category': 'Risk',
                    'title': 'High Risk Changes Detected',
                    'description': 'Multiple significant changes requiring careful review',
                    'action': 'Conduct thorough legal and financial review',
                    'impact': 'Multiple changes may have cumulative risk impact',
                    'details': {'risk_level': risk_level}
                })

            # Sort recommendations by priority
            priority_order = {'High': 0, 'Medium': 1, 'Low': 2}
            recommendations.sort(key=lambda x: priority_order[x['priority']])

            return recommendations or [{
                'priority': 'Low',
                'category': 'General',
                'title': 'Minor Changes',
                'description': 'No significant changes detected',
                'action': 'Standard review recommended',
                'impact': 'Minimal impact expected',
                'details': {}
            }]

        except Exception as e:
            logging.error(f"Error generating recommendations: {str(e)}")
            return [{
                'priority': 'High',
                'category': 'Error',
                'title': 'Error in Analysis',
                'description': 'Unable to generate recommendations',
                'action': 'Manual review required',
                'impact': 'Unable to assess impact',
                'details': {'error': str(e)}
            }]

    def _format_legal_changes_description(self, legal_changes: Dict) -> str:
        """Format description of legal term changes"""
        parts = []
        if modified := legal_changes.get('modified', []):
            parts.append(f"Modified {len(modified)} legal terms")
        if removed := legal_changes.get('removed', []):
            parts.append(f"Removed {len(removed)} legal terms")
        return '. '.join(parts) + '.' if parts else "Legal term changes detected."

    def _format_financial_changes_description(self, changes: List[Dict]) -> str:
        """Format description of financial changes"""
        total_change = sum(
            float(c.get('difference', '0').rstrip('%'))
            for c in changes
            if c.get('difference', 'N/A') != 'N/A'
        )
        return (f"{len(changes)} financial term{'s' if len(changes) > 1 else ''} "
                f"changed with net {total_change:+.1f}% impact.")

    def _format_timeline_changes_description(self, changes: List[Dict]) -> str:
        """Format description of timeline changes"""
        return (f"{len(changes)} timeline modification{'s' if len(changes) > 1 else ''} "
                f"affecting dates or durations.")

    def _format_obligation_changes_description(self, changes: List[Dict]) -> str:
        """Format description of obligation changes"""
        return (f"{len(changes)} obligation{'s' if len(changes) > 1 else ''} "
                f"modified affecting party responsibilities.")

    def analyze_critical_clauses(
            self, 
            expected_clauses: List[Dict], 
            contract_clauses: List[Dict],
            matches: List[Dict],
            partial_matches: List[Dict]
        ) -> Dict:
            """Analyze critical clauses in the contract comparison."""
            results = {
                'missing_critical': [],
                'modified_critical': [],
                'matched_critical': []
            }
            
            # Track processed clauses
            processed_expected = {m['expected_clause']['number'] for m in matches}
            processed_expected.update({p['expected_clause']['number'] for p in partial_matches})
            
            # Check each expected clause
            for exp_clause in expected_clauses:
                is_critical, clause_type, importance = self.is_critical_clause(exp_clause['text'])
                if not is_critical:
                    continue
                    
                # Check if this clause is in matches
                matched = False
                for match in matches:
                    if match['expected_clause']['number'] == exp_clause['number']:
                        results['matched_critical'].append({
                            'type': clause_type,
                            'expected': exp_clause['text'],
                            'actual': match['contract_clause']['text'],
                            'similarity': match['similarity_score']
                        })
                        matched = True
                        break
                        
                # If not in matches, check partial matches
                if not matched:
                    for partial in partial_matches:
                        if partial['expected_clause']['number'] == exp_clause['number']:
                            results['modified_critical'].append({
                                'type': clause_type,
                                'expected': exp_clause['text'],
                                'actual': partial['contract_clause']['text'],
                                'similarity': partial['similarity_score']
                            })
                            matched = True
                            break
                            
                # If not found at all, it's missing
                if not matched:
                    results['missing_critical'].append({
                        'type': clause_type,
                        'expected': exp_clause['text']
                    })
            
            return results

    def is_critical_clause(self, text: str) -> Tuple[bool, str, str]:
        """Check if a clause is critical and return its type and importance.
        
        Args:
            text (str): The text content of the clause to analyze
            
        Returns:
            Tuple[bool, str, str]: (is_critical, clause_type, importance)
            - is_critical: Whether the clause is critical
            - clause_type: Type of the clause (if multiple, joined by '|')
            - importance: Highest importance level found
            
        Raises:
            ValueError: If input text is None or empty
        """
        try:
            # Input validation
            if not text or not isinstance(text, str):
                raise ValueError("Input text must be a non-empty string")
            
            text_lower = text.lower()
            matched_types = []
            highest_importance = ''
            
            # Map importance levels to numeric values for comparison
            importance_levels = {'High': 3, 'Medium': 2, 'Low': 1}
            
            for clause_type, info in self.critical_clause_patterns.items():
                for pattern in info['patterns']:
                    try:
                        if re.search(pattern, text_lower):
                            matched_types.append(clause_type)
                            # Update highest importance if current is higher
                            current_importance = info.get('importance', 'Low')
                            if not highest_importance or importance_levels.get(current_importance, 0) > importance_levels.get(highest_importance, 0):
                                highest_importance = current_importance
                            break  # Found match for this clause type, move to next
                    except re.error as e:
                        logger.error(f"Invalid regex pattern in critical_clause_patterns: {pattern}")
                        continue
            
            if matched_types:
                return True, '|'.join(set(matched_types)), highest_importance
                
            return False, '', ''
            
        except Exception as e:
            logger.error(f"Error in is_critical_clause: {str(e)}")
            return False, '', ''

    def compare_contracts(self, expected_clauses: List[Dict], contract_clauses: List[Dict]) -> Dict:
        try:
            comparison_results = {
                'similarity_score': 0.0,
                'component_scores': {
                    'legal_term_score': 0.0,
                    'numeric_score': 0.0,
                    'obligation_score': 0.0,
                    'semantic_score': 0.0
                },
                'differences': {
                    'legal_terms': {},
                    'numeric_values': [],
                    'obligations': [],
                    'critical_changes': []
                },
                'risk_level': 'Medium',
                'change_summary': '',
                'summary': {
                    'match_count': 0,
                    'partial_match_count': 0,
                    'mismatch_count': 0,
                    'overall_similarity': 0.0,
                    'risk_level': 'Medium',
                    'critical_issues_count': 0
                },
                'matches': [],
                'partial_matches': [],
                'mismatches': [],
                'critical_analysis': {
                    'missing_critical': [],
                    'modified_critical': [],
                    'matched_critical': []
                }
            }

            print("\n=== Starting Contract Comparison ===")
            print(f"Expected Clauses: {len(expected_clauses)}")
            print(f"Contract Clauses: {len(contract_clauses)}")

            print("\n=== Processing Each Expected Clause ===")
            for expected_clause in expected_clauses:
                print(f"\nAnalyzing Expected Clause {expected_clause.get('number', 'Unknown')}:")
                print(f"Title: {expected_clause.get('title', 'Untitled')}")
                
                best_match = None
                best_score = 0
                best_result = None

                print("\nLooking for matches in contract clauses...")
                for contract_clause in contract_clauses:
                    # Compare texts using detailed analysis
                    result = self.compare_texts(
                        expected_clause['text'],
                        contract_clause['text']
                    )
                    
                    # Ensure result has all required fields
                    if not isinstance(result, dict):
                        result = {
                            'similarity_score': 0.0,
                            'component_scores': {
                                'legal_term_score': 0.0,
                                'numeric_score': 0.0,
                                'obligation_score': 0.0,
                                'semantic_score': 0.0
                            },
                            'differences': {}
                        }
                    
                    print(f"\nComparing with Contract Clause {contract_clause.get('number', 'Unknown')}:")
                    print(f"Similarity Score: {result.get('similarity_score', 0):.2f}%")
                    print(f"Component Scores:")
                    print(f"- Legal Terms: {result.get('component_scores', {}).get('legal_term_score', 0):.2f}%")
                    print(f"- Numeric Values: {result.get('component_scores', {}).get('numeric_score', 0):.2f}%")
                    print(f"- Obligations: {result.get('component_scores', {}).get('obligation_score', 0):.2f}%")
                    print(f"- Semantic: {result.get('component_scores', {}).get('semantic_score', 0):.2f}%")
                    
                    if result.get('similarity_score', 0) > best_score:
                        best_score = result.get('similarity_score', 0)
                        best_match = contract_clause
                        best_result = result.copy()  # Make a copy to prevent reference issues
                        # Update component scores with the best match's scores
                        comparison_results['component_scores'] = result.get('component_scores', {}).copy()
                        print(f"New best match found! Score: {best_score:.2f}%")

                # Categorize the match
                if best_match and best_result:
                    print(f"\nBest Match Results:")
                    print(f"Final Score: {best_score:.2f}%")
                    print(f"Match Category: ", end="")
                    
                    match_data = {
                        'expected_clause': expected_clause,
                        'contract_clause': best_match,
                        'similarity_score': best_score,
                        'differences': best_result.get('differences', {}),
                        'component_scores': best_result.get('component_scores', {}).copy()
                    }
                    
                    if best_score >= 90:
                        print("EXACT MATCH")
                        comparison_results['matches'].append(match_data)
                    elif best_score >= 70:
                        print("PARTIAL MATCH")
                        comparison_results['partial_matches'].append(match_data)
                    else:
                        print("MISMATCH")
                        comparison_results['mismatches'].append(match_data)

            print("\n=== Calculating Final Scores ===")
            # Calculate overall metrics
            total_clauses = len(expected_clauses)
            if total_clauses > 0:
                weighted_matches = (
                    len(comparison_results['matches']) * 1.0 +
                    len(comparison_results['partial_matches']) * 0.5
                )
                overall_similarity = (weighted_matches / total_clauses) * 100
                print(f"Overall Similarity: {overall_similarity:.2f}%")
                comparison_results['similarity_score'] = overall_similarity
                comparison_results['summary']['overall_similarity'] = overall_similarity

            # Analyze critical clauses
            print("\n=== Analyzing Critical Clauses ===")
            critical_analysis = self.analyze_critical_clauses(
                expected_clauses,
                contract_clauses,
                comparison_results['matches'],
                comparison_results['partial_matches']
            )
            comparison_results['critical_analysis'].update(critical_analysis)
            print(f"Missing Critical Clauses: {len(critical_analysis['missing_critical'])}")
            print(f"Modified Critical Clauses: {len(critical_analysis['modified_critical'])}")
            print(f"Matched Critical Clauses: {len(critical_analysis['matched_critical'])}")

            # Update risk level
            print("\n=== Assessing Risk Level ===")
            risk_score = self._assess_change_risk(comparison_results['differences'])
            comparison_results['risk_level'] = risk_score
            comparison_results['summary']['risk_level'] = risk_score
            print(f"Final Risk Level: {risk_score}")

            return comparison_results

        except Exception as e:
            print(f"\nError in compare_contracts: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return comparison_results

    def _analyze_clause_differences(self, exp_clause: Dict, cont_clause: Dict) -> Dict:
        """Analyze specific differences between two clauses."""
        analysis = {
            'structural_changes': [],
            'content_changes': [],
            'numeric_changes': [],
            'entity_changes': [],
            'significance': 'Low'
        }

        try:
            # Compare structure
            exp_sentences = sent_tokenize(exp_clause['text'])
            cont_sentences = sent_tokenize(cont_clause['text'])
            
            # Analyze sentence-level changes
            analysis['structural_changes'] = self._compare_sentence_structures(exp_sentences, cont_sentences)

            # Compare numeric values
            analysis['numeric_changes'] = self._compare_numeric_values(exp_clause['text'], cont_clause['text'])

            # Compare entities
            analysis['entity_changes'] = self._compare_entities(exp_clause.get('entities', []), 
                                                                 cont_clause.get('entities', []))

            # Analyze content changes
            analysis['content_changes'] = self._analyze_content_changes(exp_clause['text'], 
                                                                 cont_clause['text'])

            # Determine significance of changes
            analysis['significance'] = self._determine_change_significance(analysis)

            return analysis
        except Exception as e:
            logger.error(f"Error in _analyze_clause_differences: {str(e)}")
            return analysis

    def _compare_sentence_structures(self, exp_sentences: List[str], cont_sentences: List[str]) -> List[Dict]:
        """Compare sentence structures between clauses."""
        changes = []
        try:
            # Compare sentence counts
            if len(exp_sentences) != len(cont_sentences):
                changes.append({
                    'type': 'structure',
                    'description': f'Sentence count mismatch: expected {len(exp_sentences)}, found {len(cont_sentences)}',
                    'severity': 'Medium'
                })

            # Compare each sentence
            for i, exp_sent in enumerate(exp_sentences):
                if i < len(cont_sentences):
                    # Compare sentence lengths
                    len_diff = abs(len(exp_sent.split()) - len(cont_sentences[i].split()))
                    if len_diff > 5:
                        changes.append({
                            'type': 'structure',
                            'description': f'Significant length difference in sentence {i+1}',
                            'severity': 'Low'
                        })

                    # Compare sentence patterns
                    exp_pattern = self._get_sentence_pattern(exp_sent)
                    cont_pattern = self._get_sentence_pattern(cont_sentences[i])
                    if exp_pattern != cont_pattern:
                        changes.append({
                            'type': 'structure',
                            'description': f'Different sentence structure in sentence {i+1}',
                            'severity': 'Medium'
                        })

        except Exception as e:
            logger.error(f"Error in _compare_sentence_structures: {str(e)}")
        
        return changes

    def _compare_numeric_values(self, text1: str, text2: str) -> List[Dict]:
        """Compare numeric values between texts."""
        changes = []
        try:
            # Extract numeric values with context
            patterns = {
                'amount': r'(?:USD|€|£|\$)\s*\d+(?:,\d{3})*(?:\.\d{2})?',
                'percentage': r'\d+(?:\.\d+)?%',
                'duration': r'\d+\s*(?:day|week|month|year)s?',
                'date': r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}'
            }

            # Convert inputs to strings if they're not already
            text1_str = text1 if isinstance(text1, str) else str(text1)
            text2_str = text2 if isinstance(text2, str) else str(text2)

            for value_type, pattern in patterns.items():
                values1 = re.findall(pattern, text1_str)
                values2 = re.findall(pattern, text2_str)

                # Compare values
                for val1 in values1:
                    if val1 not in values2:
                        changes.append({
                            'type': 'numeric',
                            'value_type': value_type,
                            'expected': val1,
                            'found': 'missing',
                            'severity': 'High' if value_type in ['amount', 'percentage'] else 'Medium'
                        })

                for val2 in values2:
                    if val2 not in values1:
                        changes.append({
                            'type': 'numeric',
                            'value_type': value_type,
                            'expected': 'not present',
                            'found': val2,
                            'severity': 'High' if value_type in ['amount', 'percentage'] else 'Medium'
                        })

            return changes
        except Exception as e:
            logger.error(f"Error in _compare_numeric_values: {str(e)}")
            return changes

    def _compare_obligations(self, text1: str, text2: str) -> float:
        """Compare obligations between texts and return a similarity score"""
        try:
            obligations1 = self._extract_obligations(text1)
            obligations2 = self._extract_obligations(text2)
            
            if not obligations1 and not obligations2:
                return 100.0
                
            matches = 0
            total = max(len(obligations1), len(obligations2))
            
            for obl1 in obligations1:
                for obl2 in obligations2:
                    if obl1['text'] == obl2['text']:
                        matches += 1
                        break
                        
            return (matches / total * 100) if total > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error in _compare_obligations: {str(e)}")
            return 0.0

    def _analyze_content_changes(self, text1: str, text2: str) -> List[Dict]:
        """Analyze content changes between clauses."""
        changes = []
        try:
            # Compare key legal terms
            legal_terms1 = self._extract_legal_terms(text1)
            legal_terms2 = self._extract_legal_terms(text2)

            # Find missing and added terms
            missing_terms = legal_terms1 - legal_terms2
            added_terms = legal_terms2 - legal_terms1

            if missing_terms:
                changes.append({
                    'type': 'content',
                    'description': 'Missing legal terms',
                    'terms': list(missing_terms),
                    'severity': 'High'
                })

            if added_terms:
                changes.append({
                    'type': 'content',
                    'description': 'Added legal terms',
                    'terms': list(added_terms),
                    'severity': 'Medium'
                })

            # Compare obligations
            obligations1 = self._extract_obligations(text1)
            obligations2 = self._extract_obligations(text2)

            if obligations1 != obligations2:
                changes.append({
                    'type': 'content',
                    'description': 'Modified obligations',
                    'severity': 'High'
                })

            return changes
        except Exception as e:
            logger.error(f"Error in _analyze_content_changes: {str(e)}")
            return changes

    def _determine_change_significance(self, analysis: Dict) -> str:
        """Determine the overall significance of changes."""
        try:
            # Count high severity changes
            high_severity_count = sum(
                1 for changes in analysis.values() 
                if isinstance(changes, list) 
                and any(change.get('severity') == 'High' for change in changes)
            )

            # Count medium severity changes
            medium_severity_count = sum(
                1 for changes in analysis.values() 
                if isinstance(changes, list) 
                and any(change.get('severity') == 'Medium' for change in changes)
            )

            # Determine overall significance
            if high_severity_count > 0:
                return 'High'
            elif medium_severity_count > 0:
                return 'Medium'
            return 'Low'

        except Exception as e:
            logger.error(f"Error in _determine_change_significance: {str(e)}")
            return 'Low'

    def _generate_error_results(self) -> Dict:
        """Generate error results structure."""
        return {
            'summary': {
                'match_count': 0,
                'partial_match_count': 0,
                'mismatch_count': 0,
                'overall_similarity': 0.0,
                'risk_level': 'Unknown',
                'critical_issues_count': 0
            },
            'error': 'An error occurred during contract comparison',
            'matches': [],
            'partial_matches': [],
            'mismatches': [],
            'critical_analysis': {
                'missingCritical': [],
                'modifiedCritical': [],
                'matchedCritical': []
            }
        }

    def split_title_content(self, text: str) -> Tuple[str, str]:
        """Split clause text into title and content."""
        parts = text.split(':', 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        return text.strip(), ""  # Return full text as title if no separator found

    def _process_exact_match(self, exp_clause: Dict, cont_clause: Dict, score: float, analysis: Dict, results: Dict) -> None:
        """Process an exact match between clauses."""
        try:
            # Create match info
            match_info = {
                'expected_clause': exp_clause,
                'contract_clause': cont_clause,
                'similarity_score': score,
                'analysis': analysis,
                'changes': []
            }

            # Even in exact matches, check for minor variations
            if analysis.get('numeric_changes'):
                match_info['changes'].append({
                    'type': 'numeric',
                    'message': 'Minor numeric value differences detected',
                    'details': analysis['numeric_changes']
                })

            if analysis.get('entity_changes'):
                match_info['changes'].append({
                    'type': 'entity',
                    'message': 'Entity reference differences detected',
                    'details': analysis['entity_changes']
                })

            # Add to matches
            results['matches'].append(match_info)

            # Update section analysis
            results['section_analysis']['matched_sections'].append({
                'title': exp_clause.get('title', ''),
                'number': exp_clause.get('number', ''),
                'similarity': score
            })

            # If it's a critical clause, add to critical analysis
            is_critical, clause_type, importance = self.is_critical_clause(exp_clause['text'])
            if is_critical:
                results['critical_analysis']['matched_critical'].append({
                    'type': clause_type,
                    'expected': exp_clause['text'],
                    'actual': cont_clause['text'],
                    'similarity': score
                })

        except Exception as e:
            logger.error(f"Error in _process_exact_match: {str(e)}")

    def _process_partial_match(self, exp_clause: Dict, cont_clause: Dict, score: float, analysis: Dict, results: Dict) -> None:
        """Process a partial match between clauses."""
        try:
            match_info = {
                'expected_clause': exp_clause,
                'contract_clause': cont_clause,
                'similarity_score': score,
                'analysis': analysis,
                'changes': []
            }

            # Analyze differences
            if analysis['structural_changes']:
                match_info['changes'].append({
                    'type': 'structure',
                    'message': 'Structural differences detected',
                    'details': analysis['structural_changes']
                })

            if analysis['numeric_changes']:
                match_info['changes'].append({
                    'type': 'numeric',
                    'message': 'Numeric value differences detected',
                    'details': analysis['numeric_changes']
                })

            if analysis['content_changes']:
                match_info['changes'].append({
                    'type': 'content',
                    'message': 'Content differences detected',
                    'details': analysis['content_changes']
                })

            results['partial_matches'].append(match_info)
            results['section_analysis']['modified_sections'].append({
                'title': exp_clause.get('title', ''),
                'number': exp_clause.get('number', ''),
                'similarity': score,
                'changes': match_info['changes']
            })

        except Exception as e:
            logger.error(f"Error in _process_partial_match: {str(e)}")

    def _process_mismatch(self, exp_clause: Dict, cont_clause: Dict, score: float, analysis: Dict, results: Dict) -> None:
        """Process a mismatch between clauses."""
        try:
            mismatch_info = {
                'expected_clause': exp_clause,
                'best_match': cont_clause,
                'similarity_score': score,
                'analysis': analysis,
                'risk_level': 'High' if exp_clause.get('is_critical', False) else 'Medium'
            }

            results['mismatches'].append(mismatch_info)
            results['section_analysis']['missing_sections'].append({
                'title': exp_clause.get('title', ''),
                'number': exp_clause.get('number', ''),
                'is_critical': exp_clause.get('is_critical', False)
            })

            # Update risk analysis
            if exp_clause.get('is_critical', False):
                results['risk_analysis']['high_risk_items'].append({
                    'type': 'missing_critical_clause',
                    'clause': exp_clause,
                    'impact': 'Critical clause missing or significantly different'
                })

        except Exception as e:
            logger.error(f"Error in _process_mismatch: {str(e)}")

    def _process_extra_clause(self, cont_clause: Dict, results: Dict) -> None:
        """Process an extra clause found in the contract."""
        try:
            extra_info = {
                'contract_clause': cont_clause,
                'risk_level': self._assess_extra_clause_risk(cont_clause)
            }

            results['mismatches'].append({
                'type': 'extra_clause',
                'clause': cont_clause,
                'risk_level': extra_info['risk_level']
            })

            results['section_analysis']['extra_sections'].append({
                'title': cont_clause.get('title', ''),
                'number': cont_clause.get('number', ''),
                'risk_level': extra_info['risk_level']
            })

        except Exception as e:
            logger.error(f"Error in _process_extra_clause: {str(e)}")

    def _assess_risks(self, results: Dict) -> None:
        """Assess overall risks in the contract comparison."""
        try:
            risk_scores = {
                'critical_clauses': 0,
                'numeric_changes': 0,
                'structural_changes': 0,
                'content_changes': 0
            }

            # Analyze critical clauses
            missing_critical = len(results['critical_analysis'].get('missing_critical', []))
            modified_critical = len(results['critical_analysis'].get('modified_critical', []))
            risk_scores['critical_clauses'] = (missing_critical * 30 + modified_critical * 20)  # Higher weight for critical issues

            # Analyze partial matches
            for match in results.get('partial_matches', []):
                analysis = match.get('analysis', {})
                
                # Check numeric changes
                numeric_changes = [c for c in analysis.get('numeric_changes', []) if c.get('severity') == 'High']
                risk_scores['numeric_changes'] += len(numeric_changes) * 15

                # Check structural changes
                structural_changes = [c for c in analysis.get('structural_changes', []) if c.get('severity') == 'High']
                risk_scores['structural_changes'] += len(structural_changes) * 10

                # Check content changes
                content_changes = [c for c in analysis.get('content_changes', []) if c.get('severity') == 'High']
                risk_scores['content_changes'] += len(content_changes) * 15

            # Calculate total risk score (normalized to 0-100)
            total_risk_score = sum(risk_scores.values())
            normalized_score = min(100, total_risk_score)  # Cap at 100
            
            # Set risk level based on normalized score
            if normalized_score > 70:
                results['summary']['risk_level'] = 'High'
            elif normalized_score > 40:
                results['summary']['risk_level'] = 'Medium'
            else:
                results['summary']['risk_level'] = 'Low'

            # Store both raw scores and normalized score
            results['risk_analysis'] = {
                'score': normalized_score,
                'details': risk_scores,
                'level': results['summary']['risk_level']
            }

        except Exception as e:
            logger.error(f"Error in _assess_risks: {str(e)}")
            results['risk_analysis'] = {
                'score': 0,
                'details': risk_scores,
                'level': 'Low'
            }

    def _generate_recommendations(self, results: Dict) -> List[Dict]:
        """Generate recommendations based on comparison results."""
        recommendations = []
        try:
            # Get critical analysis data safely
            critical_analysis = results.get('critical_analysis', {})
            missing_critical = critical_analysis.get('missing_critical', [])
            modified_critical = critical_analysis.get('modified_critical', [])

            # Critical clause recommendations
            for missing in missing_critical:
                recommendations.append({
                    'priority': 'High',
                    'type': 'critical_clause',
                    'message': f"Add missing critical clause: {missing.get('type', 'Unknown')}",
                    'details': missing
                })

            for modified in modified_critical:
                recommendations.append({
                    'priority': 'High',
                    'type': 'modified_clause',
                    'message': f"Review modifications in critical clause: {modified.get('type', 'Unknown')}",
                    'details': modified
                })

            # Get differences safely
            differences = results.get('differences', {})
            
            # Numeric value recommendations
            numeric_changes = differences.get('numeric_values', [])
            for change in numeric_changes:
                if change.get('severity') == 'High':
                    recommendations.append({
                        'priority': 'High',
                        'type': 'numeric_change',
                        'message': f"Review numeric value change: {change.get('value_type', 'Unknown')}",
                        'details': change
                    })

            # Structure recommendations
            modified_sections = results.get('partial_matches', [])
            structure_issues = [
                section for section in modified_sections
                if any(change.get('type') == 'structure' for change in section.get('differences', {}).get('structural_changes', []))
            ]
            if structure_issues:
                recommendations.append({
                    'priority': 'Medium',
                    'type': 'structure',
                    'message': 'Review structural changes in modified sections',
                    'details': {'affected_sections': structure_issues}
                })

            return recommendations

        except Exception as e:
            logger.error(f"Error in _generate_recommendations: {str(e)}")
            return []

    def _calculate_overall_metrics(self, results: Dict) -> None:
        """Calculate overall metrics for the comparison."""
        try:
            # Calculate match counts
            results['summary']['match_count'] = len(results.get('matches', []))
            results['summary']['partial_match_count'] = len(results.get('partial_matches', []))
            results['summary']['mismatch_count'] = len(results.get('mismatches', []))
            
            # Calculate total clauses
            total_clauses = (results['summary']['match_count'] + 
                           results['summary']['partial_match_count'] + 
                           results['summary']['mismatch_count'])

            # Calculate similarity score if there are clauses
            if total_clauses > 0:
                weighted_matches = results['summary']['match_count'] * 1.0
                weighted_partials = results['summary']['partial_match_count'] * 0.5
                similarity_score = (weighted_matches + weighted_partials) / total_clauses * 100  # Convert to percentage
                results['summary']['overall_similarity'] = round(similarity_score, 1)
            else:
                results['summary']['overall_similarity'] = 0.0

            # Count critical issues
            missing_critical = len(results['critical_analysis'].get('missing_critical', []))
            modified_critical = len(results['critical_analysis'].get('modified_critical', []))
            results['summary']['critical_issues_count'] = missing_critical + modified_critical

        except Exception as e:
            logger.error(f"Error in _calculate_overall_metrics: {str(e)}")
            # Set default values in case of error
            results['summary'].update({
                'match_count': 0,
                'partial_match_count': 0,
                'mismatch_count': 0,
                'overall_similarity': 0.0,
                'critical_issues_count': 0
            })

    def _assess_extra_clause_risk(self, clause: Dict) -> str:
        """Assess the risk level of an extra clause."""
        try:
            # Check for critical keywords
            critical_keywords = [
                'terminate', 'liability', 'indemnify', 'warrant',
                'confidential', 'payment', 'intellectual property'
            ]
            
            text = clause.get('text', '').lower()
            
            if any(keyword in text for keyword in critical_keywords):
                return 'High'
            
            # Check for monetary values
            if re.search(r'(?:USD|€|£|\$)\s*\d+', text):
                return 'Medium'
            
            return 'Low'

        except Exception as e:
            logger.error(f"Error in _assess_extra_clause_risk: {str(e)}")
            return 'Low'

    def _analyze_critical_clauses(self, expected_clauses: List[Dict], contract_clauses: List[Dict], results: Dict) -> None:
        """Analyze critical clauses and update results."""
        try:
            # Check each expected clause
            for exp_clause in expected_clauses:
                is_critical, clause_type, importance = self.is_critical_clause(exp_clause['text'])
                if not is_critical:
                    continue

                # Look for matches in results
                found_match = False
                for match in results['matches']:
                    if match['expected_clause']['number'] == exp_clause['number']:
                        results['critical_analysis']['matched_critical'].append({
                            'type': clause_type,
                            'expected': exp_clause['text'],
                            'actual': match['contract_clause']['text'],
                            'similarity': match['similarity_score']
                        })  # Fixed missing closing brace
                        found_match = True
                        break

                if not found_match:
                    # Check partial matches
                    for partial in results['partial_matches']:
                        if partial['expected_clause']['number'] == exp_clause['number']:
                            results['critical_analysis']['modified_critical'].append({
                                'type': clause_type,
                                'expected': exp_clause['text'],
                                'actual': partial['contract_clause']['text'],
                                'similarity': partial['similarity_score']
                            })
                            found_match = True
                            break

                    if not found_match:
                        # Not found at all - missing critical clause
                        results['critical_analysis']['missing_critical'].append({
                            'type': clause_type,
                            'expected': exp_clause['text']
                        })

        except Exception as e:
            logger.error(f"Error in _analyze_critical_clauses: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    def _calculate_combined_score(self, similarity: float, analysis: Dict) -> float:
        """Calculate combined similarity score with analysis results."""
        try:
            base_score = similarity
            
            # Convert penalties to percentage scale
            if analysis['structural_changes']:
                base_score *= 0.9  # 10% penalty for structural changes
                
            if analysis['numeric_changes']:
                base_score *= 0.8  # 20% penalty for numeric changes
                
            if analysis['content_changes']:
                base_score *= 0.85  # 15% penalty for content changes
                
            # Add penalties for critical issues
            critical_issues = (
                len(analysis.get('critical_changes', {}).get('missing', [])) +
                len(analysis.get('critical_changes', {}).get('modified', []))
            )
            if critical_issues > 0:
                base_score *= max(0.1, 1 - (critical_issues * 0.2))  # 20% penalty per critical issue, min 10%
            
            # Ensure score is between 0 and 100
            return round(max(0.0, min(100.0, base_score)), 2)
            
        except Exception as e:
            logger.error(f"Error in _calculate_combined_score: {str(e)}")
            return similarity

    def validate_critical_clause(self, text: str) -> Dict:
        """Validate a critical clause and return validation status."""
        try:
            # Check for required elements
            validation_status = {
                'is_valid': True,
                'issues': [],
                'suggestions': []
            }
            
            # Check for missing key terms
            key_terms = ['shall', 'must', 'will', 'agree']
            if not any(term in text.lower() for term in key_terms):
                validation_status['is_valid'] = False
                validation_status['issues'].append('Missing obligation terms')
                validation_status['suggestions'].append('Add clear obligation terms (shall, must, will)')
            
            # Check for ambiguous language
            ambiguous_terms = ['may', 'might', 'could', 'should']
            if any(term in text.lower() for term in ambiguous_terms):
                validation_status['is_valid'] = False
                validation_status['issues'].append('Contains ambiguous language')
                validation_status['suggestions'].append('Replace ambiguous terms with definitive language')
            
            # Check for numeric values
            if any(pattern.search(text) for pattern in self.numeric_patterns.values()):
                # Verify numeric values are clearly specified
                if any(term in text.lower() for term in ['approximately', 'about', 'around']):
                    validation_status['is_valid'] = False
                    validation_status['issues'].append('Imprecise numeric values')
                    validation_status['suggestions'].append('Use exact numeric values')
            
            return validation_status
            
        except Exception as e:
            print(f"Error validating clause: {str(e)}")
            return {'is_valid': False, 'issues': ['Validation error'], 'suggestions': ['Review clause manually']}

    def natural_sort_key(self, text: str) -> List:
        """Convert string into list of string and number chunks for natural sorting."""
        import re
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        return [convert(c) for c in re.split('([0-9]+)', str(text))]

    def _get_sentence_pattern(self, sentence: str) -> str:
        """Extract basic sentence pattern/structure."""
        try:
            # Basic pattern extraction based on sentence structure
            doc = self.nlp(sentence)
            pattern = []
            for token in doc:
                if token.pos_ in ['VERB', 'NOUN', 'ADJ']:
                    pattern.append(token.pos_)
            return ' '.join(pattern)
        except Exception as e:
            logger.error(f"Error in _get_sentence_pattern: {str(e)}")
            return ""

    def _compare_entities(self, entities1: List[Dict], entities2: List[Dict]) -> List[Dict]:
        """Compare named entities between two texts."""
        try:
            changes = []
            entities1_set = {(e.get('text', ''), e.get('label', '')) for e in entities1}
            entities2_set = {(e.get('text', ''), e.get('label', '')) for e in entities2}
            
            # Find missing entities
            missing = entities1_set - entities2_set
            if missing:
                changes.append({
                    'type': 'entity',
                    'description': 'Missing entities',
                    'entities': list(missing),
                    'severity': 'Medium'
                })
            
            # Find added entities
            added = entities2_set - entities1_set
            if added:
                changes.append({
                    'type': 'entity',
                    'description': 'Added entities',
                    'entities': list(added),
                    'severity': 'Medium'
                })
            
            return changes
        except Exception as e:
            logger.error(f"Error in _compare_entities: {str(e)}")
            return []

    def _extract_legal_terms(self, text: str) -> Set[str]:
        """Extract legal terms and phrases from text."""
        try:
            legal_terms = set()
            doc = self.nlp(text)
            
            # Common legal term patterns
            legal_patterns = {
                'pursuant to': [
                    'according to', 'in accordance with', 'as per',
                    'in compliance with', 'under', 'following'
                ],
                'notwithstanding': [
                    'despite', 'regardless of', 'even if', 'although',
                    'in spite of', 'without regard to'
                ],
                'herein': [
                    'in this agreement', 'in this document',
                    'in these terms', 'contained herein'
                ],
                'termination': [
                    'terminate', 'cancel', 'end', 'discontinue',
                    'cease'
                ],
                'indemnification': [
                    'indemnify', 'hold harmless', 'defend',
                    'protect against', 'compensate'
                ],
                'confidentiality': [
                    'confidential', 'proprietary', 'non-disclosure',
                    'secret', 'private'
                ],
                'force majeure': [
                    'act of god', 'unforeseen circumstance',
                    'beyond control', 'unavoidable'
                ]
            }
            
            # Extract terms based on patterns
            for term, synonyms in legal_patterns.items():
                if any(syn.lower() in text.lower() for syn in [term] + synonyms):
                    legal_terms.add(term)
            
            # Extract additional legal entities
            for ent in doc.ents:
                if ent.label_ in ['LAW', 'ORG', 'GPE']:
                    legal_terms.add(ent.text)
            
            return legal_terms
            
        except Exception as e:
            logger.error(f"Error in _extract_legal_terms: {str(e)}")
            return set()

    def _extract_obligations(self, text: str) -> List[Dict]:
        """Extract obligations from text with their context"""
        obligations = []
        try:
            # Convert input to string if it's not already
            text_str = text if isinstance(text, str) else str(text)
            
            # Use class-level obligation patterns
            for pattern in self.obligation_patterns:
                matches = re.finditer(pattern, text_str.lower())
                for match in matches:
                    obligation_text = match.group()
                    context = self._get_term_context(text_str, obligation_text)
                    obligations.append({
                        'text': obligation_text,
                        'context': context,
                        'type': self._determine_obligation_type(obligation_text)
                    })
            
            return obligations
            
        except Exception as e:
            logger.error(f"Error extracting obligations: {str(e)}")
            return []

    def _determine_obligation_type(self, text: str) -> str:
        """Determine the type of obligation"""
        text_lower = text.lower()
        
        if any(term in text_lower for term in ['shall', 'must', 'will']):
            return 'mandatory'
        elif any(term in text_lower for term in ['may', 'can', 'permitted']):
            return 'permissive'
        elif any(term in text_lower for term in ['should', 'recommended']):
            return 'recommended'
        else:
            return 'other'

    def analyze_clause(self, expected_clause: Dict, contract_clause: Dict) -> Dict:
        """Analyze and compare two clauses with strict matching criteria"""
        try:
            comparison = self.compare_texts(expected_clause['text'], contract_clause['text'])
            
            # Much stricter thresholds for matching
            EXACT_MATCH_THRESHOLD = 95.0    # Near-exact match
            HIGH_MATCH_THRESHOLD = 85.0     # High confidence match
            MEDIUM_MATCH_THRESHOLD = 70.0   # Medium confidence match
            
            # Determine match confidence with stricter criteria
            similarity_score = comparison['similarity_score']
            semantic_score = comparison['semantic_score']
            lexical_score = comparison['lexical_score']
            
            # Both similarity and semantic scores must meet thresholds
            if similarity_score >= EXACT_MATCH_THRESHOLD and semantic_score >= EXACT_MATCH_THRESHOLD:
                match_confidence = 'Exact'
            elif similarity_score >= HIGH_MATCH_THRESHOLD and semantic_score >= HIGH_MATCH_THRESHOLD:
                match_confidence = 'High'
            elif similarity_score >= MEDIUM_MATCH_THRESHOLD and semantic_score >= MEDIUM_MATCH_THRESHOLD:
                match_confidence = 'Medium'
            else:
                match_confidence = 'Low'
                similarity_score = max(similarity_score * 0.5, 0)  # Penalize low confidence matches
            
            # Analyze specific differences
            differences = []
            
            # Check for numeric changes
            numeric_changes = self._extract_numeric_changes(expected_clause['text'], contract_clause['text'])
            if numeric_changes:
                differences.extend(numeric_changes)
            
            # Check for key term changes
            term_changes = self._analyze_key_terms(expected_clause['text'], contract_clause['text'])
            if term_changes:
                differences.extend(term_changes)
            
            # Check for structural changes
            if len(comparison['differences']['added']) > 0 or len(comparison['differences']['removed']) > 0:
                differences.append({
                    'type': 'content',
                    'description': 'Content modifications detected',
                    'added': list(comparison['differences']['added']),
                    'removed': list(comparison['differences']['removed']),
                    'severity': 'High' if match_confidence in ['Low', 'Medium'] else 'Medium'
                })
            
            return {
                'expected_clause': {
                    'text': comparison['text1'],
                    'category': expected_clause.get('category', 'General'),
                    'importance': expected_clause.get('importance', 'Medium')
                },
                'contract_clause': {
                    'text': comparison['text2'],
                    'category': contract_clause.get('category', 'General'),
                    'importance': contract_clause.get('importance', 'Medium')
                },
                'similarity_score': similarity_score,
                'semantic_score': semantic_score,
                'lexical_score': lexical_score,
                'match_confidence': match_confidence,
                'differences': differences
            }
        except Exception as e:
            logging.error(f"Error analyzing clause: {str(e)}")
            return {
                'expected_clause': expected_clause,
                'contract_clause': contract_clause,
                'similarity_score': 0,
                'match_confidence': 'Error'
            }
            
    def _extract_numeric_changes(self, text1: str, text2: str) -> List[Dict]:
        """Extract and compare numeric values between texts"""
        changes = []
        
        # Define patterns for different numeric types
        patterns = {
            'amount': r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
            'percentage': r'\d+(?:\.\d+)?%',
            'duration': r'\d+\s*(?:day|week|month|year)s?',
            'time': r'\d{1,2}:\d{2}\s*(?:am|pm)',
        }
        
        for value_type, pattern in patterns.items():
            values1 = set(re.findall(pattern, text1, re.IGNORECASE))
            values2 = set(re.findall(pattern, text2, re.IGNORECASE))
            
            if values1 != values2:
                changes.append({
                    'type': 'numeric',
                    'value_type': value_type,
                    'expected': list(values1),
                    'found': list(values2),
                    'severity': 'High' if value_type in ['amount', 'percentage'] else 'Medium'
                })
        
        return changes
        
    def _analyze_key_terms(self, text1: str, text2: str) -> List[Dict]:
        """Analyze changes in key legal and business terms"""
        changes = []
        
        # Define key terms to check
        key_terms = {
            'obligation': ['shall', 'must', 'will', 'agrees to'],
            'prohibition': ['shall not', 'must not', 'will not', 'may not'],
            'permission': ['may', 'is permitted to', 'is allowed to'],
            'condition': ['if', 'provided that', 'subject to', 'conditional upon'],
            'time': ['immediately', 'promptly', 'within', 'by'],
        }
        
        for term_type, terms in key_terms.items():
            # Check each term's presence/absence
            for term in terms:
                in_text1 = term.lower() in text1.lower()
                in_text2 = term.lower() in text2.lower()
                
                if in_text1 != in_text2:
                    changes.append({
                        'type': 'term',
                        'term_type': term_type,
                        'term': term,
                        'change': 'removed' if in_text1 else 'added',
                        'severity': 'High' if term_type in ['obligation', 'prohibition'] else 'Medium'
                    })
        
        return changes

    def _identify_critical_changes(self, text1: str, text2: str) -> Dict:
        """Identify changes in critical clauses"""
        try:
            # Get critical clauses from both texts
            critical1 = self._extract_critical_clauses(text1)
            critical2 = self._extract_critical_clauses(text2)
            
            missing = []
            modified = []
            matched = []
            
            # Check for missing and modified critical clauses
            for clause1 in critical1:
                found_match = False
                best_match = None
                best_score = 0
                
                for clause2 in critical2:
                    if clause1['type'] == clause2['type']:
                        # Calculate similarity between clauses
                        similarity = self.calculate_similarity_score(clause1['text'], clause2['text'])
                        if similarity > best_score:
                            best_score = similarity
                            best_match = clause2
                
                if best_score >= 90:  # High similarity threshold for critical clauses
                    matched.append({
                        'type': clause1['type'],
                        'expected': clause1['text'],
                        'actual': best_match['text'],
                        'similarity': best_score
                    })
                    found_match = True
                elif best_score >= 70:  # Modified threshold
                    modified.append({
                        'type': clause1['type'],
                        'expected': clause1['text'],
                        'actual': best_match['text'],
                        'similarity': best_score
                    })
                    found_match = True
                
                if not found_match:
                    missing.append({
                        'type': clause1['type'],
                        'expected': clause1['text']
                    })
            
            return {
                'missing': missing,
                'modified': modified,
                'matched': matched
            }
            
        except Exception as e:
            logging.error(f"Error identifying critical changes: {str(e)}")
            return {'missing': [], 'modified': [], 'matched': []}

    def _extract_critical_clauses(self, text: str) -> List[Dict]:
        """Extract critical clauses from text"""
        critical_clauses = []
        
        # Define critical clause patterns with their types
        critical_patterns = {
            'termination': [
                r'(?:right|ability)\s+to\s+terminate',
                r'termination\s+(?:for|with)\s+cause',
                r'immediate\s+termination'
            ],
            'liability': [
                r'limitation\s+of\s+liability',
                r'liability\s+cap',
                r'indemnification'
            ],
            'payment': [
                r'payment\s+terms?',
                r'fee\s+structure',
                r'pricing'
            ],
            'confidentiality': [
                r'confidential\s+information',
                r'non[-\s]?disclosure',
                r'trade\s+secrets?'
            ],
            'intellectual_property': [
                r'intellectual\s+property',
                r'ip\s+rights?',
                r'ownership\s+of\s+(?:work|materials|deliverables)'
            ]
        }
        
        # Extract critical clauses
        for clause_type, patterns in critical_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Get surrounding context
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    clause_text = text[start:end]
                    
                    critical_clauses.append({
                        'type': clause_type,
                        'text': clause_text,
                        'position': match.start()
                    })
        
        return critical_clauses

    def _analyze_differences(self, text1: str, text2: str) -> Dict:
        """Analyze differences between two texts"""
        try:
            # Initialize default structure
            default_differences = {
                'legal_terms': {
                    'added': [],
                    'removed': [],
                    'modified': []
                },
                'numeric_values': [],
                'obligations': [],
                'critical_changes': {
                    'missing': [],
                    'modified': [],
                    'matched': []
                }
            }

            # If either text is empty, return default structure
            if not text1 or not text2:
                return default_differences

            # Minimal cleaning while preserving structure
            text1 = self.clean_text(text1)
            text2 = self.clean_text(text2)
            
            # Legal Term Analysis
            legal_terms1 = self._extract_legal_terms_with_context(text1)
            legal_terms2 = self._extract_legal_terms_with_context(text2)
            legal_term_differences = self._analyze_legal_term_differences(legal_terms1, legal_terms2)
            
            # Ensure legal_terms has all required keys
            if 'legal_terms' not in legal_term_differences:
                legal_term_differences = default_differences['legal_terms']
            else:
                for key in ['added', 'removed', 'modified']:
                    if key not in legal_term_differences:
                        legal_term_differences[key] = []
            
            # Numeric Analysis
            numeric_values1 = self._extract_numeric_values(text1)
            numeric_values2 = self._extract_numeric_values(text2)
            numeric_changes = self._compare_numeric_values(numeric_values1, numeric_values2)
            
            # Obligation Analysis
            obligations1 = self._extract_obligations(text1)
            obligations2 = self._extract_obligations(text2)
            obligation_changes = self._analyze_obligation_changes(obligations1, obligations2)
            
            # Critical Changes Analysis
            critical_changes = self._identify_critical_changes(text1, text2)
            
            return {
                'legal_terms': legal_term_differences,
                'numeric_values': numeric_changes or [],
                'obligations': obligation_changes or [],
                'critical_changes': critical_changes or {
                    'missing': [],
                    'modified': [],
                    'matched': []
                }
            }
        except Exception as e:
            logging.error(f"Error in _analyze_differences: {str(e)}")
            return default_differences

    def _calculate_similarity_score(self, differences: Dict) -> float:
        """Calculate overall similarity score from differences"""
        try:
            # Legal terms weight (40%)
            legal_matches = len(differences.get('legal_terms', {}).get('matches', []))
            legal_total = (
                legal_matches +
                len(differences.get('legal_terms', {}).get('modified', [])) +
                len(differences.get('legal_terms', {}).get('removed', []))
            )
            legal_score = (legal_matches / legal_total * 100) if legal_total > 0 else 100
            
            # Numeric changes weight (25%)
            numeric_changes = differences.get('numeric_values', [])
            numeric_score = 100.0 if not numeric_changes else max(0.0, 100.0 - (len(numeric_changes) * 10))
            
            # Obligations weight (20%)
            obligation_changes = differences.get('obligations', [])
            obligation_score = 100.0 if not obligation_changes else max(0.0, 100.0 - (len(obligation_changes) * 15))
            
            # Critical changes weight (15%)
            critical_changes = differences.get('critical_changes', {})
            critical_score = 100.0
            if critical_changes:
                critical_issues = len(critical_changes.get('missing', [])) + len(critical_changes.get('modified', []))
                critical_score = max(0.0, 100.0 - (critical_issues * 20))
            
            # Calculate weighted final score
            final_score = (
                (legal_score * 0.40) +
                (numeric_score * 0.25) +
                (obligation_score * 0.20) +
                (critical_score * 0.15)
            )
            
            return round(final_score, 2)
        except Exception as e:
            logging.error(f"Error in _calculate_similarity_score: {str(e)}")
            return 0.0

    def _handle_comparison_error(self, e: Exception) -> Dict:
        """Handle comparison errors gracefully"""
        error_msg = str(e)
        logging.error(f"Comparison error: {error_msg}")
        
        # Determine error category
        if 'memory' in error_msg.lower():
            error_type = 'Memory Error'
            user_message = 'The document is too large to process. Please try with a smaller document.'
        elif 'timeout' in error_msg.lower():
            error_type = 'Timeout Error'
            user_message = 'The comparison took too long. Please try again or with a smaller document.'
        elif 'encoding' in error_msg.lower():
            error_type = 'Encoding Error'
            user_message = 'There was an issue with the document encoding. Please ensure the document is properly formatted.'
        else:
            error_type = 'Processing Error'
            user_message = 'An unexpected error occurred during comparison. Please try again.'
        
        return {
            'error': error_msg,
            'error_type': error_type,
            'user_message': user_message,
            'similarity_score': 0,
            'component_scores': {
                'legal_term_score': 0.0,
                'numeric_score': 0.0,
                'obligation_score': 0.0,
                'semantic_score': 0.0
            },
            'differences': {},
            'risk_level': 'Unknown',
            'summary': {
                'matchCount': 0,
                'partialMatchCount': 0,
                'mismatchCount': 0,
                'overallSimilarity': 0,
                'riskLevel': 'Unknown',
                'criticalIssuesCount': 0
            }
        }

    def _analyze_obligation_changes(self, obligations1: List[Dict], obligations2: List[Dict]) -> List[Dict]:
        """Analyze changes in obligations"""
        changes = []
        try:
            for obl1 in obligations1:
                found_match = False
                for obl2 in obligations2:
                    if obl1['text'] == obl2['text']:
                        found_match = True
                        break
                if not found_match:
                    changes.append({
                        'type': 'obligation',
                        'description': 'Modified obligation',
                        'original': obl1['text'],
                        'severity': 'High' if obl1.get('type') == 'critical' else 'Medium'
                    })
            return changes
        except Exception as e:
            logging.error(f"Error in _analyze_obligation_changes: {str(e)}")
            return changes

    def _calculate_component_scores(self, matches: List[Dict], partial_matches: List[Dict]) -> Dict[str, float]:
        """Calculate component-wise scores across all matches"""
        total_legal = []
        total_numeric = []
        total_obligations = []
        total_semantic = []
        
        # Process both matches and partial matches
        for match in matches + partial_matches:
            if 'similarity_score' in match:
                # Extract component scores if available
                differences = match.get('differences', {})
                
                # Legal terms score - based on proportion of unchanged terms
                legal_terms = differences.get('legal_terms', {})
                modified = len(legal_terms.get('modified', []))
                removed = len(legal_terms.get('removed', []))
                total = modified + removed + len(legal_terms.get('matches', []))
                if total == 0:
                    total_legal.append(100.0)  # No legal terms in either text
                else:
                    score = (1 - ((modified + removed) / total)) * 100
                    total_legal.append(max(0, score))
                
                # Numeric values score - based on proportion of unchanged values
                numeric_changes = differences.get('numeric_values', [])
                if not numeric_changes:
                    total_numeric.append(100.0)
                else:
                    score = max(0, 100 - (len(numeric_changes) * 20))  # -20% per change
                    total_numeric.append(score)
                
                # Obligations score - based on proportion of unchanged obligations
                obligations = differences.get('obligations', [])
                if not obligations:
                    total_obligations.append(100.0)
                else:
                    score = max(0, 100 - (len(obligations) * 25))  # -25% per change
                    total_obligations.append(score)
                
                # Semantic score (from similarity score)
                total_semantic.append(match.get('similarity_score', 0.0))
        
        # Calculate averages, handling empty lists
        def safe_average(lst):
            return sum(lst) / len(lst) if lst else 0.0
        
        return {
            'legal_term_score': round(safe_average(total_legal), 2),
            'numeric_score': round(safe_average(total_numeric), 2),
            'obligation_score': round(safe_average(total_obligations), 2),
            'semantic_score': round(safe_average(total_semantic), 2)
        }

    def _calculate_final_scores(self, matches: List[Dict], partial_matches: List[Dict]) -> Dict:
        """Calculate final scores and summary"""
        # Calculate component scores
        component_scores = self._calculate_component_scores(matches, partial_matches)
        
        # Calculate overall similarity score with weights
        weights = {
            'legal_term_score': 0.35,  # Legal terms have highest weight
            'numeric_score': 0.25,     # Numeric values and obligations equally important
            'obligation_score': 0.25,
            'semantic_score': 0.15     # Semantic similarity has lowest weight
        }
        
        # Calculate base similarity score
        similarity_score = (
            component_scores['legal_term_score'] * weights['legal_term_score'] +
            component_scores['numeric_score'] * weights['numeric_score'] +
            component_scores['obligation_score'] * weights['obligation_score'] +
            component_scores['semantic_score'] * weights['semantic_score']
        )
        
        # Count matches by type
        match_count = len([m for m in matches if m.get('similarity_score', 0) >= 95])
        partial_match_count = len([m for m in partial_matches if m.get('similarity_score', 0) >= 80])
        mismatch_count = len(matches) + len(partial_matches) - match_count - partial_match_count
        
        # Calculate critical issues
        critical_issues = 0
        for match in matches + partial_matches:
            differences = match.get('differences', {})
            legal_terms = differences.get('legal_terms', {})
            critical_issues += len(legal_terms.get('modified', [])) + len(legal_terms.get('removed', []))
        
        # Apply critical issues penalty (max 50% reduction)
        if critical_issues > 0:
            penalty = min(0.5, critical_issues * 0.1)  # 10% per critical issue, max 50%
            similarity_score *= (1 - penalty)
        
        # Determine risk level based on critical issues and similarity
        risk_level = 'Low'
        if critical_issues > 2 or similarity_score < 60:
                risk_level = 'High'
        elif critical_issues > 0 or similarity_score < 80:
                risk_level = 'Medium'
        
        return {
            'similarity_score': round(similarity_score, 2),
            'component_scores': component_scores,
            'summary': {
                'match_count': match_count,
                'partial_match_count': partial_match_count,
                'mismatch_count': mismatch_count,
                'overall_similarity': round(similarity_score, 2),
                'risk_level': risk_level,
                'critical_issues_count': critical_issues
            }
        }

    def _determine_risk_level(self, risk_points: float) -> str:
        """Convert risk points to risk level string"""
        if risk_points >= 70:
            return 'High'
        elif risk_points >= 40:
            return 'Medium'
        else:
            return 'Low'  # Default to Low instead of Minimal/Critical

    def _count_critical_issues(self, matches: List[Dict], partial_matches: List[Dict]) -> int:
        """Count number of critical issues across all matches"""
        critical_count = 0
        for match in matches + partial_matches:
            differences = match.get('differences', {})
            critical_changes = differences.get('critical_changes', {})
            critical_count += len(critical_changes.get('missing', []))
            critical_count += len(critical_changes.get('modified', []))
        return critical_count

    def compare_clauses(self, expected_clause: Dict, contract_clause: Dict) -> Dict:
        """Compare individual clauses and return detailed analysis"""
        try:
            # Calculate similarity scores
            similarity = self._calculate_similarity(expected_clause['text'], contract_clause['text'])
            differences = self._analyze_clause_differences(expected_clause, contract_clause)
            
            # Determine match category
            critical_issues = (
                len(differences.get('critical_changes', {}).get('missing', [])) +
                len(differences.get('critical_changes', {}).get('modified', []))
            )
            match_category = self._determine_match_category(similarity, critical_issues)
            
            return {
                'expected_clause': expected_clause,
                'contract_clause': contract_clause,
                'similarity_score': similarity,
                'differences': differences,
                'match_category': match_category
            }

        except Exception as e:
            logging.error(f"Error comparing clauses: {str(e)}")
            return {
                'expected_clause': expected_clause,
                'contract_clause': contract_clause,
                'similarity_score': 0,
                'differences': {},
                'match_category': 'Unknown'
            }

    def _get_legal_term_differences(self, text1: str, text2: str) -> Dict:
        """Get differences in legal terms between two texts"""
        try:
            # Extract legal terms with context from both texts
            terms1 = self._extract_legal_terms_with_context(text1)
            terms2 = self._extract_legal_terms_with_context(text2)
            
            # Analyze differences using existing method
            return self._analyze_legal_term_differences(terms1, terms2)
        except Exception as e:
            logging.error(f"Error in _get_legal_term_differences: {str(e)}")
            return {
                'added': [],
                'removed': [],
                'modified': []
            }

    def _get_numeric_differences(self, text1: str, text2: str) -> List[Dict]:
        """Get differences in numeric values between two texts"""
        try:
            # Extract numeric values with their context
            numeric_values1 = self._extract_numeric_values(text1)
            numeric_values2 = self._extract_numeric_values(text2)
            
            # Compare and get differences
            differences = []
            
            # Check for values in text1 not in text2
            for value1 in numeric_values1:
                found_match = False
                for value2 in numeric_values2:
                    if value1['value'] == value2['value'] and value1['type'] == value2['type']:
                        found_match = True
                        break
                if not found_match:
                    differences.append({
                        'type': 'removed',
                        'value': value1['value'],
                        'value_type': value1['type'],
                        'context': value1.get('context', ''),
                        'severity': 'High' if value1['type'] in ['amount', 'percentage'] else 'Medium'
                    })
            
            # Check for values in text2 not in text1
            for value2 in numeric_values2:
                found_match = False
                for value1 in numeric_values1:
                    if value2['value'] == value1['value'] and value2['type'] == value1['type']:
                        found_match = True
                        break
                if not found_match:
                    differences.append({
                        'type': 'added',
                        'value': value2['value'],
                        'value_type': value2['type'],
                        'context': value2.get('context', ''),
                        'severity': 'High' if value2['type'] in ['amount', 'percentage'] else 'Medium'
                    })
            
            return differences
            
        except Exception as e:
            logging.error(f"Error in _get_numeric_differences: {str(e)}")
            return []

    def _get_obligation_differences(self, text1: str, text2: str) -> List[Dict]:
        """Get differences in obligations between two texts"""
        try:
            differences = []
            
            # Extract obligations from both texts
            obligations1 = self._extract_obligations(text1)
            obligations2 = self._extract_obligations(text2)
            
            # Track matched obligations to identify additions/removals
            matched_obligations = set()
            
            # Compare each obligation from text1 with text2
            for obl1 in obligations1:
                found_match = False
                for obl2 in obligations2:
                    if obl1['text'] == obl2['text']:
                        found_match = True
                        matched_obligations.add(obl2['text'])
                        # Check for context changes
                        if obl1['context'] != obl2['context']:
                            differences.append({
                                'type': 'modified',
                                'obligation': obl1['text'],
                                'original_context': obl1['context'],
                                'new_context': obl2['context']
                            })
                        break
                
                if not found_match:
                    differences.append({
                        'type': 'removed',
                        'obligation': obl1['text'],
                        'context': obl1['context']
                    })
            
            # Check for added obligations
            for obl2 in obligations2:
                if obl2['text'] not in matched_obligations:
                    differences.append({
                        'type': 'added',
                        'obligation': obl2['text'],
                        'context': obl2['context']
                    })
            
            return differences
            
        except Exception as e:
            logging.error(f"Error getting obligation differences: {str(e)}")
            return []
