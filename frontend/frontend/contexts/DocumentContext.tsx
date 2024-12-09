import { createContext, useContext, useReducer, ReactNode } from 'react';

interface Document {
  id: string;
  name: string;
  type: 'expected_terms' | 'contract';
  uploadDate: Date;
}

interface DocumentState {
  expectedTerms: Document | null;
  contracts: Document[];
  loading: boolean;
  error: string | null;
}

type DocumentAction =
  | { type: 'SET_EXPECTED_TERMS'; payload: Document }
  | { type: 'ADD_CONTRACT'; payload: Document[] }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'CLEAR_DOCUMENTS' };

const initialState: DocumentState = {
  expectedTerms: null,
  contracts: [],
  loading: false,
  error: null,
};

const documentReducer = (state: DocumentState, action: DocumentAction): DocumentState => {
  switch (action.type) {
    case 'SET_EXPECTED_TERMS':
      return {
        ...state,
        expectedTerms: action.payload,
        error: null,
      };
    case 'ADD_CONTRACT':
      return {
        ...state,
        contracts: [...state.contracts, ...action.payload],
        error: null,
      };
    case 'SET_LOADING':
      return {
        ...state,
        loading: action.payload,
      };
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
      };
    case 'CLEAR_DOCUMENTS':
      return {
        ...initialState,
      };
    default:
      return state;
  }
};

const DocumentContext = createContext<{
  state: DocumentState;
  dispatch: React.Dispatch<DocumentAction>;
} | null>(null);

export const DocumentProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(documentReducer, initialState);

  return (
    <DocumentContext.Provider value={{ state, dispatch }}>
      {children}
    </DocumentContext.Provider>
  );
};

export const useDocuments = () => {
  const context = useContext(DocumentContext);
  if (!context) {
    throw new Error('useDocuments must be used within a DocumentProvider');
  }
  return context;
}; 