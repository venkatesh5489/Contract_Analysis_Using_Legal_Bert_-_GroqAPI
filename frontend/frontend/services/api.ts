import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Store comparison results temporarily
let lastComparisonResult: any = null;

// Helper function to parse dates from API responses
const parseDateString = (dateStr: string | null | undefined): Date | null => {
  if (!dateStr) return null;
  const date = new Date(dateStr);
  return isNaN(date.getTime()) ? null : date;
};

export const documentService = {
  uploadExpectedTerms: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/upload/expected-terms', formData, {
      headers: { 
        'Content-Type': 'multipart/form-data'
      },
    });
    // Parse the response data to ensure dates are handled correctly
    const data = response.data;
    if (data.uploadDate) {
      data.uploadDate = parseDateString(data.uploadDate);
    }
    return data;
  },

  uploadContracts: async (files: File[]) => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    const response = await api.post('/upload/contracts', formData, {
      headers: { 
        'Content-Type': 'multipart/form-data'
      },
    });
    // Parse dates in the response data
    const data = response.data;
    if (data.contracts) {
      data.contracts = data.contracts.map((contract: any) => ({
        ...contract,
        uploadDate: parseDateString(contract.uploadDate)
      }));
    }
    return data;
  },

  getDocumentClauses: async (documentId: string) => {
    const response = await api.get(`/documents/${documentId}/clauses`);
    return response.data;
  },
};

export const comparisonService = {
  compareDocuments: async (sourceDocId: string, targetDocId: string) => {
    try {
      // Make the comparison request
      const response = await api.post('/compare', {
        expected_terms_id: sourceDocId,
        contract_ids: [targetDocId],
      });

      // Log the response for debugging
      console.log('Compare API Response:', response.data);

      // Extract the first comparison from the response
      const comparisons = response.data.comparisons;
      if (!Array.isArray(comparisons) || comparisons.length === 0) {
        throw new Error('No comparison results returned from server');
      }

      const comparison = comparisons[0];
      console.log('Comparison object:', comparison);

      // Get the server-generated comparison ID
      const comparisonId = comparison.comparison_id;
      if (!comparisonId) {
        throw new Error('No comparison ID in server response');
      }

      // Return the comparison with the correct ID
      return {
        ...comparison,
        comparison_id: comparisonId
      };
    } catch (error) {
      console.error('Error in compareDocuments:', error);
      throw error;
    }
  },

  getComparisonResults: async (comparisonId: string | number) => {
    try {
      // Get the stored ID from localStorage
      const storedId = localStorage.getItem('lastComparisonId');
      console.log('Stored ID:', storedId, 'Requested ID:', comparisonId);

      // Use the stored ID if it exists, otherwise use the provided ID
      const finalId = storedId || comparisonId;
      console.log('Using comparison ID:', finalId);

      // Make the API request with the correct endpoint
      const response = await api.get(`/comparison/${finalId}`);
      
      if (!response.data) {
        throw new Error('No comparison data returned from server');
      }

      return response.data;
    } catch (error: any) {
      console.error('Error fetching comparison:', {
        message: error.message,
        status: error.response?.status,
        data: error.response?.data
      });
      throw error;
    }
  }
};

export const adminService = {
  getStatistics: async () => {
    const response = await api.get('/admin/statistics');
    return response.data;
  },

  getRecentActivity: async () => {
    const response = await api.get('/admin/recent-activity');
    return response.data;
  },

  getHighRiskContracts: async () => {
    const response = await api.get('/admin/high-risk-contracts');
    return response.data;
  },
};

export { api }; 