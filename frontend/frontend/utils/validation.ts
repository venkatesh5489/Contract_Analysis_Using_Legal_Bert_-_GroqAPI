export const ALLOWED_FILE_TYPES = ['.pdf', '.doc', '.docx', '.txt'];
export const MAX_FILE_SIZE = 16 * 1024 * 1024; // 16MB

export const validateFile = (file: File): string | null => {
  // Check file size
  if (file.size > MAX_FILE_SIZE) {
    return `File size exceeds ${MAX_FILE_SIZE / (1024 * 1024)}MB limit`;
  }

  // Check file type
  const fileExtension = `.${file.name.split('.').pop()?.toLowerCase()}`;
  if (!ALLOWED_FILE_TYPES.includes(fileExtension)) {
    return `Invalid file type. Please upload PDF, DOC, DOCX, or TXT files.`;
  }

  return null;
};

export const validateFiles = (files: File[]): string | null => {
  // Check number of files
  if (files.length > 5) {
    return 'Maximum 5 files allowed';
  }

  // Check each file
  for (const file of files) {
    const error = validateFile(file);
    if (error) {
      return `${file.name}: ${error}`;
    }
  }

  return null;
};

export const validateComparisonRequest = (
  expectedTermsId: string | null,
  contractIds: string[]
): string | null => {
  if (!expectedTermsId) {
    return 'Expected terms document is required';
  }

  if (contractIds.length === 0) {
    return 'At least one contract is required for comparison';
  }

  if (contractIds.length > 5) {
    return 'Maximum 5 contracts allowed for comparison';
  }

  return null;
}; 