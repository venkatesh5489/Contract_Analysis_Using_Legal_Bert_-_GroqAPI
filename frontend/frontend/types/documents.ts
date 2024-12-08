export interface Document {
  id: string;
  name: string;
  type: 'expected_terms' | 'contract';
  uploadDate: string;
}

export interface DocumentState {
  expectedTerms: Document | null;
  contracts: Document[];
  loading: boolean;
  error: string | null;
} 