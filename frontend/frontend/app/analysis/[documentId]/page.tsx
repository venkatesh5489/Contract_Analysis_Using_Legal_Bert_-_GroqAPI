'use client';

import { useEffect, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { ClauseCard } from '@/components/analysis/ClauseCard';
import { FileUploader } from '@/components/uploads/FileUploader';

interface Clause {
  text: string;
  category: string;
  importance: string;
}

interface AnalysisPageProps {
  params: Promise<{
    documentId: string;
  }>;
}

export default function AnalysisPage({ params }: AnalysisPageProps) {
  const resolvedParams = use(params);
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [comparing, setComparing] = useState(false);
  const [contracts, setContracts] = useState<File[]>([]);
  const router = useRouter();

  useEffect(() => {
    let mounted = true;

    const fetchClauses = async () => {
      try {
        const response = await api.get(`/documents/${resolvedParams.documentId}/clauses`);
        if (mounted) {
          setClauses(response.data.clauses);
          setLoading(false);
        }
      } catch (err) {
        if (mounted) {
          setError('Failed to load clauses. Please try again.');
          setLoading(false);
          console.error('Error fetching clauses:', err);
        }
      }
    };

    fetchClauses();

    return () => {
      mounted = false;
    };
  }, [resolvedParams.documentId]);

  const handleCompare = async () => {
    if (contracts.length === 0) {
      setError('Please upload at least one contract for comparison');
      return;
    }

    try {
      setComparing(true);
      setError(null);

      // Upload comparison contracts
      const contractsFormData = new FormData();
      contracts.forEach(contract => {
        contractsFormData.append('files', contract);
      });
      
      const contractsResponse = await api.post('/upload/contracts', contractsFormData);
      
      // Start comparison
      const response = await api.post('/compare', {
        expected_terms_id: resolvedParams.documentId,
        contract_ids: contractsResponse.data.contracts.map((c: any) => c.document_id)
      });
      
      // Navigate to comparison results page
      router.push(`/documents/${response.data.comparisons[0].comparison_id}/comparison`);
    } catch (err) {
      setError('Failed to process comparison. Please try again.');
      console.error('Comparison error:', err);
    } finally {
      setComparing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold">Expected Terms Analysis</h1>
          <p className="mt-2 text-gray-600">
            Review the extracted clauses from your expected terms document
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <div className="bg-white rounded-xl shadow-lg p-8">
          <div className="space-y-6">
            {clauses.map((clause, index) => (
              <div key={index} className="border-b border-gray-100 last:border-0 pb-6 last:pb-0">
                <ClauseCard
                  text={clause.text}
                  category={clause.category}
                  importance={clause.importance}
                />
              </div>
            ))}

            {clauses.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                No clauses found in this document.
              </div>
            )}
          </div>
        </div>

        {clauses.length > 0 && (
          <div className="bg-white rounded-xl shadow-lg p-8">
            <h2 className="text-xl font-semibold mb-4">Upload Contracts for Comparison</h2>
            <p className="text-gray-600 mb-6">
              Upload the contracts you want to compare against these expected terms.
            </p>
            
            <FileUploader
              maxFiles={5}
              onFileSelect={setContracts}
              acceptedFileTypes={['.pdf', '.doc', '.docx', '.txt']}
            />

            <div className="mt-6 flex justify-center">
              <button
                onClick={handleCompare}
                disabled={comparing || contracts.length === 0}
                className={`
                  px-8 py-4 rounded-lg font-medium text-white text-lg
                  ${comparing || contracts.length === 0
                    ? 'bg-blue-400 cursor-not-allowed' 
                    : 'bg-blue-600 hover:bg-blue-700'}
                  transition-colors duration-200 shadow-md
                `}
              >
                {comparing ? (
                  <span className="flex items-center">
                    <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white mr-3"></div>
                    Comparing Contracts...
                  </span>
                ) : (
                  'Compare with Selected Contracts'
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}