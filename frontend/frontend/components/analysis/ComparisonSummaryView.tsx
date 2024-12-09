import React from 'react';
import { ComparisonResults } from '@/types/documents';
import {
  CheckCircleIcon,
  AlertTriangleIcon,
  ClockIcon,
  ScaleIcon,
  FileTextIcon,
  AlertCircleIcon,
} from 'lucide-react';

interface ComparisonSummaryViewProps {
  results: ComparisonResults;
  className?: string;
}

interface ExecutiveSummaryCardProps {
  title: string;
  content: string;
  icon: React.ReactNode;
  type: 'success' | 'warning' | 'danger' | 'info';
}

const ExecutiveSummaryCard: React.FC<ExecutiveSummaryCardProps> = ({
  title,
  content,
  icon,
  type,
}) => {
  const getTypeStyles = () => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border-green-200';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200';
      case 'danger':
        return 'bg-red-50 border-red-200';
      case 'info':
        return 'bg-blue-50 border-blue-200';
    }
  };

  return (
    <div className={`border rounded-lg p-4 ${getTypeStyles()}`}>
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">{icon}</div>
        <div>
          <h4 className="font-medium text-gray-900">{title}</h4>
          <p className="mt-1 text-sm text-gray-600">{content}</p>
        </div>
      </div>
    </div>
  );
};

export const ComparisonSummaryView: React.FC<ComparisonSummaryViewProps> = ({
  results,
  className = '',
}) => {
  // Generate summary insights
  const getOverallStatus = () => {
    const similarityScore = results?.similarity_score ?? 0;
    
    if (similarityScore >= 90) {
      return {
        title: 'High Similarity',
        content: 'Documents are highly similar with minimal changes',
        type: 'success' as const,
        icon: <CheckCircleIcon className="h-5 w-5 text-green-600" />,
      };
    } else if (similarityScore >= 70) {
      return {
        title: 'Moderate Changes',
        content: 'Documents have notable differences requiring review',
        type: 'warning' as const,
        icon: <AlertCircleIcon className="h-5 w-5 text-yellow-600" />,
      };
    } else {
      return {
        title: 'Significant Changes',
        content: 'Documents have major differences requiring careful review',
        type: 'danger' as const,
        icon: <AlertTriangleIcon className="h-5 w-5 text-red-600" />,
      };
    }
  };

  const getRiskSummary = () => {
    const criticalCount = results?.differences?.critical_changes?.length ?? 0;
    if (criticalCount > 0) {
      return {
        title: 'Risk Assessment',
        content: `${criticalCount} critical changes identified requiring immediate attention`,
        type: 'danger' as const,
        icon: <AlertTriangleIcon className="h-5 w-5 text-red-600" />,
      };
    }
    return {
      title: 'Risk Assessment',
      content: 'No critical changes identified',
      type: 'success' as const,
      icon: <CheckCircleIcon className="h-5 w-5 text-green-600" />,
    };
  };

  const getTimelineSummary = () => {
    const timelineChanges = results?.differences?.numeric_values?.filter(
      change => change.type === 'date' || change.type === 'duration'
    )?.length ?? 0;
    
    return {
      title: 'Timeline Changes',
      content: `${timelineChanges} changes to dates, durations, or deadlines`,
      type: 'info' as const,
      icon: <ClockIcon className="h-5 w-5 text-blue-600" />,
    };
  };

  const getObligationSummary = () => {
    const obligationChanges = results?.differences?.obligations?.length ?? 0;
    return {
      title: 'Obligation Changes',
      content: `${obligationChanges} changes to contractual obligations`,
      type: 'warning' as const,
      icon: <ScaleIcon className="h-5 w-5 text-yellow-600" />,
    };
  };

  const getLegalTermsSummary = () => {
    const legalChanges = (results?.differences?.legal_terms?.added?.length ?? 0) +
      (results?.differences?.legal_terms?.removed?.length ?? 0) +
      (results?.differences?.legal_terms?.modified?.length ?? 0);
    
    return {
      title: 'Legal Terms',
      content: `${legalChanges} changes to legal terminology and definitions`,
      type: 'info' as const,
      icon: <FileTextIcon className="h-5 w-5 text-blue-600" />,
    };
  };

  const getMatchSummary = () => {
    const matches = results?.matches?.length ?? 0;
    const partialMatches = results?.partial_matches?.length ?? 0;
    const mismatches = results?.mismatches?.length ?? 0;
    
    return {
      title: 'Clause Matching',
      content: `${matches} exact matches, ${partialMatches} partial matches, ${mismatches} mismatches`,
      type: 'info' as const,
      icon: <CheckCircleIcon className="h-5 w-5 text-blue-600" />,
    };
  };

  if (!results) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-500">No comparison results available</p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-xl font-bold text-gray-900">Executive Summary</h3>
            <p className="mt-1 text-sm text-gray-500">
              Overall Similarity: {(results.similarity_score ?? 0).toFixed(1)}%
            </p>
          </div>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${
            (results.risk_level ?? '').toLowerCase() === 'high' ? 'bg-red-100 text-red-800' :
            (results.risk_level ?? '').toLowerCase() === 'medium' ? 'bg-yellow-100 text-yellow-800' :
            'bg-green-100 text-green-800'
          }`}>
            {results.risk_level ?? 'Unknown'} Risk
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ExecutiveSummaryCard {...getOverallStatus()} />
          <ExecutiveSummaryCard {...getRiskSummary()} />
          <ExecutiveSummaryCard {...getTimelineSummary()} />
          <ExecutiveSummaryCard {...getObligationSummary()} />
          <ExecutiveSummaryCard {...getLegalTermsSummary()} />
          <ExecutiveSummaryCard {...getMatchSummary()} />
        </div>

        {/* Key Recommendations */}
        <div className="mt-6">
          <h4 className="text-lg font-semibold text-gray-800 mb-4">Key Recommendations</h4>
          <div className="space-y-3">
            {(results.differences?.critical_changes?.length ?? 0) > 0 && (
              <div className="flex items-start space-x-2 text-red-600">
                <AlertTriangleIcon className="h-5 w-5 mt-0.5" />
                <p>Review {results.differences.critical_changes.length} critical changes immediately</p>
              </div>
            )}
            {(results.differences?.obligations?.length ?? 0) > 0 && (
              <div className="flex items-start space-x-2 text-yellow-600">
                <AlertCircleIcon className="h-5 w-5 mt-0.5" />
                <p>Assess changes to {results.differences.obligations.length} contractual obligations</p>
              </div>
            )}
            {(results.mismatches?.length ?? 0) > 0 && (
              <div className="flex items-start space-x-2 text-blue-600">
                <FileTextIcon className="h-5 w-5 mt-0.5" />
                <p>Review {results.mismatches.length} unmatched clauses</p>
              </div>
            )}
          </div>
        </div>

        {/* Change Summary */}
        {results.change_summary && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="text-lg font-semibold text-gray-800 mb-2">Summary of Changes</h4>
            <p className="text-gray-600">{results.change_summary}</p>
          </div>
        )}
      </div>
    </div>
  );
}; 