import { createContext, useContext, useReducer, ReactNode } from 'react';

interface Clause {
  clause: string;
  category: string;
  importance: string;
}

interface ComparisonMatch {
  expected: Clause;
  actual: Clause;
  similarity: number;
}

interface ComparisonMismatch {
  expected: Clause;
  actual: Clause | null;
  similarity: number;
}

interface ComparisonResults {
  matches: ComparisonMatch[];
  mismatches: ComparisonMismatch[];
}

interface Recommendation {
  text: string;
  priority: 'High' | 'Medium' | 'Low';
  category: string;
}

interface ComparisonResult {
  id: string;
  expectedTermsId: string;
  contractId: string;
  matchPercentage: number;
  riskScore: number;
  results: ComparisonResults;
  recommendations: Recommendation[];
}

interface ComparisonState {
  results: ComparisonResult[];
  activeComparison: string | null;
  loading: boolean;
  error: string | null;
}

type ComparisonAction =
  | { type: 'ADD_COMPARISON'; payload: ComparisonResult }
  | { type: 'SET_ACTIVE_COMPARISON'; payload: string }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'CLEAR_COMPARISONS' };

const initialState: ComparisonState = {
  results: [],
  activeComparison: null,
  loading: false,
  error: null,
};

const comparisonReducer = (state: ComparisonState, action: ComparisonAction): ComparisonState => {
  switch (action.type) {
    case 'ADD_COMPARISON':
      const existingIndex = state.results.findIndex(r => r.id === action.payload.id);
      if (existingIndex !== -1) {
        const updatedResults = [...state.results];
        updatedResults[existingIndex] = action.payload;
        return {
          ...state,
          results: updatedResults,
          error: null,
        };
      }
      return {
        ...state,
        results: [...state.results, action.payload],
        error: null,
      };
    case 'SET_ACTIVE_COMPARISON':
      return {
        ...state,
        activeComparison: action.payload,
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
        loading: false,
      };
    case 'CLEAR_COMPARISONS':
      return {
        ...initialState,
      };
    default:
      return state;
  }
};

const ComparisonContext = createContext<{
  state: ComparisonState;
  dispatch: React.Dispatch<ComparisonAction>;
} | null>(null);

export const ComparisonProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(comparisonReducer, initialState);

  return (
    <ComparisonContext.Provider value={{ state, dispatch }}>
      {children}
    </ComparisonContext.Provider>
  );
};

export const useComparison = () => {
  const context = useContext(ComparisonContext);
  if (!context) {
    throw new Error('useComparison must be used within a ComparisonProvider');
  }
  return context;
}; 