import React from 'react';
import { ComparisonResults } from '@/types/documents';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

interface StatisticalAnalysisViewProps {
  results: ComparisonResults;
  className?: string;
}

export const StatisticalAnalysisView: React.FC<StatisticalAnalysisViewProps> = ({
  results,
  className = '',
}) => {
  // Safely access arrays with fallbacks
  const matches = results?.matches || [];
  const partial_matches = results?.partial_matches || [];
  const mismatches = results?.mismatches || [];
  const component_scores = results?.component_scores || {};
  const differences = results?.differences || {};

  // Calculate metrics
  const totalClauses = matches.length + partial_matches.length + mismatches.length;
  const matchRate = totalClauses > 0 ? (matches.length / totalClauses) * 100 : 0;
  const averageSimilarity = results?.similarity_score || 0;

  // Prepare data for charts
  const matchDistributionData = [
    { name: 'Exact Matches', value: matches.length },
    { name: 'Partial Matches', value: partial_matches.length },
    { name: 'Mismatches', value: mismatches.length },
  ];

  const componentScoresData = [
    {
      name: 'Legal Terms',
      score: component_scores.legal_term_score || 0,
      weight: 40,
    },
    {
      name: 'Numeric Values',
      score: component_scores.numeric_score || 0,
      weight: 25,
    },
    {
      name: 'Obligations',
      score: component_scores.obligation_score || 0,
      weight: 20,
    },
    {
      name: 'Semantic',
      score: component_scores.semantic_score || 0,
      weight: 15,
    },
  ];

  const differenceTypesData = [
    {
      name: 'Legal Terms',
      count: (differences.legal_terms?.added?.length || 0) +
        (differences.legal_terms?.removed?.length || 0) +
        (differences.legal_terms?.modified?.length || 0),
    },
    {
      name: 'Numeric Values',
      count: differences.numeric_values?.length || 0,
    },
    {
      name: 'Obligations',
      count: differences.obligations?.length || 0,
    },
    {
      name: 'Critical Changes',
      count: differences.critical_changes?.length || 0,
    },
  ];

  const COLORS = ['#4CAF50', '#FFC107', '#F44336'];

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-6">Statistical Analysis</h3>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Match Rate</div>
            <div className="text-2xl font-bold text-gray-900">{matchRate.toFixed(1)}%</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Average Similarity</div>
            <div className="text-2xl font-bold text-gray-900">{averageSimilarity.toFixed(1)}%</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Total Clauses</div>
            <div className="text-2xl font-bold text-gray-900">{totalClauses}</div>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Match Distribution */}
          <div className="h-80">
            <h4 className="text-lg font-semibold text-gray-800 mb-4">Match Distribution</h4>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={matchDistributionData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label
                >
                  {matchDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Component Scores */}
          <div className="h-80">
            <h4 className="text-lg font-semibold text-gray-800 mb-4">Component Scores</h4>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={componentScoresData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="score" name="Score" fill="#2196F3" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Difference Types */}
          <div className="h-80 lg:col-span-2">
            <h4 className="text-lg font-semibold text-gray-800 mb-4">Difference Distribution</h4>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={differenceTypesData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="count" name="Number of Changes" fill="#673AB7" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}; 