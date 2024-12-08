interface RawClause {
  text: string;
  category: string;
  importance: string;
}

interface FormattedClause {
  title: string;
  content: string;
  category: string;
  importance: string;
}

export const transformClause = (clause: RawClause): FormattedClause => {
  const [title, ...contentParts] = clause.text.split(':');
  const content = contentParts.join(':').trim();

  return {
    title: title.trim(),
    content: content || title,
    category: clause.category,
    importance: clause.importance,
  };
};

export const calculateRiskScore = (matchPercentage: number): number => {
  return 100 - matchPercentage;
};

export const formatPercentage = (value: number): string => {
  return `${Math.round(value)}%`;
};

export const priorityToColor = (priority: string): string => {
  const colors = {
    High: 'red',
    Medium: 'yellow',
    Low: 'green',
  };
  return colors[priority as keyof typeof colors] || 'gray';
};

export const categoryToColor = (category: string): string => {
  const colors = {
    Legal: 'purple',
    Financial: 'blue',
    Operational: 'orange',
  };
  return colors[category as keyof typeof colors] || 'gray';
};

const parseDate = (date: string | Date): Date => {
  if (date instanceof Date) return date;
  // Handle ISO 8601 date string
  const parsedDate = new Date(date);
  if (isNaN(parsedDate.getTime())) {
    throw new Error('Invalid date format');
  }
  return parsedDate;
};

export const formatDate = (date: string | Date | null | undefined): string => {
  if (!date) return 'No date';
  
  try {
    const d = parseDate(date);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }).format(d);
  } catch (error) {
    console.error('Date formatting error:', error);
    return 'Invalid date';
  }
};

export const formatDateTime = (date: string | Date | null | undefined): string => {
  if (!date) return 'No date';

  try {
    const d = parseDate(date);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    }).format(d);
  } catch (error) {
    console.error('DateTime formatting error:', error);
    return 'Invalid date';
  }
}; 