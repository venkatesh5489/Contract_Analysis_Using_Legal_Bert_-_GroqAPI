import axios, { AxiosResponse, AxiosError } from 'axios';
import { Document, ComparisonResult } from '@/types/documents';

interface ErrorResponse {
  message?: string;
  data?: any;
}

interface ApiResponse {
  state: {
    expectedTerms: Document | null;
    contracts: Document[];
    loading: boolean;
    error: string | null;
  };
}

interface ComparisonApiResponse {
  state: {
    comparison: ComparisonResult;
    loading: boolean;
    error: string | null;
  };
}

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<ErrorResponse>) => {
    // Enhanced error logging
    const errorDetails = {
      message: error.response?.data?.message || error.message,
      status: error.response?.status,
      statusText: error.response?.statusText,
      url: error.config?.url,
      method: error.config?.method,
      data: error.config?.data
    };
    console.error('API Error Details:', errorDetails);
    return Promise.reject(error);
  }
);

interface Contract {
  id: string;
  uploadDate: string;
  [key: string]: any;
}

export const apiService = {
  async uploadExpectedTerms(file: File): Promise<ApiResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/upload/expected-terms', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async uploadContracts(files: File[]): Promise<ApiResponse> {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    const response = await api.post('/upload/contracts', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getDocuments(): Promise<Document[]> {
    const response = await api.get('/documents');
    const data = response.data;
    if (data.contracts) {
      data.contracts = data.contracts.map((contract: Contract) => ({
        ...contract,
        uploadDate: parseDateString(contract.uploadDate) || new Date().toISOString()
      }));
    }
    return data;
  },

  async compareContracts(expectedTermsId: string, contractIds: string[]): Promise<ComparisonApiResponse> {
    try {
      console.log('Sending comparison request:', { expected_terms_id: expectedTermsId, contract_ids: contractIds });
      
      const response = await api.post('/compare', {
        expected_terms_id: expectedTermsId,
        contract_ids: contractIds
      }, {
        timeout: 180000,  // 3 minutes
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      console.log('Raw comparison response:', response.data);

      // Transform the backend response to match frontend expected format
      if (response.data.comparisons && response.data.comparisons.length > 0) {
        const comparison = response.data.comparisons[0];
        
        // Transform matches to match frontend format
        const transformedMatches = comparison.results.matches.map((match: any) => ({
          expectedClause: {
            number: parseInt(match.expected_clause.number) || 0,
            text: match.expected_clause.text || ''
          },
          contractClause: {
            number: parseInt(match.contract_clause.number) || 0,
            text: match.contract_clause.text || ''
          },
          similarityScore: parseFloat(match.similarity_score) || 0,
          differences: {
            added: Array.isArray(match.differences?.added) ? match.differences.added : [],
            removed: Array.isArray(match.differences?.removed) ? match.differences.removed : []
          }
        }));

        // Transform partial matches
        const transformedPartialMatches = comparison.results.partial_matches.map((match: any) => ({
          expectedClause: {
            number: parseInt(match.expected_clause.number) || 0,
            text: match.expected_clause.text || ''
          },
          contractClause: {
            number: parseInt(match.contract_clause.number) || 0,
            text: match.contract_clause.text || ''
          },
          similarityScore: parseFloat(match.similarity_score) || 0,
          differences: {
            added: Array.isArray(match.differences?.added) ? match.differences.added : [],
            removed: Array.isArray(match.differences?.removed) ? match.differences.removed : []
          }
        }));

        // Transform mismatches
        const transformedMismatches = comparison.results.mismatches.map((match: any) => ({
          expectedClause: {
            number: parseInt(match.expected_clause.number) || 0,
            text: match.expected_clause.text || ''
          },
          contractClause: {
            number: parseInt(match.contract_clause.number) || 0,
            text: match.contract_clause.text || ''
          },
          similarityScore: parseFloat(match.similarity_score) || 0,
          differences: {
            added: Array.isArray(match.differences?.added) ? match.differences.added : [],
            removed: Array.isArray(match.differences?.removed) ? match.differences.removed : []
          }
        }));

        // Transform critical analysis
        const transformedCriticalAnalysis = {
          missingCritical: comparison.results.critical_analysis?.missing_critical?.map((item: any) => ({
            type: item.type || 'Unknown',
            expected: item.expected || ''
          })) || [],
          modifiedCritical: comparison.results.critical_analysis?.modified_critical?.map((item: any) => ({
            type: item.type || 'Unknown',
            expected: item.expected || '',
            actual: item.actual || '',
            similarity: parseFloat(item.similarity) || 0
          })) || [],
          matchedCritical: comparison.results.critical_analysis?.matched_critical?.map((item: any) => ({
            type: item.type || 'Unknown',
            expected: item.expected || '',
            actual: item.actual || '',
            similarity: parseFloat(item.similarity) || 0
          })) || []
        };

        // Get first clause numbers safely
        const firstExpectedClause = comparison.expected_terms.clauses?.[0] || {};
        const firstContractClause = comparison.contract.clauses?.[0] || {};

        return {
          state: {
            comparison: {
              id: comparison.id.toString(),
              expectedClause: {
                number: parseInt(firstExpectedClause.number) || 0,
                text: firstExpectedClause.text || ''
              },
              contractClause: {
                number: parseInt(firstContractClause.number) || 0,
                text: firstContractClause.text || ''
              },
              riskScore: parseFloat(comparison.risk_score) || 0,
              matchPercentage: parseFloat(comparison.match_percentage) || 0,
              matchedClauses: transformedMatches.length,
              partialMatches: transformedPartialMatches.length,
              mismatches: transformedMismatches.length,
              results: {
                summary: {
                  matchCount: transformedMatches.length,
                  partialMatchCount: transformedPartialMatches.length,
                  mismatchCount: transformedMismatches.length,
                  overallSimilarity: parseFloat(comparison.match_percentage) || 0,
                  riskLevel: comparison.risk_level || 'Medium',
                  criticalIssuesCount: 
                    (transformedCriticalAnalysis.missingCritical.length || 0) +
                    (transformedCriticalAnalysis.modifiedCritical.length || 0)
                },
                matches: transformedMatches,
                partialMatches: transformedPartialMatches,
                mismatches: transformedMismatches,
                criticalAnalysis: transformedCriticalAnalysis
              }
            },
            loading: false,
            error: null
          }
        };
      }

      throw new Error('Invalid comparison response format');
    } catch (error: any) {
      console.error('Error comparing contracts:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });
      throw new Error(error.response?.data?.error || error.message || 'Failed to compare contracts');
    }
  },

  async healthCheck() {
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  },

  async getComparisonResults(comparisonId: string): Promise<any> {
    try {
      console.log('Fetching comparison results for ID:', comparisonId);
      const response = await api.get(`/comparison/${comparisonId}`);
      
      // Log the raw response for debugging
      console.log('Raw comparison API response:', response.data);
      
      // Return the raw response data - we'll transform it in the component
      return response.data;
    } catch (error: any) {
      console.error('Error fetching comparison results:', {
        error,
        response: error.response?.data,
        status: error.response?.status
      });
      
      // Throw a more descriptive error
      if (error.response?.status === 404) {
        throw new Error('Comparison not found');
      }
      throw new Error(error.response?.data?.message || 'Failed to fetch comparison results');
    }
  },
};

function parseDateString(dateString: string): string | null {
  if (!dateString) return null;
  try {
    const date = new Date(dateString);
    return date.toISOString();
  } catch (error) {
    console.error('Error parsing date:', error);
    return null;
  }
}

// Export the service as both default and named export
export const comparisonService = apiService;
export default apiService; 