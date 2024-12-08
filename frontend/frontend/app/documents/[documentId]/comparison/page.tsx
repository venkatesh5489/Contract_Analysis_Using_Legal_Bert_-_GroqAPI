'use client';

import { useEffect } from 'react';
import { useComparison } from '@/contexts/ComparisonContext';
import { useDocuments } from '@/contexts/DocumentContext';
import { comparisonService } from '@/services/api';
import { ComparisonResultsViewer } from '@/components/analysis/ComparisonResultsViewer';
import { useParams } from 'next/navigation';

export default function ComparisonPage() {
  const params = useParams();
  const { state: comparisonState, dispatch } = useComparison();
  const { state: documentState } = useDocuments();

  useEffect(() => {
    const loadComparison = async () => {
      // Get the comparison ID from localStorage instead of URL params
      const comparisonId = localStorage.getItem('lastComparisonId');
      if (!comparisonId) {
        dispatch({
          type: 'SET_ERROR',
          payload: 'No comparison ID found',
        });
        return;
      }

      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        dispatch({ type: 'SET_ERROR', payload: null });
        
        // Check if we already have comparison results
        const existingComparison = comparisonState.results.find(result => 
          result.id === comparisonId
        );

        if (existingComparison) {
          dispatch({
            type: 'SET_ACTIVE_COMPARISON',
            payload: existingComparison.id,
          });
          return;
        }

        // Try to get comparison results from the API
        try {
          const comparisonResult = await comparisonService.getComparisonResults(comparisonId);
          if (!comparisonResult) {
            throw new Error('No comparison results found');
          }

          // Transform the backend data structure to match our frontend types
          const transformedComparison = {
            id: comparisonResult.comparison_id,
            expectedTermsId: comparisonResult.source_doc_id,
            contractId: comparisonResult.target_doc_id,
            matchPercentage: comparisonResult.match_percentage || 0,
            riskScore: comparisonResult.risk_score || 0,
            results: comparisonResult.results || { matches: [], mismatches: [] },
            recommendations: comparisonResult.recommendations || [],
          };

          // Add comparison and set as active
          dispatch({
            type: 'ADD_COMPARISON',
            payload: transformedComparison,
          });
          dispatch({
            type: 'SET_ACTIVE_COMPARISON',
            payload: transformedComparison.id,
          });
        } catch (err) {
          console.error('Error fetching comparison:', err);
          throw new Error('Failed to load comparison results');
        }

      } catch (err) {
        console.error('Error in comparison:', err);
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
  }, [dispatch, comparisonState.results]);

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

  const activeComparison = comparisonState.results.find(result => result.id === comparisonState.activeComparison);

  if (!activeComparison) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded">
          No comparison results available
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