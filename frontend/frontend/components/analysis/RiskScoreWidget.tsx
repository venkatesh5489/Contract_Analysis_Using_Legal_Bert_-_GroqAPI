import React from 'react';
import { formatPercentage } from '@/utils/transformers';

interface RiskScoreWidgetProps {
  score: number;
  size?: 'small' | 'medium' | 'large';
}

export const RiskScoreWidget: React.FC<RiskScoreWidgetProps> = ({
  score,
  size = 'medium'
}) => {
  const getColorClass = (score: number) => {
    if (score >= 70) return 'text-red-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getSizeClasses = (size: string) => {
    switch (size) {
      case 'small':
        return 'w-20 h-20 text-xl';
      case 'large':
        return 'w-40 h-40 text-4xl';
      default:
        return 'w-32 h-32 text-3xl';
    }
  };

  return (
    <div className="flex flex-col items-center space-y-2">
      <div className={`relative ${getSizeClasses(size)} flex items-center justify-center`}>
        <svg className="transform -rotate-90 w-full h-full">
          <circle
            className="text-gray-200"
            strokeWidth="8"
            stroke="currentColor"
            fill="transparent"
            r="45%"
            cx="50%"
            cy="50%"
          />
          <circle
            className={getColorClass(score)}
            strokeWidth="8"
            strokeDasharray={`${score} 100`}
            strokeLinecap="round"
            stroke="currentColor"
            fill="transparent"
            r="45%"
            cx="50%"
            cy="50%"
          />
        </svg>
        <span className={`absolute ${getColorClass(score)} font-bold`}>
          {formatPercentage(score)}
        </span>
      </div>
      <div className="text-center">
        <h3 className="font-semibold text-gray-900">Risk Score</h3>
        <p className={`text-sm ${getColorClass(score)}`}>
          {score >= 70 ? 'High Risk' : score >= 40 ? 'Medium Risk' : 'Low Risk'}
        </p>
      </div>
    </div>
  );
}; 