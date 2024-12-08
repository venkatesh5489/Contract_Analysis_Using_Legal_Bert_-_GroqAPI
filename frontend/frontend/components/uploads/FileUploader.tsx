'use client';

import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X } from 'lucide-react';

interface FileUploaderProps {
  maxFiles: number;
  multiple?: boolean;
  onFileSelect: (files: File[]) => void;
  acceptedFileTypes: string[];
}

export function FileUploader({
  maxFiles,
  multiple = false,
  onFileSelect,
  acceptedFileTypes,
}: FileUploaderProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    const validFiles = acceptedFiles.slice(0, maxFiles);
    onFileSelect(validFiles);
  }, [maxFiles, onFileSelect]);

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    maxFiles,
    multiple,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
  });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8
          transition-colors duration-200 cursor-pointer
          ${isDragActive 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
        `}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center">
          <Upload className="h-12 w-12 text-gray-400" />
          <p className="mt-2 text-sm text-gray-600">
            {isDragActive
              ? 'Drop the files here...'
              : 'Drag & drop files here, or click to select'}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Supported formats: {acceptedFileTypes.join(', ')}
          </p>
        </div>
      </div>

      {acceptedFiles.length > 0 && (
        <ul className="space-y-2">
          {acceptedFiles.map((file, index) => (
            <li
              key={index}
              className="flex items-center justify-between p-3 bg-white rounded-lg shadow-sm"
            >
              <div className="flex items-center space-x-3">
                <span className="text-sm text-gray-700">{file.name}</span>
                <span className="text-xs text-gray-500">
                  ({Math.round(file.size / 1024)} KB)
                </span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  const newFiles = acceptedFiles.filter((_, i) => i !== index);
                  onFileSelect(newFiles);
                }}
                className="text-gray-400 hover:text-red-500"
              >
                <X className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}