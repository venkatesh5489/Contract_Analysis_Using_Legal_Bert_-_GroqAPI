import React from 'react';
import { Document } from '@/types/documents';

interface DocumentListProps {
  contracts: Document[];
}

export function DocumentList({ contracts }: DocumentListProps) {
  if (!contracts || contracts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="text-center text-gray-500">
          No documents uploaded yet
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md">
      <div className="space-y-2">
        {contracts.map((contract) => (
          <div 
            key={contract.id} 
            className="flex items-center justify-between p-4 border-b last:border-b-0 hover:bg-gray-50"
          >
            <div className="flex items-center space-x-4">
              <div className="text-gray-700 font-medium">{contract.name}</div>
            </div>
            <div className="text-sm text-gray-500">
              {contract.type === 'expected_terms' ? 'Expected Terms' : 'Contract'}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
} 