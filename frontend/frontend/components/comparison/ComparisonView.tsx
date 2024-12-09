import { useComparison } from '@/contexts/ComparisonContext';
import { ComparisonResult } from '@/types/documents';

interface ComparisonViewProps {
  result?: ComparisonResult;
}

export const ComparisonView = ({ result }: ComparisonViewProps) => {
  const { activeResult } = useComparison();
  const comparisonData = result || activeResult;

  if (!comparisonData) {
    return (
      <div className="p-4 text-center">
        <p>No comparison data available</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Comparison Results</h2>
      {/* Add your comparison view UI here */}
    </div>
  );
}; 