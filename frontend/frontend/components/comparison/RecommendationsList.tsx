import { Card } from '@/components/ui/Card';
import { AlertTriangle, CheckCircle, Info } from 'lucide-react';

interface RecommendationsListProps {
  recommendations: string[];
}

export function RecommendationsList({ recommendations }: RecommendationsListProps) {
  const getRecommendationIcon = (text: string) => {
    if (text.toLowerCase().includes('critical') || text.toLowerCase().includes('high risk')) {
      return <AlertTriangle className="h-5 w-5 text-red-500" />;
    }
    if (text.toLowerCase().includes('suggest') || text.toLowerCase().includes('consider')) {
      return <Info className="h-5 w-5 text-blue-500" />;
    }
    return <CheckCircle className="h-5 w-5 text-green-500" />;
  };

  return (
    <Card>
      <div className="p-6">
        <ul className="space-y-4">
          {recommendations.map((recommendation, index) => (
            <li key={index} className="flex items-start space-x-3">
              <div className="flex-shrink-0 mt-0.5">
                {getRecommendationIcon(recommendation)}
              </div>
              <p className="text-sm text-gray-700">{recommendation}</p>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}