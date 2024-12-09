'use client';

import React, { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useComparison } from '@/contexts/ComparisonContext';
import { comparisonService } from '@/services/api';
import ComparisonResultsViewer from '@/components/analysis/ComparisonResultsViewer';

interface Recommendation {
  category: string;
  priority: string;
  text: string;
}

interface BackendResponse {
  comparison_id: number;
  source_doc_id: number;
  target_doc_id: number;
  risk_score: number;
  risk_level: string;
  match_percentage: number;
  results: {
    summary: {
      match_count: number;
      partial_match_count: number;
      mismatch_count: number;
      overall_similarity: number;
      critical_issues_count: number;
    };
    matches: Array<{
      expected_clause: { number: number; text: string; };
      contract_clause: { number: number; text: string; };
      similarity_score: number;
      differences: { added: string[]; removed: string[]; };
    }>;
    partial_matches: Array<{
      expected_clause: { number: number; text: string; };
      contract_clause: { number: number; text: string; };
      similarity_score: number;
      differences: { added: string[]; removed: string[]; };
    }>;
    mismatches: Array<{
      expected_clause: { number: number; text: string; };
      contract_clause: { number: number; text: string; };
      similarity_score: number;
      differences: { added: string[]; removed: string[]; };
    }>;
  };
  recommendations: Recommendation[];
}

export default function ComparisonPage() {
  const params = useParams();
  const { state: comparisonState, dispatch } = useComparison();
  const urlComparisonId = params?.comparisonId as string;

  useEffect(() => {
    const loadComparison = async () => {
      if (!urlComparisonId) {
        dispatch({
          type: 'SET_ERROR',
          payload: 'No comparison ID provided',
        });
        return;
      }

      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        dispatch({ type: 'SET_ERROR', payload: null });

        console.log('Loading comparison with ID:', urlComparisonId);

        // Get the comparison results
        const response = await comparisonService.getComparisonResults(urlComparisonId);
        console.log('Received comparison results:', response);

        if (!response || !response.comparison_id) {
          throw new Error('Invalid comparison response format');
        }

        const backendResponse = response as BackendResponse;

        // Transform the data to match the expected format
        const transformedComparison = {
          id: backendResponse.comparison_id.toString(),
          expectedClause: {
            id: backendResponse.source_doc_id.toString(),
            text: backendResponse.results.matches[0]?.expected_clause.text || '',
            number: backendResponse.results.matches[0]?.expected_clause.number || 0
          },
          contractClause: {
            id: backendResponse.target_doc_id.toString(),
            text: backendResponse.results.matches[0]?.contract_clause.text || '',
            number: backendResponse.results.matches[0]?.contract_clause.number || 0
          },
          riskScore: backendResponse.risk_score,
          matchPercentage: backendResponse.match_percentage,
          matchedClauses: backendResponse.results.summary.match_count,
          partialMatches: backendResponse.results.summary.partial_match_count,
          mismatches: backendResponse.results.summary.mismatch_count,
          results: {
            summary: {
              matchCount: backendResponse.results.summary.match_count,
              partialMatchCount: backendResponse.results.summary.partial_match_count,
              mismatchCount: backendResponse.results.summary.mismatch_count,
              overallSimilarity: backendResponse.results.summary.overall_similarity,
              riskLevel: backendResponse.risk_level,
              criticalIssuesCount: backendResponse.results.summary.critical_issues_count
            },
            matches: backendResponse.results.matches.map(match => ({
              expectedClause: {
                number: match.expected_clause.number,
                text: match.expected_clause.text
              },
              contractClause: {
                number: match.contract_clause.number,
                text: match.contract_clause.text
              },
              similarityScore: match.similarity_score,
              differences: match.differences
            })),
            partialMatches: backendResponse.results.partial_matches.map(match => ({
              expectedClause: {
                number: match.expected_clause.number,
                text: match.expected_clause.text
              },
              contractClause: {
                number: match.contract_clause.number,
                text: match.contract_clause.text
              },
              similarityScore: match.similarity_score,
              differences: match.differences
            })),
            mismatches: backendResponse.results.mismatches.map(match => ({
              expectedClause: {
                number: match.expected_clause.number,
                text: match.expected_clause.text
              },
              contractClause: {
                number: match.contract_clause.number,
                text: match.contract_clause.text
              },
              similarityScore: match.similarity_score,
              differences: match.differences
            })),
            criticalAnalysis: {
              missingCritical: backendResponse.recommendations
                .filter((rec: Recommendation) => 
                  rec.category === 'critical_clause' && rec.priority === 'High'
                )
                .map((rec: Recommendation) => ({
                  type: 'missing',
                  expected: rec.text
                })),
              modifiedCritical: [],
              matchedCritical: []
            }
          }
        };

        console.log('Transformed comparison:', transformedComparison);

        // Update the comparison context
        dispatch({
          type: 'SET_COMPARISON_RESULT',
          payload: transformedComparison
        });

      } catch (err) {
        console.error('Error loading comparison:', err);
        const errorMessage = err instanceof Error ? err.message : 'Failed to load comparison results';
        dispatch({
          type: 'SET_ERROR',
          payload: errorMessage,
        });
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    loadComparison();
  }, [urlComparisonId, dispatch]);

  if (comparisonState.loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (comparisonState.error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {comparisonState.error}
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold">Contract Comparison Results</h1>
          <p className="mt-2 text-gray-600">
            Detailed analysis and recommendations
          </p>
        </div>

        <ComparisonResultsViewer />
      </div>
    </div>
  );
} 