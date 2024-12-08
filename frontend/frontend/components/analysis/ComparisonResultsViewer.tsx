import React, { useState, useMemo, useCallback } from 'react';
import { RiskScoreWidget } from './RiskScoreWidget';
import { RecommendationPanel } from './RecommendationPanel';
import { formatPercentage } from '@/utils/transformers';
import { useComparison } from '@/contexts/ComparisonContext';
import { DownloadIcon, TableIcon, ListIcon, FilterIcon } from 'lucide-react';
import { FilterDropdown } from './FilterDropdown';
import { exportToPdf, exportToExcel } from '@/utils/exportUtils';
import { useDocuments } from '@/contexts/DocumentContext';

interface Clause {
  number: string;
  text: string;
  category: string;
  importance: string;
}

interface ClauseMatch {
  expected_clause: Clause;
  contract_clause: Clause;
  similarity_score: number;
}

interface ClauseMismatch {
  expected_clause?: Clause;
  contract_clause?: Clause;
  best_similarity_score?: number;
  note?: string;
}

interface ComparisonResult {
  comparison_id: number;
  source_doc_id: number;
  target_doc_id: number;
  match_percentage: number;
  risk_score: number;
  results: {
    matches: ClauseMatch[];
    partial_matches: ClauseMatch[];
    mismatches: ClauseMismatch[];
    match_count: number;
    partial_match_count: number;
    mismatch_count: number;
  };
  recommendations: Array<{
    text: string;
    category: string;
    priority: string;
  }>;
}

// Move the function outside of the component to make it available everywhere
const getCategoryBadgeColor = (category: string) => {
  switch (category.toLowerCase()) {
    case 'legal':
      return 'bg-purple-100 text-purple-800';
    case 'financial':
      return 'bg-blue-100 text-blue-800';
    case 'operational':
      return 'bg-orange-100 text-orange-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

const ClauseComparison: React.FC<ClauseMatch> = ({
  expected_clause,
  contract_clause,
  similarity_score
}) => {
  // Extract clause title and content
  const [expectedTitle, ...expectedContentParts] = expected_clause.text.split(':');
  const expectedContent = expectedContentParts.join(':').trim();
  const [actualTitle, ...actualContentParts] = contract_clause?.text.split(':') || [];
  const actualContent = actualContentParts.join(':').trim();

  return (
    <div className="bg-green-50 rounded-lg p-6 border border-green-200">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getCategoryBadgeColor(expected_clause.category)}`}>
            {expected_clause.category}
          </span>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            expected_clause.importance === 'High' ? 'bg-red-100 text-red-800' :
            expected_clause.importance === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
            'bg-green-100 text-green-800'
          }`}>
            {expected_clause.importance} Priority
          </span>
        </div>
        <span className="px-4 py-2 rounded-full text-sm font-bold bg-green-100 text-green-800">
          {formatPercentage(similarity_score * 100)}% Match
        </span>
      </div>

      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        {expected_clause.number}. {expectedTitle.trim()}
      </h3>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <div className="flex items-center mb-2">
            <span className="mr-2">📋</span>
            <h4 className="font-medium text-gray-700">Expected Terms</h4>
          </div>
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            <p className="text-gray-800 whitespace-pre-wrap">{expectedContent}</p>
          </div>
        </div>

        <div>
          <div className="flex items-center mb-2">
            <span className="mr-2">📄</span>
            <h4 className="font-medium text-gray-700">Actual Contract</h4>
          </div>
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            {contract_clause ? (
              <p className="text-gray-800 whitespace-pre-wrap">{actualContent}</p>
            ) : (
              <div className="flex items-center text-red-600">
                <span className="mr-2">⚠️</span>
                <p>Missing in contract</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

interface FilterState {
  priority: string[];
  category: string[];
  view: 'list' | 'table';
  sortBy: 'priority' | 'category' | 'similarity';
}

export const ComparisonResultsViewer: React.FC = () => {
  const { state } = useComparison();
  const { state: documentState } = useDocuments();
  const [filters, setFilters] = useState<FilterState>({
    priority: [],
    category: [],
    view: 'list',
    sortBy: 'priority'
  });
  const [isFilterDropdownOpen, setIsFilterDropdownOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  
  const activeResult = useMemo(() => 
    state.results.find(r => r.id === state.activeComparison),
    [state.results, state.activeComparison]
  );

  const {
    matches,
    partial_matches,
    mismatches,
    recommendations,
    match_percentage,
    risk_score,
    match_count,
    partial_match_count,
    mismatch_count
  } = useMemo(() => {
    if (!activeResult) {
      return {
        matches: [],
        partial_matches: [],
        mismatches: [],
        recommendations: [],
        match_percentage: 0,
        risk_score: 100,
        match_count: 0,
        partial_match_count: 0,
        mismatch_count: 0
      };
    }
    return {
      matches: activeResult.results.matches || [],
      partial_matches: activeResult.results.partial_matches || [],
      mismatches: activeResult.results.mismatches || [],
      recommendations: activeResult.recommendations || [],
      match_percentage: activeResult.match_percentage || 0,
      risk_score: activeResult.risk_score || 100,
      match_count: activeResult.results.match_count || 0,
      partial_match_count: activeResult.results.partial_match_count || 0,
      mismatch_count: activeResult.results.mismatch_count || 0
    };
  }, [activeResult]);

  const handleExport = useCallback(async (format: 'pdf' | 'excel') => {
    try {
      setIsExporting(true);
      const contract = documentState.contracts.find(c => c.id === activeResult?.contractId);
      const documentName = contract?.name || 'contract-analysis';
      const exportData = {
        documentName,
        matchPercentage: match_percentage,
        riskScore: risk_score,
        matches,
        mismatches,
        recommendations,
      };
      if (format === 'pdf') {
        await exportToPdf(exportData);
      } else {
        await exportToExcel(exportData);
      }
    } catch (error) {
      console.error('Export error:', error);
    } finally {
      setIsExporting(false);
    }
  }, [activeResult, documentState.contracts, match_percentage, risk_score, matches, mismatches, recommendations]);

  const handleFilterChange = useCallback((type: 'priority' | 'category', value: string) => {
    setFilters(prev => {
      const currentValues = prev[type];
      const newValues = currentValues.includes(value)
        ? currentValues.filter(v => v !== value)
        : [...currentValues, value];
      return { ...prev, [type]: newValues };
    });
  }, []);

  const filteredMatches = useMemo(() => {
    return [...matches, ...partial_matches].filter(match => {
      const priorityMatch = filters.priority.length === 0 || filters.priority.includes(match.expected_clause.importance);
      const categoryMatch = filters.category.length === 0 || filters.category.includes(match.expected_clause.category);
      return priorityMatch && categoryMatch;
    });
  }, [matches, partial_matches, filters.priority, filters.category]);

  const filteredMismatches = useMemo(() => {
    return mismatches.filter(mismatch => {
      if (!mismatch.expected_clause) return true;
      const priorityMatch = filters.priority.length === 0 || filters.priority.includes(mismatch.expected_clause.importance);
      const categoryMatch = filters.category.length === 0 || filters.category.includes(mismatch.expected_clause.category);
      return priorityMatch && categoryMatch;
    });
  }, [mismatches, filters.priority, filters.category]);

  const sortedMatches = useMemo(() => {
    return [...filteredMatches].sort((a, b) => {
      switch (filters.sortBy) {
        case 'priority':
          return b.expected_clause.importance.localeCompare(a.expected_clause.importance);
        case 'category':
          return a.expected_clause.category.localeCompare(b.expected_clause.category);
        case 'similarity':
          return b.similarity_score - a.similarity_score;
        default:
          return 0;
      }
    });
  }, [filteredMatches, filters.sortBy]);

  const sortedMismatches = useMemo(() => {
    return [...filteredMismatches].sort((a, b) => {
      if (!a.expected_clause || !b.expected_clause) return 0;
      switch (filters.sortBy) {
        case 'priority':
          return b.expected_clause.importance.localeCompare(a.expected_clause.importance);
        case 'category':
          return a.expected_clause.category.localeCompare(b.expected_clause.category);
        case 'similarity':
          return (b.best_similarity_score || 0) - (a.best_similarity_score || 0);
        default:
          return 0;
      }
    });
  }, [filteredMismatches, filters.sortBy]);

  if (!activeResult) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-700">Select a comparison to view results</h2>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Risk Score and Match Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <RiskScoreWidget 
          riskScore={risk_score} 
          matchPercentage={match_percentage}
        />
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Match Analysis</h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-green-600">{match_count}</div>
              <div className="text-sm text-gray-600">Full Matches</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-yellow-600">{partial_match_count}</div>
              <div className="text-sm text-gray-600">Partial Matches</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-red-600">{mismatch_count}</div>
              <div className="text-sm text-gray-600">Mismatches</div>
            </div>
          </div>
        </div>
      </div>

      {/* Recommendations Section */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Detailed analysis and recommendations
          </h2>
          <RecommendationPanel 
            comparisonResults={activeResult?.results || { 
              matches: [], 
              partial_matches: [], 
              mismatches: [],
              match_count: 0,
              partial_match_count: 0,
              mismatch_count: 0,
              section_analysis: {
                matched_sections: [],
                missing_sections: [],
                modified_sections: [],
                extra_sections: []
              }
            }} 
          />
        </div>
      </div>

      {/* Clause Comparison Section */}
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-800">
            Clause Comparison
          </h2>
          <div className="flex space-x-2">
            <button
              onClick={() => handleExport('pdf')}
              disabled={isExporting}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center space-x-2"
            >
              <DownloadIcon size={16} />
              <span>Export PDF</span>
            </button>
            <button
              onClick={() => handleExport('excel')}
              disabled={isExporting}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center space-x-2"
            >
              <DownloadIcon size={16} />
              <span>Export Excel</span>
            </button>
            <button
              onClick={() => setIsFilterDropdownOpen(!isFilterDropdownOpen)}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 flex items-center space-x-2"
            >
              <FilterIcon size={16} />
              <span>Filter</span>
            </button>
            <div className="flex rounded-lg border border-gray-200 overflow-hidden">
              <button
                onClick={() => setFilters(prev => ({ ...prev, view: 'list' }))}
                className={`px-3 py-2 ${filters.view === 'list' ? 'bg-blue-50 text-blue-600' : 'bg-white text-gray-600'}`}
              >
                <ListIcon size={16} />
              </button>
              <button
                onClick={() => setFilters(prev => ({ ...prev, view: 'table' }))}
                className={`px-3 py-2 ${filters.view === 'table' ? 'bg-blue-50 text-blue-600' : 'bg-white text-gray-600'}`}
              >
                <TableIcon size={16} />
              </button>
            </div>
          </div>
        </div>

        {isFilterDropdownOpen && (
          <FilterDropdown
            filters={filters}
            onFilterChange={handleFilterChange}
            onClose={() => setIsFilterDropdownOpen(false)}
          />
        )}

        {/* Matching Clauses */}
        {sortedMatches.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-700">Matching Clauses ({sortedMatches.length})</h3>
            <div className="space-y-4">
              {sortedMatches.map((match, index) => (
                <ClauseComparison key={index} {...match} />
              ))}
            </div>
          </div>
        )}

        {/* Mismatches */}
        {filteredMismatches.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-red-700">Mismatches ({filteredMismatches.length})</h3>
            <div className="space-y-4">
              {filteredMismatches.map((mismatch, index) => (
                mismatch.expected_clause && (
                  <div key={index} className="bg-red-50 border border-red-200 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-2">
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getCategoryBadgeColor(mismatch.expected_clause.category)}`}>
                          {mismatch.expected_clause.category}
                        </span>
                        <span className="px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
                          {mismatch.expected_clause.importance} Priority
                        </span>
                      </div>
                      {mismatch.best_similarity_score && (
                        <span className="px-4 py-2 rounded-full text-sm font-bold bg-red-100 text-red-800">
                          {formatPercentage(mismatch.best_similarity_score * 100)}% Match
                        </span>
                      )}
                    </div>
                    <div className="space-y-4">
                      <div>
                        <h4 className="font-medium text-gray-700 mb-2">Expected Terms:</h4>
                        <div className="bg-white rounded p-4 border border-red-100">
                          <p className="text-gray-800 whitespace-pre-wrap">{mismatch.expected_clause.text}</p>
                        </div>
                      </div>
                      {mismatch.contract_clause && (
                        <div>
                          <h4 className="font-medium text-gray-700 mb-2">Found in Contract:</h4>
                          <div className="bg-white rounded p-4 border border-red-100">
                            <p className="text-gray-800 whitespace-pre-wrap">{mismatch.contract_clause.text}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}; 