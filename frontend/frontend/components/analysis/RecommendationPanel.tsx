import React, { useState } from 'react';

interface ClauseDetails {
  text: string;
  category: string;
  importance: string;
  number: string;
}

interface ComparisonMatch {
  expected_clause: ClauseDetails;
  contract_clause: ClauseDetails;
  similarity_score: number;
  title_match_score?: number;
}

interface ComparisonMismatch {
  expected_clause?: ClauseDetails;
  contract_clause?: ClauseDetails;
  best_similarity_score: number;
  note?: string;
}

interface ComparisonResults {
  matches: ComparisonMatch[];
  partial_matches: ComparisonMatch[];
  mismatches: ComparisonMismatch[];
  match_count: number;
  partial_match_count: number;
  mismatch_count: number;
  section_analysis: {
    matched_sections: Array<{ title: string; similarity: number }>;
    missing_sections: Array<{ title: string }>;
    modified_sections: Array<{ title: string; similarity: number }>;
    extra_sections: Array<{ title: string }>;
  };
}

interface Recommendation {
  type: 'match' | 'partial_match' | 'mismatch';
  details: ComparisonMatch | ComparisonMismatch;
  category: string;
  priority: string;
  text: string;
}

interface RecommendationPanelProps {
  comparisonResults: ComparisonResults;
}

interface RecommendationSectionProps {
  title: string;
  recommendations: Recommendation[];
  isOpen: boolean;
  onToggle: () => void;
}

interface RecommendationCardProps {
  recommendation: Recommendation;
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({ recommendation }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const getImpactText = (type: string, details: ComparisonMatch | ComparisonMismatch): string => {
    if (type === 'match') return 'No significant differences found';
    if (type === 'partial_match') {
      const match = details as ComparisonMatch;
      return `Partial match found (${Math.round(match.similarity_score * 100)}% similarity)`;
    }
    return 'Significant differences or missing content found';
  };

  const getActionText = (type: string): string => {
    if (type === 'match') return 'No action needed';
    if (type === 'partial_match') return 'Review differences and align with expected terms';
    return 'Add or update clause to match expected terms';
  };
  
  return (
    <div className="border-b border-gray-100 last:border-0">
      <div 
        className="p-4 hover:bg-gray-50 transition-colors duration-150 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start space-x-3">
          <span className="text-xl mt-1">
            {recommendation.priority === 'High' ? '🚨' : recommendation.priority === 'Medium' ? '⚡' : '💡'}
          </span>
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              <span
                className={`
                  px-2.5 py-1 rounded-full text-xs font-medium
                  ${recommendation.priority === 'High' 
                    ? 'bg-red-100 text-red-800' 
                    : recommendation.priority === 'Medium'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-green-100 text-green-800'
                  }
                `}
              >
                {recommendation.priority} Priority
              </span>
              <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                {recommendation.category}
              </span>
            </div>
            <div className="text-gray-700 text-sm leading-relaxed">
              <p className="font-medium text-gray-900 mb-1">{recommendation.text}</p>
              {isExpanded && (
                <div className="mt-3 space-y-4 text-sm">
                  {'expected_clause' in recommendation.details && recommendation.details.expected_clause && (
                    <div className="bg-green-50 p-3 rounded-lg">
                      <span className="font-medium text-green-800 block mb-1">Expected Terms:</span>
                      <span className="text-green-700 whitespace-pre-wrap">{recommendation.details.expected_clause.text}</span>
                    </div>
                  )}
                  {'contract_clause' in recommendation.details && recommendation.details.contract_clause && (
                    <div className="bg-blue-50 p-3 rounded-lg">
                      <span className="font-medium text-blue-800 block mb-1">Actual Contract:</span>
                      <span className="text-blue-700 whitespace-pre-wrap">{recommendation.details.contract_clause.text}</span>
                    </div>
                  )}
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="mb-2">
                      <span className="font-medium text-gray-700">Impact: </span>
                      <span className="text-gray-600">{getImpactText(recommendation.type, recommendation.details)}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">Recommended Action: </span>
                      <span className="text-gray-600">{getActionText(recommendation.type)}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
          <span 
            className={`transform transition-transform duration-200 text-gray-400 ${isExpanded ? 'rotate-180' : ''}`}
          >
            ▼
          </span>
        </div>
      </div>
    </div>
  );
};

const RecommendationSection: React.FC<RecommendationSectionProps> = ({
  title,
  recommendations,
  isOpen,
  onToggle,
}) => {
  return (
    <div className="rounded-lg border border-gray-200">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors duration-150 rounded-t-lg"
      >
        <div className="flex items-center space-x-2">
          <span className="text-xl">
            {title === 'Legal' ? '⚖️' : title === 'Financial' ? '💰' : title === 'Critical' ? '🚨' : '🔧'}
          </span>
          <h3 className="font-semibold text-gray-800">
            {title} Recommendations
            <span className="ml-2 text-sm font-medium text-gray-500">
              ({recommendations.length})
            </span>
          </h3>
        </div>
        <span className={`transform transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </button>

      {isOpen && (
        <div className="divide-y divide-gray-100">
          {recommendations.map((rec: Recommendation, index: number) => (
            <RecommendationCard key={index} recommendation={rec} />
          ))}
        </div>
      )}
    </div>
  );
};

export const RecommendationPanel: React.FC<RecommendationPanelProps> = ({
  comparisonResults
}) => {
  // Define all possible categories
  const categories = ['Critical', 'Legal', 'Financial', 'General'];
  const [openSections, setOpenSections] = useState<Record<string, boolean>>(
    categories.reduce((acc, category) => ({ ...acc, [category]: true }), {})
  );

  // Process and transform recommendations
  const processedRecommendations = React.useMemo(() => {
    const processed: Recommendation[] = [];
    
    if (!comparisonResults) {
      return processed;
    }

    // Process matches
    if (Array.isArray(comparisonResults.matches)) {
      comparisonResults.matches.forEach((match) => {
        processed.push({
          type: 'match',
          details: match,
          category: match.expected_clause.category,
          priority: match.expected_clause.importance,
          text: `Matching ${match.expected_clause.category} clause`
        });
      });
    }

    // Process partial matches
    if (Array.isArray(comparisonResults.partial_matches)) {
      comparisonResults.partial_matches.forEach((partial) => {
        processed.push({
          type: 'partial_match',
          details: partial,
          category: partial.expected_clause.category,
          priority: partial.expected_clause.importance,
          text: `Modified ${partial.expected_clause.category} clause`
        });
      });
    }

    // Process mismatches
    if (Array.isArray(comparisonResults.mismatches)) {
      comparisonResults.mismatches.forEach((mismatch) => {
        if (mismatch.expected_clause || mismatch.contract_clause) {
          processed.push({
            type: 'mismatch',
            details: mismatch,
            category: mismatch.expected_clause?.category || mismatch.contract_clause?.category || 'General',
            priority: mismatch.expected_clause?.importance || 'High',
            text: mismatch.note || `Missing ${mismatch.expected_clause?.category || 'General'} clause`
          });
        }
      });
    }

    return processed;
  }, [comparisonResults]);

  // Group recommendations by category
  const groupedRecommendations = React.useMemo(() => {
    return processedRecommendations.reduce((acc, rec) => {
      const category = categories.includes(rec.category) ? rec.category : 'General';
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(rec);
      return acc;
    }, {} as Record<string, Recommendation[]>);
  }, [processedRecommendations, categories]);

  const toggleSection = (category: string) => {
    setOpenSections(prev => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  // If no comparison results, show loading or error state
  if (!comparisonResults) {
    return (
      <div className="bg-white rounded-lg shadow-lg border border-gray-100 p-6">
        <div className="text-center py-8">
          <div className="text-4xl mb-4">⚠️</div>
          <h3 className="text-lg font-medium text-gray-700">No Comparison Data</h3>
          <p className="text-gray-500 mt-2">Please try comparing documents again</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-100 p-6">
      {processedRecommendations.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-4xl mb-4">✨</div>
          <h3 className="text-lg font-medium text-gray-700">All Looking Good!</h3>
          <p className="text-gray-500 mt-2">No recommendations needed</p>
        </div>
      ) : (
        <div className="space-y-4">
          {categories.map(category => (
            groupedRecommendations[category]?.length > 0 && (
              <RecommendationSection
                key={category}
                title={category}
                recommendations={groupedRecommendations[category]}
                isOpen={openSections[category]}
                onToggle={() => toggleSection(category)}
              />
            )
          ))}
        </div>
      )}
    </div>
  );
}; 