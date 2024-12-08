import { Badge } from '@/components/ui/Badge';

interface ClauseCardProps {
  clause: {
    text: string;
    category: string;
    importance: string;
  };
}

export function ClauseCard({ clause }: ClauseCardProps) {
  const importanceColor = {
    High: 'bg-red-100 text-red-800',
    Medium: 'bg-yellow-100 text-yellow-800',
    Low: 'bg-green-100 text-green-800',
  }[clause.importance] || 'bg-gray-100 text-gray-800';

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 space-y-4">
      <div className="flex items-center justify-between">
        <Badge variant="outline">{clause.category}</Badge>
        <Badge className={importanceColor}>
          {clause.importance} Priority
        </Badge>
      </div>
      
      <div className="text-gray-700 text-sm leading-relaxed">
        {clause.text}
      </div>
    </div>
  );
}