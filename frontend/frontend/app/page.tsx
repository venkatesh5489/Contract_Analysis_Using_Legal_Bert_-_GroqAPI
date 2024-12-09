'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { FileUploader } from '@/components/uploads/FileUploader';
import { DocumentList } from '@/components/documents/DocumentList';
import { ComparisonView } from '@/components/comparison/ComparisonView';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';
import { ErrorMessage } from '@/components/common/ErrorMessage';
import { useDocuments } from '@/contexts/DocumentContext';
import { useComparison } from '@/contexts/ComparisonContext';
import apiService from '@/services/api';
import { validateFile, validateFiles } from '@/utils/validation';
import { DocumentTextIcon, MagnifyingGlassIcon, LightBulbIcon } from '@heroicons/react/24/outline';
import { Debug } from '@/components/common/Debug';

export default function UploadPage() {
  console.log('Rendering UploadPage');
  const router = useRouter();
  const { state, dispatch: documentDispatch } = useDocuments();
  const { dispatch: comparisonDispatch } = useComparison();
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [isComparing, setIsComparing] = useState(false);

  // Add logging to check context values
  console.log('Document state:', state);

  const handleExpectedTermsUpload = async (files: File[]) => {
    if (!files.length) return;
    
    try {
      setUploading(true);
      setError(null);
      const file = files[0];
      
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }

      const response = await apiService.uploadExpectedTerms(file);
      
      // Check if response has the expected structure
      if (response?.state?.expectedTerms) {
        documentDispatch({ 
          type: 'SET_EXPECTED_TERMS', 
          payload: {
            id: response.state.expectedTerms.id,
            name: response.state.expectedTerms.name,
            type: response.state.expectedTerms.type
          }
        });
      } else {
        throw new Error('Invalid response format from server');
      }
      
    } catch (err) {
      console.error('Upload error:', err);
      setError('Failed to upload file. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleContractsUpload = async (files: File[]) => {
    if (!files.length) return;
    
    try {
      setUploading(true);
      setError(null);

      const validationError = validateFiles(files);
      if (validationError) {
        setError(validationError);
        return;
      }

      const response = await apiService.uploadContracts(files);
      
      // Check if response has the expected structure
      if (response?.state?.contracts) {
        documentDispatch({ 
          type: 'ADD_CONTRACT', 
          payload: response.state.contracts.map((contract: any) => ({
            id: contract.id,
            name: contract.name,
            type: contract.type
          }))
        });
      } else {
        throw new Error('Invalid response format from server');
      }

    } catch (err) {
      console.error('Upload error:', err);
      setError('Failed to upload files. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleCompare = async () => {
    if (!state.expectedTerms || state.contracts.length === 0) {
      setError('Please select both expected terms and at least one contract');
      return;
    }

    try {
      setIsComparing(true);
      setError(null);

      console.log('Starting comparison with:', {
        expected_terms_id: state.expectedTerms.id,
        contract_ids: [state.contracts[0].id]
      });

      // Make the comparison request
      const response = await apiService.compareContracts(
        state.expectedTerms.id,
        [state.contracts[0].id]  // Send as array of contract IDs
      );

      console.log('Comparison response:', response);

      if (response?.state?.comparison) {
        // Store the comparison result in context
        comparisonDispatch({
          type: 'SET_COMPARISON_RESULT',
          payload: response.state.comparison
        });

        // Store the ID in localStorage
        localStorage.setItem('lastComparisonId', response.state.comparison.id);

        // Redirect to the comparison results page
        router.push(`/comparison/${response.state.comparison.id}`);
      } else {
        throw new Error('Invalid comparison response format');
      }
      
    } catch (err: any) {
      console.error('Comparison error:', err);
      setError(err.message || 'Failed to create comparison. Please try again.');
    } finally {
      // Always clear the comparing state
      setIsComparing(false);
    }
  };

  // Get all documents for display
  const allDocuments = [
    ...(state.expectedTerms ? [state.expectedTerms] : []),
    ...state.contracts
  ];

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Smart Contract Analyzer</h1>
          <p className="mt-2 text-sm text-gray-600">
            Simply legal document comparisons with AI-powered analysis and recommendations
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center justify-center">
                <DocumentTextIcon className="h-8 w-8 text-blue-500" />
              </div>
              <div className="mt-4 text-center">
                <h3 className="text-lg font-medium text-gray-900">Compare Documents</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Compare multiple contracts against expected terms with detailed AI analysis
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center justify-center">
                <MagnifyingGlassIcon className="h-8 w-8 text-blue-500" />
              </div>
              <div className="mt-4 text-center">
                <h3 className="text-lg font-medium text-gray-900">Extract Insights</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Extract and analyze key clauses with importance categorization
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center justify-center">
                <LightBulbIcon className="h-8 w-8 text-blue-500" />
              </div>
              <div className="mt-4 text-center">
                <h3 className="text-lg font-medium text-gray-900">Get Recommendations</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Get actionable insights and recommendations for contract improvements
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Upload Section */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Start Your Analysis</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Expected Terms Upload */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">Expected Terms</h3>
                <p className="text-sm text-gray-500 mb-4">
                  Upload your standard contract template or expected terms document
                </p>
                <FileUploader
                  maxFiles={1}
                  onFileSelect={handleExpectedTermsUpload}
                  acceptedFileTypes={['.pdf', '.doc', '.docx', '.txt']}
                  multiple={false}
                />
              </div>

              {/* Contracts Upload */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">Contracts for Comparison</h3>
                <p className="text-sm text-gray-500 mb-4">
                  Upload up to 5 contracts to compare
                </p>
                <FileUploader
                  maxFiles={5}
                  onFileSelect={handleContractsUpload}
                  acceptedFileTypes={['.pdf', '.doc', '.docx', '.txt']}
                  multiple={true}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Uploaded Documents Section */}
        <div className="bg-white shadow rounded-lg">
          <div className="p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Uploaded Documents</h2>
            {allDocuments.length > 0 ? (
              <>
                <DocumentList contracts={allDocuments} />
                {state.expectedTerms && state.contracts.length > 0 && (
                  <div className="mt-6 flex justify-center">
                    <button
                      onClick={handleCompare}
                      disabled={isComparing}
                      className={`
                        px-6 py-3 rounded-md text-white font-medium
                        ${isComparing 
                          ? 'bg-blue-400 cursor-not-allowed' 
                          : 'bg-blue-600 hover:bg-blue-700'
                        }
                      `}
                    >
                      {isComparing ? 'Comparing...' : 'Compare Documents'}
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-12">
                <p className="text-gray-500">No documents uploaded yet</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Loading Overlay */}
      {uploading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-4 flex items-center space-x-3">
            <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-blue-600"></div>
            <p className="text-gray-700">Uploading...</p>
          </div>
        </div>
      )}

      {/* Error Toast */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded shadow-lg">
          {error}
        </div>
      )}

      {/* Only show Debug in development */}
      {process.env.NODE_ENV === 'development' && (
        <Debug data={{ state, uploading, error }} />
      )}
    </div>
  );
}