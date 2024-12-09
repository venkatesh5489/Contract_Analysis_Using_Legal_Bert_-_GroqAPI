interface CardProps {
    2|  children: React.ReactNode;
      className?: string;
    }
    
    export function Card({ children, className = '' }: CardProps) {
      return (
        <div className={`bg-white rounded-lg shadow-sm ${className}`}>
          {children}
        </div>
      );
    }