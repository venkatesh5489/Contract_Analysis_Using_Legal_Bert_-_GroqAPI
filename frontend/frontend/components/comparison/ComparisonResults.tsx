import { Card } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';

interface ComparisonResultsProps {
  data: {
    match_percentage: number;
    risk_score: number;
    results: {
      matches: any[];
      partial_matches: any[];
      mismatches: any[];
    };
  };
}

export function ComparisonResults({ data }: ComparisonResultsProps) {
  return (
    <div className="space-y-6">
      <Card>
        <div className="p-6 space-y-4">
          <div className="space-y-2">
            <h3 className="text-lg font-medium">Match Percentage</h3>
            <Progress value={data.match_percentage} />
            <p className="text-sm text-gray-500">
              {data.match_percentage.toFixed(1)}% of clauses match the expected terms
            </p>
          </div>

          <div className="space-y-2">
            <h3 className="text-lg font-medium">Risk Score</h3>
            <Progress 
              value={data.risk_score} 
              variant={data.risk_score > 70 ? 'destructive' : 'default'}
            />
            <p className="text-sm text-gray-500">
              Risk score: {data.risk_score.toFixed(1)}
            </p>
          </div>
        </div>
      </Card>

      <div className="space-y-4">
        <ClauseSection
          title="Matching Clauses"
          clauses={data.results.matches}
          type="success"
        />
        <ClauseSection
          title="Partial Matches"
          clauses={data.results.partial_matches}
          type="warning"
        />
        <ClauseSection
          title="Mismatches"
          clauses={data.results.mismatches}
          type="error"
        />
      </div>
    </div>
  );
}

function ClauseSection({ 
  title, 
  clauses, 
  type 
}: { 
  title: string; 
  clauses: any[]; 
  type: 'success' | 'warning' | 'error' 
}) {
  const colors = {
    success: 'border-green-200 bg-green-50',
    warning: 'border-yellow-200 bg-yellow-50',
    error: 'border-red-200 bg-red-50',
  };

  return (
    <div className="space-y-2">
      <h4 className="font-medium">{title} ({clauses.length})</h4>
      {clauses.map((item, index) => (
        <div
          key={index}
          className={`p-4 rounded-lg border ${colors[type]}`}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="text-sm font-medium">Expected</p>
              <p className="text-sm mt-1">{item.expected.clause}</p>
            </div>
            <div>
              <p className="text-sm font-medium">Actual</p>
              <p className="text-sm mt-1">{item.actual.clause}</p>
            </div>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            Similarity: {(item.similarity * 100).toFixed(1)}%
          </div>
        </div>
      ))}
    </div>
  );
}