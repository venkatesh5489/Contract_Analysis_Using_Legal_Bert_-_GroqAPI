import React, { useState } from 'react';
import { ComparisonResults, LegalTerms, Differences } from '@/types/documents';
import { BookOpenIcon, ScaleIcon, AlertTriangleIcon, ArrowRightIcon } from 'lucide-react';

interface ContextualAnalysisViewProps {
  results: ComparisonResults;
  className?: string;
}

interface ContextualChange {
  title: string;
  originalContext: string;
  modifiedContext: string;
  type: 'critical' | 'addition' | 'removal' | 'modification' | 'obligation';
}

export const ContextualAnalysisView: React.FC<ContextualAnalysisViewProps> = ({
  results,
  className = '',
}) => {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  // Safely access differences with proper types
  const differences: Differences = results?.differences || {
    legal_terms: {},
    numeric_values: [],
    obligations: [],
    critical_changes: []
  };

  const legal_terms: LegalTerms = differences?.legal_terms || {};

  // Process legal term changes with proper typing
  const legalTermChanges: ContextualChange[] = [
    ...(legal_terms.added || []).map(term => ({
      title: 'New Legal Terms Added',
      originalContext: 'Original contract did not include these terms',
      modifiedContext: term,
      type: 'addition' as const
    })),
    ...(legal_terms.removed || []).map(term => ({
      title: 'Legal Terms Removed',
      originalContext: term,
      modifiedContext: 'Terms removed in the new version',
      type: 'removal' as const
    })),
    ...(legal_terms.modified || []).map(term => ({
      title: 'Legal Terms Modified',
      originalContext: term.original,
      modifiedContext: term.modified,
      type: 'modification' as const
    }))
  ];

  // Process obligation changes with proper typing
  const obligationChanges: ContextualChange[] = differences.obligations.map(obligation => ({
    title: 'Obligation Changes',
    originalContext: obligation.original,
    modifiedContext: obligation.modified,
    type: 'obligation' as const
  }));

  // Process critical changes with proper typing
  const criticalIssues: ContextualChange[] = differences.critical_changes.map(change => ({
    title: change.type,
    originalContext: change.description,
    modifiedContext: `Severity: ${change.severity}`,
    type: 'critical' as const
  }));

  const allChanges: ContextualChange[] = [
    ...legalTermChanges,
    ...obligationChanges,
    ...criticalIssues
  ];

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  if (!results || allChanges.length === 0) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Contextual Analysis</h3>
          <p className="text-gray-500">No contextual changes found between the documents.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-6">Contextual Analysis</h3>
        
        <div className="space-y-4">
          {allChanges.map((change, index) => (
            <div
              key={index}
              className="border rounded-lg overflow-hidden"
            >
              <button
                className={`w-full px-4 py-3 flex items-center justify-between text-left ${
                  change.type === 'critical' ? 'bg-red-50' :
                  change.type === 'addition' ? 'bg-green-50' :
                  change.type === 'removal' ? 'bg-red-50' :
                  'bg-yellow-50'
                }`}
                onClick={() => toggleSection(`change-${index}`)}
              >
                <div className="flex items-center space-x-3">
                  {change.type === 'critical' ? (
                    <AlertTriangleIcon className="h-5 w-5 text-red-600" />
                  ) : change.type === 'addition' ? (
                    <BookOpenIcon className="h-5 w-5 text-green-600" />
                  ) : change.type === 'removal' ? (
                    <BookOpenIcon className="h-5 w-5 text-red-600" />
                  ) : (
                    <ScaleIcon className="h-5 w-5 text-yellow-600" />
                  )}
                  <span className="font-medium">{change.title}</span>
                </div>
                <ArrowRightIcon
                  className={`h-5 w-5 transform transition-transform ${
                    expandedSection === `change-${index}` ? 'rotate-90' : ''
                  }`}
                />
              </button>
              
              {expandedSection === `change-${index}` && (
                <div className="px-4 py-3 bg-white space-y-3">
                  <div>
                    <div className="text-sm font-medium text-gray-500">Original Context</div>
                    <div className="mt-1 text-gray-900">{change.originalContext}</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-500">Modified Context</div>
                    <div className="mt-1 text-gray-900">{change.modifiedContext}</div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}; 