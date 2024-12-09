import React from 'react';
import { AlertTriangleIcon, CheckCircleIcon, XCircleIcon, AlertCircleIcon } from 'lucide-react';
import { ComparisonResults } from '@/types/documents';

interface RiskAnalysisPanelProps {
  results: ComparisonResults;
  className?: string;
}

interface RiskFactor {
  type: string;
  description: string;
  severity: 'high' | 'medium' | 'low';
}

export const RiskAnalysisPanel: React.FC<RiskAnalysisPanelProps> = ({ results, className = '' }) => {
  // Safely access differences with null checks
  const differences = results?.differences || {};
  const critical_changes = differences?.critical_changes || [];
  const legal_terms = differences?.legal_terms || {};
  const numeric_values = differences?.numeric_values || [];
  const obligations = differences?.obligations || [];

  const getRiskFactors = () => {
    const factors: RiskFactor[] = [];

    // Check critical changes
    if (critical_changes.length > 0) {
      factors.push({
        type: 'Critical Changes',
        description: `${critical_changes.length} critical changes identified`,
        severity: 'high'
      });
    }

    // Check legal terms
    const legalTermChanges = (legal_terms?.added?.length || 0) +
      (legal_terms?.removed?.length || 0) +
      (legal_terms?.modified?.length || 0);

    if (legalTermChanges > 0) {
      factors.push({
        type: 'Legal Term Changes',
        description: `${legalTermChanges} changes to legal terminology`,
        severity: legalTermChanges > 5 ? 'high' : legalTermChanges > 2 ? 'medium' : 'low'
      });
    }

    // Check numeric values
    if (numeric_values.length > 0) {
      factors.push({
        type: 'Numeric Changes',
        description: `${numeric_values.length} changes to numeric values`,
        severity: numeric_values.length > 5 ? 'high' : numeric_values.length > 2 ? 'medium' : 'low'
      });
    }

    // Check obligations
    if (obligations.length > 0) {
      factors.push({
        type: 'Obligation Changes',
        description: `${obligations.length} changes to contractual obligations`,
        severity: obligations.length > 3 ? 'high' : obligations.length > 1 ? 'medium' : 'low'
      });
    }

    return factors;
  };

  const riskFactors = getRiskFactors();
  const riskLevel = results?.risk_level?.toLowerCase() || 'unknown';
  const similarityScore = results?.similarity_score || 0;

  if (!results) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Risk Analysis</h3>
          <p className="text-gray-500">No risk analysis data available.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-6">Risk Analysis</h3>

        {/* Risk Level Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="text-lg font-semibold text-gray-800">Overall Risk Level</h4>
              <p className="text-sm text-gray-600">Based on identified changes and their severity</p>
            </div>
            <div className={`px-4 py-2 rounded-full font-medium ${
              riskLevel === 'high' ? 'bg-red-100 text-red-800' :
              riskLevel === 'medium' ? 'bg-yellow-100 text-yellow-800' :
              riskLevel === 'low' ? 'bg-green-100 text-green-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {riskLevel.charAt(0).toUpperCase() + riskLevel.slice(1)} Risk
            </div>
          </div>

          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${
                riskLevel === 'high' ? 'bg-red-500' :
                riskLevel === 'medium' ? 'bg-yellow-500' :
                'bg-green-500'
              }`}
              style={{ width: `${similarityScore}%` }}
            />
          </div>
        </div>

        {/* Risk Factors */}
        <div className="space-y-4">
          <h4 className="text-lg font-semibold text-gray-800 mb-2">Risk Factors</h4>
          {riskFactors.length > 0 ? (
            riskFactors.map((factor, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border ${
                  factor.severity === 'high' ? 'border-red-200 bg-red-50' :
                  factor.severity === 'medium' ? 'border-yellow-200 bg-yellow-50' :
                  'border-green-200 bg-green-50'
                }`}
              >
                <div className="flex items-start">
                  {factor.severity === 'high' ? (
                    <AlertTriangleIcon className="h-5 w-5 text-red-600 mt-0.5 mr-3" />
                  ) : factor.severity === 'medium' ? (
                    <AlertCircleIcon className="h-5 w-5 text-yellow-600 mt-0.5 mr-3" />
                  ) : (
                    <CheckCircleIcon className="h-5 w-5 text-green-600 mt-0.5 mr-3" />
                  )}
                  <div>
                    <h5 className={`font-medium ${
                      factor.severity === 'high' ? 'text-red-800' :
                      factor.severity === 'medium' ? 'text-yellow-800' :
                      'text-green-800'
                    }`}>
                      {factor.type}
                    </h5>
                    <p className="text-sm text-gray-600 mt-1">{factor.description}</p>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-4 text-gray-500">
              No significant risk factors identified
            </div>
          )}
        </div>

        {/* Recommendations */}
        {results.recommendations && results.recommendations.length > 0 && (
          <div className="mt-8">
            <h4 className="text-lg font-semibold text-gray-800 mb-4">Recommendations</h4>
            <div className="space-y-3">
              {results.recommendations.map((rec, index) => (
                <div key={index} className="flex items-start space-x-3">
                  <div className={`p-1 rounded-full ${
                    rec.priority.toLowerCase() === 'high' ? 'bg-red-100' :
                    rec.priority.toLowerCase() === 'medium' ? 'bg-yellow-100' :
                    'bg-green-100'
                  }`}>
                    {rec.priority.toLowerCase() === 'high' ? (
                      <AlertTriangleIcon className="h-4 w-4 text-red-600" />
                    ) : rec.priority.toLowerCase() === 'medium' ? (
                      <AlertCircleIcon className="h-4 w-4 text-yellow-600" />
                    ) : (
                      <CheckCircleIcon className="h-4 w-4 text-green-600" />
                    )}
                  </div>
                  <div>
                    <h6 className="font-medium text-gray-900">{rec.title}</h6>
                    <p className="text-sm text-gray-600">{rec.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}; 