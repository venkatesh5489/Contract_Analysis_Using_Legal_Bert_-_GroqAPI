export interface Document {
  id: string;
  name: string;
  type: string;
  content: string;
  clauses: Clause[];
}

export interface Clause {
  number: number;
  text: string;
  category?: string;
  importance?: string;
}

export interface ClauseMatch {
  expected_clause: Clause;
  contract_clause: Clause;
  similarity_score: number;
  differences: {
    added: string[];
    removed: string[];
  };
}

export interface ComponentScores {
  legal_term_score: number;
  numeric_score: number;
  obligation_score: number;
  semantic_score: number;
}

export interface LegalTerms {
  added?: string[];
  removed?: string[];
  modified?: Array<{
    original: string;
    modified: string;
  }>;
}

export interface NumericValue {
  type: string;
  original: string;
  modified: string;
  difference?: string;
}

export interface Obligation {
  type: string;
  original: string;
  modified: string;
}

export interface CriticalChange {
  type: string;
  description: string;
  severity: string;
}

export interface Differences {
  legal_terms: LegalTerms;
  numeric_values: NumericValue[];
  obligations: Obligation[];
  critical_changes: CriticalChange[];
}

export interface ComparisonResults {
  similarity_score: number;
  component_scores: ComponentScores;
  differences: Differences;
  risk_level: string;
  change_summary?: string;
  matches: ClauseMatch[];
  partial_matches: ClauseMatch[];
  mismatches: ClauseMatch[];
  summary: {
    match_count: number;
    partial_match_count: number;
    mismatch_count: number;
    overall_similarity: number;
    risk_level: string;
    critical_issues_count: number;
  };
}

export interface ComparisonResult {
  id: string;
  expected_terms: {
    id: string;
    name: string;
    clauses: Clause[];
  };
  contract: {
    id: string;
    name: string;
    clauses: Clause[];
  };
  match_percentage: number;
  risk_score: number;
  risk_level: string;
  results: ComparisonResults;
  recommendations?: Array<{
    priority: string;
    category: string;
    title: string;
    description: string;
    action: string;
    impact: string;
  }>;
} 