import React, { useState } from 'react';
import { ClauseMatch } from '@/types/documents';
import { ChevronDownIcon, ChevronUpIcon, CheckCircleIcon, AlertCircleIcon, XCircleIcon } from 'lucide-react';

interface ClauseComparisonViewProps {
  matches?: ClauseMatch[];
  partialMatches?: ClauseMatch[];
  mismatches?: ClauseMatch[];
  className?: string;
}

export const ClauseComparisonView: React.FC<ClauseComparisonViewProps> = ({
  matches = [],
  partialMatches = [],
  mismatches = [],
  className = '',
}) => {
  const [expandedClause, setExpandedClause] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<'all' | 'matches' | 'partial' | 'mismatches'>('all');

  const totalClauses = (matches?.length || 0) + (partialMatches?.length || 0) + (mismatches?.length || 0);
  if (totalClauses === 0) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Clause Comparison</h3>
          <p className="text-gray-500">No clauses available for comparison.</p>
        </div>
      </div>
    );
  }

  const getFilteredClauses = () => {
    switch (activeFilter) {
      case 'matches':
        return matches || [];
      case 'partial':
        return partialMatches || [];
      case 'mismatches':
        return mismatches || [];
      default:
        return [...(matches || []), ...(partialMatches || []), ...(mismatches || [])];
    }
  };

  const toggleClause = (id: string) => {
    setExpandedClause(expandedClause === id ? null : id);
  };

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-6">Clause Comparison</h3>

        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <button
            onClick={() => setActiveFilter('all')}
            className={`p-4 rounded-lg border ${
              activeFilter === 'all' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
            }`}
          >
            <div className="text-sm text-gray-600">Total Clauses</div>
            <div className="text-2xl font-bold text-gray-900">{totalClauses}</div>
          </button>
          
          <button
            onClick={() => setActiveFilter('matches')}
            className={`p-4 rounded-lg border ${
              activeFilter === 'matches' ? 'border-green-500 bg-green-50' : 'border-gray-200'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">Exact Matches</div>
              <CheckCircleIcon className="h-5 w-5 text-green-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900">{matches?.length || 0}</div>
          </button>
          
          <button
            onClick={() => setActiveFilter('partial')}
            className={`p-4 rounded-lg border ${
              activeFilter === 'partial' ? 'border-yellow-500 bg-yellow-50' : 'border-gray-200'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">Partial Matches</div>
              <AlertCircleIcon className="h-5 w-5 text-yellow-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900">{partialMatches?.length || 0}</div>
          </button>
          
          <button
            onClick={() => setActiveFilter('mismatches')}
            className={`p-4 rounded-lg border ${
              activeFilter === 'mismatches' ? 'border-red-500 bg-red-50' : 'border-gray-200'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">Mismatches</div>
              <XCircleIcon className="h-5 w-5 text-red-500" />
            </div>
            <div className="text-2xl font-bold text-gray-900">{mismatches?.length || 0}</div>
          </button>
        </div>

        {/* Clauses List */}
        <div className="space-y-4">
          {getFilteredClauses().map((clause, index) => {
            if (!clause || !clause.expected_clause || !clause.contract_clause) {
              return null;
            }

            const id = `clause-${index}`;
            const isExpanded = expandedClause === id;
            const matchType = matches?.includes(clause) ? 'match' :
                            partialMatches?.includes(clause) ? 'partial' :
                            'mismatch';

            return (
              <div key={id} className="border rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleClause(id)}
                  className={`w-full px-4 py-3 flex items-center justify-between text-left ${
                    matchType === 'match' ? 'bg-green-50' :
                    matchType === 'partial' ? 'bg-yellow-50' :
                    'bg-red-50'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    {matchType === 'match' ? (
                      <CheckCircleIcon className="h-5 w-5 text-green-600" />
                    ) : matchType === 'partial' ? (
                      <AlertCircleIcon className="h-5 w-5 text-yellow-600" />
                    ) : (
                      <XCircleIcon className="h-5 w-5 text-red-600" />
                    )}
                    <div>
                      <div className="font-medium">
                        {clause.expected_clause?.number ? `Clause ${clause.expected_clause.number}` : 'Unnamed Clause'}
                      </div>
                      <div className="text-sm text-gray-600">
                        Similarity: {clause.similarity_score?.toFixed(1) || '0'}%
                      </div>
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronUpIcon className="h-5 w-5 text-gray-500" />
                  ) : (
                    <ChevronDownIcon className="h-5 w-5 text-gray-500" />
                  )}
                </button>

                {isExpanded && (
                  <div className="p-4 bg-white">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <h4 className="font-medium text-gray-700 mb-2">Expected Clause</h4>
                        <div className="p-3 bg-gray-50 rounded text-sm">
                          {clause.expected_clause?.text || 'No text available'}
                        </div>
                        {clause.expected_clause?.category && (
                          <div className="mt-2 text-sm text-gray-600">
                            Category: {clause.expected_clause.category}
                          </div>
                        )}
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-700 mb-2">Contract Clause</h4>
                        <div className="p-3 bg-gray-50 rounded text-sm">
                          {clause.contract_clause?.text || 'No text available'}
                        </div>
                        {clause.contract_clause?.category && (
                          <div className="mt-2 text-sm text-gray-600">
                            Category: {clause.contract_clause.category}
                          </div>
                        )}
                      </div>
                    </div>

                    {clause.differences && (clause.differences.added?.length > 0 || clause.differences.removed?.length > 0) && (
                      <div className="mt-4">
                        <h4 className="font-medium text-gray-700 mb-2">Differences</h4>
                        <div className="space-y-2">
                          {clause.differences.added?.length > 0 && (
                            <div>
                              <div className="text-sm font-medium text-green-600">Added:</div>
                              <ul className="list-disc list-inside text-sm text-gray-600 pl-4">
                                {clause.differences.added.map((item, i) => (
                                  <li key={i}>{item}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {clause.differences.removed?.length > 0 && (
                            <div>
                              <div className="text-sm font-medium text-red-600">Removed:</div>
                              <ul className="list-disc list-inside text-sm text-gray-600 pl-4">
                                {clause.differences.removed.map((item, i) => (
                                  <li key={i}>{item}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}; 