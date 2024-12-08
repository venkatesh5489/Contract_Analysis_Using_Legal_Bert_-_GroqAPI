'use client';

import { DocumentProvider } from '@/contexts/DocumentContext';
import { ComparisonProvider } from '@/contexts/ComparisonContext';
import { Navigation } from '@/components/layout/Navigation';
import './globals.css';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <DocumentProvider>
          <ComparisonProvider>
            <Navigation />
            <main className="min-h-screen bg-gray-50">
              {children}
            </main>
          </ComparisonProvider>
        </DocumentProvider>
      </body>
    </html>
  );
}
