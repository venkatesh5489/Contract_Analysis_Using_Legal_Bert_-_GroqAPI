import React, { useState } from 'react';
import { Differences } from '@/types/documents';
import { ChevronDownIcon, ChevronUpIcon } from 'lucide-react';

interface DifferenceAnalysisViewProps {
  differences: Differences;
  className?: string;
}

export const DifferenceAnalysisView: React.FC<DifferenceAnalysisViewProps> = ({
  differences,
  className = '',
}) => {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  // Calculate counts
  const legalTermsCount = 
    (differences?.legal_terms?.added?.length || 0) +
    (differences?.legal_terms?.removed?.length || 0) +
    (differences?.legal_terms?.modified?.length || 0);
  const numericValuesCount = differences?.numeric_values?.length || 0;
  const obligationsCount = differences?.obligations?.length || 0;
  const criticalChangesCount = differences?.critical_changes?.length || 0;

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  if (!differences || (legalTermsCount === 0 && numericValuesCount === 0 && obligationsCount === 0 && criticalChangesCount === 0)) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Difference Analysis</h3>
          <p className="text-gray-500">No differences found between the documents.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-6">Difference Analysis</h3>
        
        {/* Legal Terms */}
        {legalTermsCount > 0 && (
          <div className="mb-6">
            <button
              className="w-full flex items-center justify-between text-left"
              onClick={() => toggleSection('legal-terms')}
            >
              <div className="flex items-center">
                <span className="text-lg font-semibold text-gray-900">Legal Terms</span>
                <span className="ml-2 px-2 py-1 text-sm bg-blue-100 text-blue-800 rounded-full">
                  {legalTermsCount} changes
                </span>
              </div>
              {expandedSection === 'legal-terms' ? (
                <ChevronUpIcon className="h-5 w-5 text-gray-500" />
              ) : (
                <ChevronDownIcon className="h-5 w-5 text-gray-500" />
              )}
            </button>
            
            {expandedSection === 'legal-terms' && (
              <div className="mt-4 space-y-4">
                {differences.legal_terms.added && differences.legal_terms.added.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-700 mb-2">Added Terms</h4>
                    <ul className="list-disc list-inside space-y-1">
                      {differences.legal_terms.added.map((term, index) => (
                        <li key={index} className="text-green-600">{term}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {differences.legal_terms.removed && differences.legal_terms.removed.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-700 mb-2">Removed Terms</h4>
                    <ul className="list-disc list-inside space-y-1">
                      {differences.legal_terms.removed.map((term, index) => (
                        <li key={index} className="text-red-600">{term}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {differences.legal_terms.modified && differences.legal_terms.modified.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-700 mb-2">Modified Terms</h4>
                    <ul className="list-disc list-inside space-y-1">
                      {differences.legal_terms.modified.map((term, index) => (
                        <li key={index} className="text-yellow-600">
                          <span className="text-gray-600">From: </span>
                          {term.original}
                          <span className="text-gray-600"> → </span>
                          {term.modified}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        
        {/* Numeric Values */}
        {numericValuesCount > 0 && (
          <div className="mb-6">
            <button
              className="w-full flex items-center justify-between text-left"
              onClick={() => toggleSection('numeric-values')}
            >
              <div className="flex items-center">
                <span className="text-lg font-semibold text-gray-900">Numeric Values</span>
                <span className="ml-2 px-2 py-1 text-sm bg-green-100 text-green-800 rounded-full">
                  {numericValuesCount} changes
                </span>
              </div>
              {expandedSection === 'numeric-values' ? (
                <ChevronUpIcon className="h-5 w-5 text-gray-500" />
              ) : (
                <ChevronDownIcon className="h-5 w-5 text-gray-500" />
              )}
            </button>
            
            {expandedSection === 'numeric-values' && (
              <div className="mt-4">
                <ul className="space-y-3">
                  {differences.numeric_values.map((value, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-gray-600">{value.type}:</span>
                      <div>
                        <div className="text-red-600 line-through">{value.original}</div>
                        <div className="text-green-600">{value.modified}</div>
                        {value.difference && (
                          <div className="text-sm text-gray-500">
                            Difference: {value.difference}
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        
        {/* Obligations */}
        {obligationsCount > 0 && (
          <div className="mb-6">
            <button
              className="w-full flex items-center justify-between text-left"
              onClick={() => toggleSection('obligations')}
            >
              <div className="flex items-center">
                <span className="text-lg font-semibold text-gray-900">Obligations</span>
                <span className="ml-2 px-2 py-1 text-sm bg-purple-100 text-purple-800 rounded-full">
                  {obligationsCount} changes
                </span>
              </div>
              {expandedSection === 'obligations' ? (
                <ChevronUpIcon className="h-5 w-5 text-gray-500" />
              ) : (
                <ChevronDownIcon className="h-5 w-5 text-gray-500" />
              )}
            </button>
            
            {expandedSection === 'obligations' && (
              <div className="mt-4">
                <ul className="space-y-4">
                  {differences.obligations.map((obligation, index) => (
                    <li key={index} className="border-l-4 border-purple-200 pl-4">
                      <div className="font-medium text-gray-700">{obligation.type}</div>
                      <div className="mt-1">
                        <div className="text-red-600 line-through">{obligation.original}</div>
                        <div className="text-green-600">{obligation.modified}</div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        
        {/* Critical Changes */}
        {criticalChangesCount > 0 && (
          <div>
            <button
              className="w-full flex items-center justify-between text-left"
              onClick={() => toggleSection('critical-changes')}
            >
              <div className="flex items-center">
                <span className="text-lg font-semibold text-gray-900">Critical Changes</span>
                <span className="ml-2 px-2 py-1 text-sm bg-red-100 text-red-800 rounded-full">
                  {criticalChangesCount} changes
                </span>
              </div>
              {expandedSection === 'critical-changes' ? (
                <ChevronUpIcon className="h-5 w-5 text-gray-500" />
              ) : (
                <ChevronDownIcon className="h-5 w-5 text-gray-500" />
              )}
            </button>
            
            {expandedSection === 'critical-changes' && (
              <div className="mt-4">
                <ul className="space-y-4">
                  {differences.critical_changes.map((change, index) => (
                    <li key={index} className="border-l-4 border-red-300 pl-4">
                      <div className="font-medium text-red-600">{change.type}</div>
                      <div className="mt-1 text-gray-700">{change.description}</div>
                      <div className="mt-1 text-sm text-red-500">Severity: {change.severity}</div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}; 