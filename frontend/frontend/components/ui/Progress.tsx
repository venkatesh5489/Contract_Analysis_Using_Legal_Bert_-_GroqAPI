interface ProgressProps {
    value: number;
    variant?: 'default' | 'destructive';
  }
  
  export function Progress({ value, variant = 'default' }: ProgressProps) {
    const bgColor = variant === 'destructive' ? 'bg-red-600' : 'bg-blue-600';
  
    return (
      <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${bgColor} transition-all duration-300 ease-in-out`}
          style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
        />
      </div>
    );
  }