'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileUploader } from '@/components/uploads/FileUploader';
import { DocumentList } from '@/components/documents/DocumentList';
import { useDocuments } from '@/contexts/DocumentContext';
import { useComparison } from '@/contexts/ComparisonContext';
import { documentService, comparisonService } from '@/services/api';
import { validateFile, validateFiles } from '@/utils/validation';
import { DocumentTextIcon, MagnifyingGlassIcon, LightBulbIcon } from '@heroicons/react/24/outline';

export default function UploadPage() {
  const router = useRouter();
  const { state, dispatch: documentDispatch } = useDocuments();
  const { dispatch: comparisonDispatch } = useComparison();
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [isComparing, setIsComparing] = useState(false);

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

      const response = await documentService.uploadExpectedTerms(file);
      documentDispatch({ 
        type: 'SET_EXPECTED_TERMS', 
        payload: {
          id: response.id,
          name: response.name,
          type: response.type,
          uploadDate: response.uploadDate
        }
      });
      
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

      const response = await documentService.uploadContracts(files);
      documentDispatch({ 
        type: 'ADD_CONTRACT', 
        payload: response.contracts.map((contract: any) => ({
          id: contract.id,
          name: contract.name,
          type: contract.type,
          uploadDate: contract.uploadDate
        }))
      });

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
        expectedTermsId: state.expectedTerms.id,
        contractId: state.contracts[0].id
      });

      // Make the comparison request
      const response = await comparisonService.compareDocuments(
        state.expectedTerms.id,
        state.contracts[0].id
      );

      console.log('Comparison response:', response);

      // Get the comparison ID from the response
      const comparisonId = response.comparison_id;
      if (!comparisonId) {
        throw new Error('No comparison ID returned from server');
      }

      console.log('Using comparison ID for redirect:', comparisonId);

      // Store the ID in localStorage
      localStorage.setItem('lastComparisonId', comparisonId.toString());

      // Redirect to the correct comparison page
      router.push(`/comparison/${comparisonId}`);
      
    } catch (err) {
      console.error('Comparison error:', err);
      setError('Failed to create comparison. Please try again.');
    } finally {
      setIsComparing(false);
    }
  };

  // Get all documents for display
  const allDocuments = [
    ...(state.expectedTerms ? [state.expectedTerms] : []),
    ...state.contracts
  ];

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">Smart Contract Analyzer</h1>
        <p className="text-lg text-gray-600">
          Simplify legal document comparisons with AI-powered analysis and recommendations
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div className="bg-white rounded-lg shadow-md p-6 text-center">
          <div className="text-blue-500 mb-4 flex justify-center">
            <DocumentTextIcon className="h-8 w-8" />
          </div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Compare Documents</h3>
          <p className="text-gray-600">
            Compare multiple contracts against expected terms with detailed AI analysis
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 text-center">
          <div className="text-blue-500 mb-4 flex justify-center">
            <MagnifyingGlassIcon className="h-8 w-8" />
          </div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Extract Insights</h3>
          <p className="text-gray-600">
            Extract and analyze key clauses with importance categorization
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6 text-center">
          <div className="text-blue-500 mb-4 flex justify-center">
            <LightBulbIcon className="h-8 w-8" />
          </div>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Get Recommendations</h3>
          <p className="text-gray-600">
            Get actionable insights and recommendations for contract improvements
          </p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-8">
        <h2 className="text-2xl font-semibold text-gray-800 mb-6 text-center">Start Your Analysis</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div>
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Expected Terms</h3>
            <p className="text-gray-600 mb-4">
              Upload your standard contract template or expected terms document
            </p>
            <FileUploader
              maxFiles={1}
              onFileSelect={handleExpectedTermsUpload}
              acceptedFileTypes={['.pdf', '.doc', '.docx', '.txt']}
              multiple={false}
            />
            {!state.expectedTerms && (
              <p className="text-sm text-blue-600 mt-2">
                Please upload an expected terms document first
              </p>
            )}
          </div>

          <div>
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Contracts for Comparison</h3>
            <p className="text-gray-600 mb-4">Upload up to 5 contracts to compare</p>
            <FileUploader
              maxFiles={5}
              onFileSelect={handleContractsUpload}
              acceptedFileTypes={['.pdf', '.doc', '.docx', '.txt']}
              multiple={true}
            />
          </div>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="text-2xl font-semibold text-gray-800 mb-6">Uploaded Documents</h2>
        {allDocuments.length > 0 ? (
          <>
            <DocumentList 
              contracts={allDocuments.map(doc => ({
                ...doc,
                uploadDate: doc.uploadDate.toISOString()
              }))} 
            />
            {state.expectedTerms && state.contracts.length > 0 && (
              <div className="mt-8 flex justify-center">
                <button
                  onClick={handleCompare}
                  disabled={isComparing}
                  className={`
                    px-8 py-4 rounded-lg font-medium text-lg shadow-md transition-colors duration-200
                    ${isComparing 
                      ? 'bg-blue-400 cursor-not-allowed' 
                      : 'bg-blue-600 hover:bg-blue-700 text-white'
                    }
                  `}
                >
                  {isComparing ? (
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white"></div>
                      <span>Comparing Documents...</span>
                    </div>
                  ) : (
                    'Compare Documents'
                  )}
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-12 bg-white rounded-lg shadow-md">
            <p className="text-gray-600">No documents uploaded yet</p>
          </div>
        )}
      </div>

      {uploading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 flex items-center space-x-4">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
            <p className="text-gray-700">Uploading documents...</p>
          </div>
        </div>
      )}

      {error && (
        <div className="fixed top-4 right-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded shadow-lg">
          {error}
        </div>
      )}
    </div>
  );
}