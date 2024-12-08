'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileUploader } from '@/components/upload/FileUploader';
import { Button } from '@/components/ui/Button';
import { uploadApi } from '@/lib/api';

export default function UploadPage() {
  const router = useRouter();
  const [expectedTerms, setExpectedTerms] = useState<File | null>(null);
  const [contracts, setContracts] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async () => {
    if (!expectedTerms || contracts.length === 0) {
      setError('Please upload both expected terms and at least one contract');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      // Upload expected terms
      const expectedTermsResult = await uploadApi.uploadExpectedTerms(expectedTerms);
      
      // Upload contracts
      const contractsResult = await uploadApi.uploadContracts(contracts);

      // Navigate to analysis page with the document IDs
      router.push(`/analysis/${expectedTermsResult.document_id}`);
    } catch (err) {
      setError('Failed to upload documents. Please try again.');
      console.error('Upload error:', err);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold">Contract Analysis Platform</h1>
          <p className="mt-2 text-gray-600">
            Upload your contracts for AI-powered analysis and comparison
          </p>
        </div>

        <div className="grid gap-8 md:grid-cols-2">
          {/* Expected Terms Upload */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Expected Terms</h2>
            <FileUploader
              maxFiles={1}
              onFileSelect={(files) => setExpectedTerms(files[0])}
              acceptedFileTypes={['.pdf', '.doc', '.docx', '.txt']}
            />
          </div>

          {/* Contracts Upload */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Contracts for Comparison</h2>
            <p className="text-sm text-gray-500">Upload up to 5 contracts</p>
            <FileUploader
              maxFiles={5}
              multiple
              onFileSelect={setContracts}
              acceptedFileTypes={['.pdf', '.doc', '.docx', '.txt']}
            />
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <div className="flex justify-center">
          <Button
            onClick={handleUpload}
            disabled={isUploading || !expectedTerms || contracts.length === 0}
            className="w-full md:w-auto"
          >
            {isUploading ? 'Uploading...' : 'Upload and Analyze'}
          </Button>
        </div>
      </div>
    </div>
  );
}