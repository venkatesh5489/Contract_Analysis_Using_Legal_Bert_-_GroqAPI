// components/comparison/ExportButton.tsx
import { Button } from '@/components/ui/Button';
import { Download } from 'lucide-react';

interface ExportButtonProps {
  comparisonData: any;
}

export function ExportButton({ comparisonData }: ExportButtonProps) {
  const handleExport = () => {
    const report = generateReport(comparisonData);
    const blob = new Blob([report], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `comparison-report-${new Date().toISOString()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const generateReport = (data: any) => {
    return `
Contract Analysis Report
Generated: ${new Date().toLocaleString()}

Overall Metrics:
- Match Percentage: ${data.match_percentage.toFixed(1)}%
- Risk Score: ${data.risk_score.toFixed(1)}

Matching Clauses (${data.results.matches.length}):
${data.results.matches.map((m: any) => `- ${m.expected.clause}`).join('\n')}

Partial Matches (${data.results.partial_matches.length}):
${data.results.partial_matches.map((m: any) => 
  `- Expected: ${m.expected.clause}\n  Actual: ${m.actual.clause}`
).join('\n')}

Mismatches (${data.results.mismatches.length}):
${data.results.mismatches.map((m: any) => 
  `- Expected: ${m.expected.clause}\n  Actual: ${m.actual.clause}`
).join('\n')}

Recommendations:
${data.recommendations.map((r: string) => `- ${r}`).join('\n')}
`;
  };

  return (
    <Button onClick={handleExport} variant="outline">
      <Download className="w-4 h-4 mr-2" />
      Export Report
    </Button>
  );
}