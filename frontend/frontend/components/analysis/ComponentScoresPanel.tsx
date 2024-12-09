import React from 'react';
import { ComponentScores } from '@/types/documents';

interface ComponentScoresPanelProps {
  scores?: ComponentScores | null;
  className?: string;
}

interface ScoreCardProps {
  label: string;
  score: number | null | undefined;
  weight: string;
  description: string;
  color: string;
}

const ScoreCard: React.FC<ScoreCardProps> = ({ label, score, weight, description, color }) => {
  // Ensure score is a number for display
  const displayScore = typeof score === 'number' ? score : 0;
  
  return (
    <div className="bg-white rounded-lg shadow p-4 relative overflow-hidden">
      <div className={`absolute top-0 right-0 w-1 h-full ${color}`} />
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <h4 className="font-semibold text-gray-800">{label}</h4>
          <span className="text-sm font-medium text-gray-500">Weight: {weight}</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="text-2xl font-bold">{displayScore.toFixed(1)}%</div>
          <div className="flex-1">
            <div className="h-2 rounded-full bg-gray-200">
              <div 
                className={`h-2 rounded-full ${color}`} 
                style={{ width: `${displayScore}%` }}
              />
            </div>
          </div>
        </div>
        <p className="text-sm text-gray-600">{description}</p>
      </div>
    </div>
  );
};

export const ComponentScoresPanel: React.FC<ComponentScoresPanelProps> = ({ scores, className = '' }) => {
  if (!scores) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center text-gray-500">
            No component scores available
          </div>
        </div>
      </div>
    );
  }

  const scoreComponents = [
    {
      label: 'Legal Terms',
      score: scores.legal_term_score,
      weight: '40%',
      description: 'Analysis of legal terminology and context',
      color: 'bg-blue-500',
    },
    {
      label: 'Numeric Values',
      score: scores.numeric_score,
      weight: '25%',
      description: 'Comparison of dates, amounts, and durations',
      color: 'bg-green-500',
    },
    {
      label: 'Obligations',
      score: scores.obligation_score,
      weight: '20%',
      description: 'Analysis of legal obligations and requirements',
      color: 'bg-purple-500',
    },
    {
      label: 'Semantic',
      score: scores.semantic_score,
      weight: '15%',
      description: 'General meaning and context comparison',
      color: 'bg-orange-500',
    },
  ];

  const calculateWeightedTotal = () => {
    const legalTermScore = typeof scores.legal_term_score === 'number' ? scores.legal_term_score : 0;
    const numericScore = typeof scores.numeric_score === 'number' ? scores.numeric_score : 0;
    const obligationScore = typeof scores.obligation_score === 'number' ? scores.obligation_score : 0;
    const semanticScore = typeof scores.semantic_score === 'number' ? scores.semantic_score : 0;

    return (
      (legalTermScore * 0.4) +
      (numericScore * 0.25) +
      (obligationScore * 0.2) +
      (semanticScore * 0.15)
    );
  };

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-gray-900">Component Scores</h3>
          <div className="text-right">
            <div className="text-sm text-gray-600">Weighted Total</div>
            <div className="text-2xl font-bold text-gray-900">
              {calculateWeightedTotal().toFixed(1)}%
            </div>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {scoreComponents.map((component) => (
            <ScoreCard
              key={component.label}
              {...component}
            />
          ))}
        </div>
      </div>
    </div>
  );
}; 