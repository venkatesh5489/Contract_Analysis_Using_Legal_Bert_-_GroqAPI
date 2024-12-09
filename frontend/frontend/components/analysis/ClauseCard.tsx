import React from 'react';

interface ClauseCardProps {
  text: string;
  category: string;
  importance: string;
}

export const ClauseCard: React.FC<ClauseCardProps> = ({
  text,
  category,
  importance,
}) => {
  const importanceColor = {
    High: 'bg-red-100 text-red-800',
    Medium: 'bg-yellow-100 text-yellow-800',
    Low: 'bg-green-100 text-green-800',
  }[importance] || 'bg-gray-100 text-gray-800';

  const categoryColor = {
    Legal: 'bg-purple-100 text-purple-800',
    Financial: 'bg-blue-100 text-blue-800',
    Operational: 'bg-orange-100 text-orange-800',
  }[category] || 'bg-gray-100 text-gray-800';

  // Split the text into title and content if it contains a colon
  const [title, ...contentParts] = text.split(':');
  const content = contentParts.join(':').trim();
  const hasTitle = text.includes(':') && title.length < 100; // Check if it's a reasonable title length

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex flex-wrap gap-2 mb-4">
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${categoryColor}`}>
          {category}
        </span>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${importanceColor}`}>
          {importance} Priority
        </span>
      </div>
      
      <div className="space-y-2">
        {hasTitle ? (
          <>
            <h3 className="font-bold text-gray-900">{title}:</h3>
            <div className="pl-4 pt-1">
              <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                {content}
              </p>
            </div>
          </>
        ) : (
          <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
            {text}
          </p>
        )}
      </div>
    </div>
  );
}; 