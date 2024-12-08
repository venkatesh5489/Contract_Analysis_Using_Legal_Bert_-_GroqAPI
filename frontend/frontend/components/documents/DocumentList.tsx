import React from 'react';
import { Document } from '@/types/documents';
import { formatDate } from '@/utils/transformers';

interface DocumentListProps {
  contracts: Document[];
}

export function DocumentList({ contracts }: DocumentListProps) {
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
              <div className="text-sm text-gray-500">
                {formatDate(contract.uploadDate)}
              </div>
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