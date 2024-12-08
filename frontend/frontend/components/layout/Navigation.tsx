import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { HomeIcon, DocumentTextIcon, ChartBarIcon } from '@heroicons/react/24/outline';

export const Navigation: React.FC = () => {
  const pathname = usePathname();

  const isActive = (path: string) => {
    return pathname === path;
  };

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            {/* Logo/Home */}
            <Link 
              href="/"
              className={`inline-flex items-center px-4 py-2 text-sm font-medium ${
                isActive('/') 
                  ? 'text-blue-600 border-b-2 border-blue-600' 
                  : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <HomeIcon className="h-5 w-5 mr-2" />
              Home
            </Link>

            {/* Documents */}
            <Link 
              href="/documents"
              className={`inline-flex items-center px-4 py-2 text-sm font-medium ${
                isActive('/documents') 
                  ? 'text-blue-600 border-b-2 border-blue-600' 
                  : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <DocumentTextIcon className="h-5 w-5 mr-2" />
              Documents
            </Link>
          </div>

          {/* Admin Link */}
          <div className="flex items-center">
            <Link 
              href="/admin"
              className={`inline-flex items-center px-4 py-2 text-sm font-medium rounded-md ${
                isActive('/admin')
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              <ChartBarIcon className="h-5 w-5 mr-2" />
              Admin Dashboard
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}; 