'use client';

import React, { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useComparison } from '@/contexts/ComparisonContext';
import { comparisonService } from '@/services/api';
import { ComparisonResultsViewer } from '@/components/analysis/ComparisonResultsViewer';

export default function ComparisonPage() {
  const params = useParams();
  const router = useRouter();
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

        // Try to load the comparison results
        const comparisonResult = await comparisonService.getComparisonResults(urlComparisonId);
        console.log('Loaded comparison result:', comparisonResult);
        
        if (!comparisonResult) {
          throw new Error('No comparison results found');
        }

        // Transform the data for the frontend
        const transformedComparison = {
          id: comparisonResult.comparison_id,
          expectedTermsId: comparisonResult.source_doc_id,
          contractId: comparisonResult.target_doc_id,
          matchPercentage: comparisonResult.match_percentage || 0,
          riskScore: comparisonResult.risk_score || 0,
          results: comparisonResult.results || { matches: [], mismatches: [] },
          recommendations: comparisonResult.recommendations || [],
        };

        console.log('Transformed comparison:', transformedComparison);

        // Update the comparison context
        dispatch({
          type: 'ADD_COMPARISON',
          payload: transformedComparison,
        });
        dispatch({
          type: 'SET_ACTIVE_COMPARISON',
          payload: transformedComparison.id,
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