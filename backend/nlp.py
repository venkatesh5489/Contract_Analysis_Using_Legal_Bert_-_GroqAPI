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
            # Using a more reliable legal model that's compatible with sentence-transformers
            self.similarity_model = SentenceTransformer('law-ai/InLegalBERT')
            logging.info("Successfully loaded Legal model")
        except Exception as e:
            logging.error(f"Error loading Legal model: {e}")
            # Fallback to a smaller, general-purpose model if Legal model fails
            self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
            logging.warning("Falling back to MiniLM model")
        
        # Initialize spaCy NLP model for NER
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except OSError:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load('en_core_web_sm')
        
        # Initialize Groq client with proper error handling
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            logging.warning("GROQ_API_KEY not found in environment variables")
            self.groq_client = None
        else:
            try:
                self.groq_client = groq.Groq(
                    api_key=api_key,
                    # Remove problematic parameters
                    base_url="https://api.groq.com/v1"
                )
                logging.info("Successfully initialized Groq client")
            except Exception as e:
                logging.error(f"Error initializing Groq client: {e}")
                self.groq_client = None

        # Initialize TF-IDF vectorizer
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.tfidf = TfidfVectorizer(stop_words='english')
        
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
                    r'act(?:s)?\s+of\s+god',
                    r'unforeseen\s+(?:circumstances?|events?)',
                    # Specific events
                    r'(?:natural|man-made)\s+disaster',
                    r'(?:pandemic|epidemic|outbreak)',
                    r'(?:war|terrorism|civil\s+unrest)',
                    # Effects and procedures
                    r'(?:suspension|interruption)\s+of\s+(?:service|performance)',
                    r'(?:delay|prevention)\s+of\s+performance',
                    # Notice requirements
                    r'force\s+majeure\s+notice',
                    r'notification\s+requirement',
                    # Duration and termination
                    r'duration\s+of\s+force\s+majeure',
                    r'right\s+to\s+terminate\s+(?:due\s+to|following)\s+force\s+majeure'
                ],
                'importance': 'High',
                'category': 'Legal',
                'risk_level': 'Medium',
                'validation_required': True
            }
        }

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
        """Normalize legal terms to improve matching accuracy."""
        normalized = text.lower()
        for standard, variants in self.legal_term_normalizations.items():
            for variant in variants:
                normalized = normalized.replace(variant, standard)
        return normalized

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
        """Enhanced clause extraction with domain-specific context."""
        try:
            # Input validation
            if not text or len(text.strip()) < 10:
                print("\nError: Input text is too short or empty")
                return []

            # Detect domain using NER
            domain, confidence = self.detect_domain_with_ner(text)
            print(f"\nProcessing document with detected domain: {domain}")
            
            # Normalize legal terms before extraction
            normalized_text = self.normalize_legal_terms(text)
            
            # Initialize patterns for different section formats
            section_patterns = {
                'numbered': r'(\d+\.)\s*([^:]+):\s*([^\n]+(?:\n(?!\d+\.)[^\n]+)*)',
                'lettered': r'([A-Z]\.)\s*([^:]+):\s*([^\n]+(?:\n(?![A-Z]\.)[^\n]+)*)',
                'roman': r'([XVI]+\.)\s*([^:]+):\s*([^\n]+(?:\n(?![XVI]+\.)[^\n]+)*)',
                'caps': r'([A-Z][A-Z\s]+):\s*([^\n]+(?:\n(?![A-Z][A-Z\s]+:)[^\n]+)*)'
            }
            
            validated_clauses = []
            
            # Process each pattern type
            for pattern_type, pattern in section_patterns.items():
                matches = re.finditer(pattern, normalized_text)
                for match in matches:
                    if len(match.groups()) >= 2:
                        number = match.group(1).rstrip('.')
                        title = match.group(2).strip()
                        content = match.group(3).strip() if len(match.groups()) > 2 else ""
                        
                        # Skip empty or invalid sections
                        if not content or len(content) < 10:
                            continue
                        
                        # Process the clause
                        clause = self._process_clause(number, title, content, domain, confidence)
                        if clause:
                            validated_clauses.append(clause)
            
            # If no clauses found, try LLM-based extraction
            if not validated_clauses:
                print("No structured sections found, attempting LLM-based extraction...")
                validated_clauses = self._extract_with_llm(normalized_text, domain, confidence)
            
            # Post-process and sort clauses
            if validated_clauses:
                validated_clauses.sort(key=lambda x: self.natural_sort_key(x['number']))
                print(f"Successfully extracted {len(validated_clauses)} clauses")
                return validated_clauses
            
            return []

        except Exception as e:
            print(f"Error in extract_clauses: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return []

    def _process_clause(self, number: str, title: str, content: str, domain: str, confidence: float) -> Optional[Dict]:
        """Process a single clause and return structured data."""
        try:
            # Basic validation
            if not content.strip():
                return None
            
            # Process with spaCy for entity extraction
            doc = self.nlp(content)
            entities = [{'text': ent.text, 'label': ent.label_} for ent in doc.ents]
            
            # Determine clause characteristics
            is_critical, clause_type, importance = self.is_critical_clause(content)
            category = self.determine_clause_category(content, domain) or "General"
            
            # Validate critical clauses
            validation_status = None
            if is_critical:
                validation_status = self.validate_critical_clause(content)
            
            return {
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
            
        except Exception as e:
            print(f"Error processing clause: {str(e)}")
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

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Enhanced similarity computation with multiple comparison strategies."""
        try:
            if not text1 or not text2:
                return 0.0
            
            # Normalize and clean texts
            text1 = self._normalize_text(text1)
            text2 = self._normalize_text(text2)
            
            # Calculate different similarity scores
            scores = {
                'semantic': self._compute_semantic_similarity(text1, text2),
                'lexical': self._compute_lexical_similarity(text1, text2),
                'structural': self._compute_structural_similarity(text1, text2),
                'numeric': self._compute_numeric_similarity(text1, text2)
            }
            
            # Weight the scores based on their reliability and importance
            weights = {
                'semantic': 0.4,    # Semantic similarity (most important)
                'lexical': 0.3,     # Lexical/TF-IDF similarity
                'structural': 0.2,  # Structure and pattern similarity
                'numeric': 0.1      # Numeric value similarity
            }
            
            # Calculate weighted average
            final_score = sum(score * weights[key] for key, score in scores.items())
            
            # Normalize to [0, 1] range
            return max(0.0, min(1.0, final_score))
            
        except Exception as e:
            logger.error(f"Error in compute_similarity: {str(e)}")
            return 0.0

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        try:
            # Convert to lowercase
            text = text.lower()
            
            # Normalize whitespace
            text = ' '.join(text.split())
            
            # Normalize legal terms
            text = self.normalize_legal_terms(text)
            
            # Remove punctuation except in numbers and currency
            text = re.sub(r'(?<![\d$€£¥])([^\w\s]|_)(?![\d])', ' ', text)
            
            # Normalize numbers and currency
            text = self._normalize_numbers(text)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error in _normalize_text: {str(e)}")
            return text

    def _normalize_numbers(self, text: str) -> str:
        """Normalize numbers and currency values."""
        try:
            # Normalize currency symbols
            text = re.sub(r'[$€£¥]', 'CUR', text)
            
            # Normalize number formats (e.g., 1,000,000 -> 1000000)
            text = re.sub(r'(\d),(\d)', r'\1\2', text)
            
            # Normalize decimal points
            text = re.sub(r'(\d)\.(\d)', r'\1DOT\2', text)
            
            # Normalize percentage values
            text = re.sub(r'(\d+)%', r'\1PERCENT', text)
            
            return text
            
        except Exception as e:
            logger.error(f"Error in _normalize_numbers: {str(e)}")
            return text

    def _compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity using SBERT."""
        try:
            # Generate embeddings
            embeddings = self.similarity_model.encode([text1, text2])
            
            # Calculate cosine similarity
            similarity = float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0])
            
            return similarity
            
        except Exception as e:
            logger.error(f"Error in _compute_semantic_similarity: {str(e)}")
            return 0.0

    def _compute_lexical_similarity(self, text1: str, text2: str) -> float:
        """Compute lexical similarity using TF-IDF and additional metrics."""
        try:
            # TF-IDF similarity
            tfidf_matrix = self.tfidf.fit_transform([text1, text2])
            tfidf_sim = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
            
            # Jaccard similarity for word sets
            words1 = set(text1.split())
            words2 = set(text2.split())
            jaccard_sim = len(words1.intersection(words2)) / len(words1.union(words2)) if words1 or words2 else 0.0
            
            # Combine similarities with weights
            combined_sim = (0.7 * tfidf_sim) + (0.3 * jaccard_sim)
            
            return combined_sim
            
        except Exception as e:
            logger.error(f"Error in _compute_lexical_similarity: {str(e)}")
            return 0.0

    def _compute_structural_similarity(self, text1: str, text2: str) -> float:
        """Compute structural similarity based on patterns and organization."""
        try:
            # Define structural patterns to compare
            patterns = {
                'sections': r'(?m)^\d+\.',
                'lists': r'(?m)^[\s]*[•\-\*]\s',
                'references': r'(?i)section|clause|article\s+\d+',
                'definitions': r'(?i)"[^"]+" means',
                'dates': r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
                'amounts': r'CUR\s*\d+'
            }
            
            similarity_scores = []
            
            for pattern_type, pattern in patterns.items():
                # Find matches in both texts
                matches1 = set(re.findall(pattern, text1))
                matches2 = set(re.findall(pattern, text2))
                
                if matches1 or matches2:
                    # Calculate Jaccard similarity for this pattern
                    if matches1 and matches2:
                        score = len(matches1.intersection(matches2)) / len(matches1.union(matches2))
                        similarity_scores.append(score)
            
            # Return average similarity if scores exist, otherwise 0
            return sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
            
        except Exception as e:
            logger.error(f"Error in _compute_structural_similarity: {str(e)}")
            return 0.0

    def _compute_numeric_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity based on numeric values and patterns."""
        try:
            # Extract numeric values with context
            numeric_patterns = {
                'currency': r'CUR\s*\d+(?:DOT\d+)?',
                'percentage': r'\d+PERCENT',
                'dates': r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
                'quantities': r'\b\d+\s*(?:days?|months?|years?|hours?)\b'
            }
            
            similarity_scores = []
            
            for value_type, pattern in numeric_patterns.items():
                values1 = re.findall(pattern, text1)
                values2 = re.findall(pattern, text2)
                
                if values1 or values2:
                    if values1 and values2:
                        # Compare sets of values
                        common_values = set(values1).intersection(set(values2))
                        all_values = set(values1).union(set(values2))
                        score = len(common_values) / len(all_values)
                        similarity_scores.append(score)
            
            return sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
            
        except Exception as e:
            logger.error(f"Error in _compute_numeric_similarity: {str(e)}")
            return 0.0

    def extract_parties(self, text: str) -> Dict[str, str]:
        """Extract parties from the contract text."""
        parties = {}
        lines = text.split('\n')
        
        # Look for party information in different formats
        for i, line in enumerate(lines):
            if any(marker in line.lower() for marker in ['parties:', 'between:', 'agreement between']):
                # Look at next few lines for party information
                for j in range(i, min(i + 5, len(lines))):
                    party_line = lines[j].strip()
                    if ':' in party_line:
                        role, name = party_line.split(':', 1)
                        parties[role.strip()] = name.strip()
                    elif 'and' in party_line:
                        parts = party_line.split('and')
                        if len(parts) == 2:
                            parties['Party 1'] = parts[0].strip()
                            parties['Party 2'] = parts[1].strip()
                break
        
        return parties

    def generate_recommendations(self, comparison_results: Dict) -> List[Dict]:
        """Generate recommendations with actionable insights."""
        try:
            recommendations = []
            
            # Handle critical clause issues first
            if 'critical_clause_analysis' in comparison_results:
                for missing in comparison_results['critical_clause_analysis']['missing_critical']:
                    recommendations.append({
                        'text': f"Critical {missing['type']} clause is missing",
                        'details': {
                            'expected': missing['expected'],
                            'impact': 'High risk - Essential clause missing',
                            'action': 'Add this required clause immediately'
                        },
                        'priority': 'High',
                        'category': 'Critical'
                    })
                
                for modified in comparison_results['critical_clause_analysis']['modified_critical']:
                    recommendations.append({
                        'text': f"Critical {modified['type']} clause has significant differences",
                        'details': {
                            'expected': modified['expected'],
                            'actual': modified['actual'],
                            'impact': 'High risk - Critical terms mismatch',
                            'action': 'Review and align with expected terms'
                        },
                        'priority': 'High',
                        'category': 'Critical'
                    })
            
            # Handle clause-specific recommendations
            clause_recommendations = {}
            
            # Process mismatches
            for mismatch in comparison_results.get('mismatches', []):
                if 'expected_clause' in mismatch:
                    clause_num = mismatch['expected_clause'].get('number', '')
                    if clause_num not in clause_recommendations:
                        clause_recommendations[clause_num] = []
                    
                    clause_recommendations[clause_num].append({
                        'text': f"Missing {mismatch['expected_clause'].get('category', 'general')} clause",
                        'details': {
                            'expected': mismatch['expected_clause']['text'],
                            'impact': 'Required clause not found',
                            'action': 'Add this clause to ensure compliance'
                        },
                        'priority': mismatch['expected_clause'].get('importance', 'Medium'),
                        'category': mismatch['expected_clause'].get('category', 'General')
                    })
            
            # Process partial matches
            for partial in comparison_results.get('partial_matches', []):
                clause_num = partial['expected_clause'].get('number', '')
                if clause_num not in clause_recommendations:
                    clause_recommendations[clause_num] = []
                
                clause_recommendations[clause_num].append({
                    'text': f"Modified {partial['expected_clause'].get('category', 'general')} clause",
                    'details': {
                        'expected': partial['expected_clause']['text'],
                        'actual': partial['contract_clause']['text'],
                        'impact': 'Terms differ from expected',
                        'action': 'Review differences and align with expected terms'
                    },
                    'priority': partial['expected_clause'].get('importance', 'Medium'),
                    'category': partial['expected_clause'].get('category', 'General')
                })
            
            # Add all recommendations with proper grouping
            for clause_recs in clause_recommendations.values():
                recommendations.extend(clause_recs)
            
            # Sort recommendations by priority
            priority_order = {'High': 0, 'Medium': 1, 'Low': 2}
            recommendations.sort(key=lambda x: (priority_order[x['priority']], [x['category']]))
            
            return recommendations
            
        except Exception as e:
            print(f"Error in generate_recommendations: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return []

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
        """Check if a clause is critical and return its type and importance."""
        text_lower = text.lower()
        
        for clause_type, info in self.critical_clause_patterns.items():
            for pattern in info['patterns']:
                if re.search(pattern, text_lower):
                    return True, clause_type, info['importance']
        
        return False, '', ''

    def compare_contracts(self, expected_clauses: List[Dict], contract_clauses: List[Dict]) -> Dict:
        """Compare contracts with enhanced analysis and detailed comparison."""
        try:
            # Initialize comprehensive results structure
            results = {
                'summary': {
                    'match_count': 0,
                    'partial_match_count': 0,
                    'mismatch_count': 0,
                    'overall_similarity': 0.0,
                    'risk_level': 'Low',
                    'critical_issues_count': 0
                },
                'matches': [],
                'partial_matches': [],
                'mismatches': [],
                'critical_analysis': {
                    'missing_critical': [],
                    'modified_critical': [],
                    'matched_critical': []
                },
                'section_analysis': {
                    'matched_sections': [],
                    'missing_sections': [],
                    'modified_sections': [],
                    'extra_sections': []
                },
                'risk_analysis': {
                    'high_risk_items': [],
                    'medium_risk_items': [],
                    'low_risk_items': []
                },
                'recommendations': []
            }

            # Track processed clauses
            processed_expected = set()
            processed_contract = set()

            # Step 1: First pass - Match exact and near-exact clauses
            for exp_clause in expected_clauses:
                best_match = None
                best_score = 0.0
                best_analysis = {}

                for cont_clause in contract_clauses:
                    if cont_clause['number'] in processed_contract:
                        continue

                    # Compute comprehensive similarity
                    similarity = self.compute_similarity(exp_clause['text'], cont_clause['text'])
                    
                    # Additional analysis for better matching
                    analysis = self._analyze_clause_differences(exp_clause, cont_clause)
                    
                    # Combine similarity score with analysis results
                    combined_score = self._calculate_combined_score(similarity, analysis)
                    
                    if combined_score > best_score:
                        best_score = combined_score
                        best_match = cont_clause
                        best_analysis = analysis

                # Categorize the match based on score
                if best_score >= 0.85:  # Exact match threshold
                    self._process_exact_match(exp_clause, best_match, best_score, best_analysis, results)
                    processed_expected.add(exp_clause['number'])
                    processed_contract.add(best_match['number'])
                    results['summary']['match_count'] += 1
                elif best_score >= 0.60:  # Partial match threshold
                    self._process_partial_match(exp_clause, best_match, best_score, best_analysis, results)
                    processed_expected.add(exp_clause['number'])
                    processed_contract.add(best_match['number'])
                    results['summary']['partial_match_count'] += 1
                else:
                    self._process_mismatch(exp_clause, best_match, best_score, best_analysis, results)
                    results['summary']['mismatch_count'] += 1

            # Step 2: Process unmatched contract clauses
            for cont_clause in contract_clauses:
                if cont_clause['number'] not in processed_contract:
                    self._process_extra_clause(cont_clause, results)

            # Step 3: Critical clause analysis
            self._analyze_critical_clauses(expected_clauses, contract_clauses, results)

            # Step 4: Risk assessment
            self._assess_risks(results)

            # Step 5: Generate recommendations
            self._generate_recommendations(results)

            # Step 6: Calculate overall metrics
            self._calculate_overall_metrics(results)

            return results

        except Exception as e:
            logger.error(f"Error in compare_contracts: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._generate_error_results()

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

            return changes
        except Exception as e:
            logger.error(f"Error in _compare_sentence_structures: {str(e)}")
            return changes

    def _compare_numeric_values(self, text1: str, text2: str) -> List[Dict]:
        """Compare numeric values between clauses."""
        changes = []
        try:
            # Extract numeric values with context
            patterns = {
                'amount': r'(?:USD|€|£|\$)\s*\d+(?:,\d{3})*(?:\.\d{2})?',
                'percentage': r'\d+(?:\.\d+)?%',
                'duration': r'\d+\s*(?:day|week|month|year)s?',
                'date': r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}'
            }

            for value_type, pattern in patterns.items():
                values1 = re.findall(pattern, text1)
                values2 = re.findall(pattern, text2)

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
                'missing_critical': [],
                'modified_critical': [],
                'matched_critical': []
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
            match_info = {
                'expected_clause': exp_clause,
                'contract_clause': cont_clause,
                'similarity_score': score,
                'analysis': analysis,
                'changes': []
            }

            # Check for minor variations even in exact matches
            if analysis['structural_changes'] or analysis['numeric_changes']:
                match_info['changes'].append({
                    'type': 'warning',
                    'message': 'Minor variations detected in exact match',
                    'details': {
                        'structural': analysis['structural_changes'],
                        'numeric': analysis['numeric_changes']
                    }
                })

            results['matches'].append(match_info)
            results['section_analysis']['matched_sections'].append({
                'title': exp_clause.get('title', ''),
                'number': exp_clause.get('number', ''),
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

    def _generate_recommendations(self, results: Dict) -> None:
        """Generate recommendations based on comparison results."""
        try:
            recommendations = []

            # Critical clause recommendations
            for missing in results['critical_analysis']['missing_critical']:
                recommendations.append({
                    'priority': 'High',
                    'type': 'critical_clause',
                    'message': f"Add missing critical clause: {missing.get('type', 'Unknown')}",
                    'details': missing
                })

            # Modified clause recommendations
            for modified in results['critical_analysis']['modified_critical']:
                recommendations.append({
                    'priority': 'High',
                    'type': 'modified_clause',
                    'message': f"Review modifications in critical clause: {modified.get('type', 'Unknown')}",
                    'details': modified
                })

            # Numeric value recommendations
            for match in results['partial_matches']:
                for change in match.get('analysis', {}).get('numeric_changes', []):
                    if change.get('severity') == 'High':
                        recommendations.append({
                            'priority': 'High',
                            'type': 'numeric_change',
                            'message': f"Review numeric value change in section {match['expected_clause'].get('number', '')}",
                            'details': change
                        })

            # Structure recommendations
            structure_issues = [
                section for section in results['section_analysis']['modified_sections']
                if any(change.get('type') == 'structure' for change in section.get('changes', []))
            ]
            if structure_issues:
                recommendations.append({
                    'priority': 'Medium',
                    'type': 'structure',
                    'message': 'Review structural changes in modified sections',
                    'details': {'affected_sections': structure_issues}
                })

            results['recommendations'] = sorted(
                recommendations,
                key=lambda x: {'High': 0, 'Medium': 1, 'Low': 2}[x['priority']]
            )

        except Exception as e:
            logger.error(f"Error in _generate_recommendations: {str(e)}")

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
                        })
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
            
            # Adjust score based on analysis
            if analysis['structural_changes']:
                base_score *= 0.9  # 10% penalty for structural changes
                
            if analysis['numeric_changes']:
                base_score *= 0.8  # 20% penalty for numeric changes
                
            if analysis['content_changes']:
                base_score *= 0.85  # 15% penalty for content changes
                
            # Ensure score is between 0 and 1
            return max(0.0, min(1.0, base_score))
            
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
                    'cease', 'conclude'
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

    def _extract_obligations(self, text: str) -> Set[str]:
        """Extract obligations and duties from text."""
        try:
            obligations = set()
            doc = self.nlp(text)
            
            # Common obligation indicators
            obligation_verbs = {
                'shall', 'must', 'will', 'agrees to', 'is required to',
                'is obligated to', 'has duty to', 'is responsible for'
            }
            
            # Extract obligations based on modal verbs and indicators
            for token in doc:
                if (token.text.lower() in obligation_verbs or 
                    token.dep_ == 'aux' and token.head.pos_ == 'VERB'):
                    # Get the full verb phrase
                    verb_phrase = ' '.join([t.text for t in token.head.subtree])
                    obligations.add(verb_phrase.strip())
            
            return obligations
            
        except Exception as e:
            logger.error(f"Error in _extract_obligations: {str(e)}")
            return set()