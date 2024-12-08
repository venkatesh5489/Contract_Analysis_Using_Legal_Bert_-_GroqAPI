import axios from 'axios';

export const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadApi = {
  uploadExpectedTerms: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/upload/expected-terms', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  uploadContracts: async (files: File[]) => {
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

  getDocumentClauses: async (documentId: string) => {
    const response = await api.get(`/documents/${documentId}/clauses`);
    return response.data;
  },

  compareContracts: async (expectedTermsId: string, contractIds: string[]) => {
    const response = await api.post('/compare', {
      expected_terms_id: expectedTermsId,
      contract_ids: contractIds,
    });
    return response.data;
  },
};