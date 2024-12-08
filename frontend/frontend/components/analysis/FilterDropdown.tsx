import React from 'react';
import { CheckIcon } from 'lucide-react';

interface FilterOption {
  value: string;
  label: string;
}

interface FilterDropdownProps {
  isOpen: boolean;
  onToggle: () => void;
  filters: {
    priority: string[];
    category: string[];
  };
  onFilterChange: (type: 'priority' | 'category', value: string) => void;
}

const priorities: FilterOption[] = [
  { value: 'High', label: 'High Priority' },
  { value: 'Medium', label: 'Medium Priority' },
  { value: 'Low', label: 'Low Priority' },
];

const categories: FilterOption[] = [
  { value: 'Legal', label: 'Legal Clauses' },
  { value: 'Financial', label: 'Financial Clauses' },
  { value: 'Operational', label: 'Operational Clauses' },
];

export const FilterDropdown: React.FC<FilterDropdownProps> = ({
  isOpen,
  onToggle,
  filters,
  onFilterChange,
}) => {
  if (!isOpen) return null;

  return (
    <div className="absolute top-full left-0 mt-2 w-64 rounded-lg bg-white shadow-lg border border-gray-200 z-50">
      <div className="p-4">
        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-900 mb-2">Priority</h3>
            <div className="space-y-2">
              {priorities.map((priority) => (
                <label
                  key={priority.value}
                  className="flex items-center space-x-2 text-sm text-gray-700 cursor-pointer"
                  onClick={() => onFilterChange('priority', priority.value)}
                >
                  <div className={`
                    w-4 h-4 border rounded flex items-center justify-center
                    ${filters.priority.includes(priority.value)
                      ? 'bg-blue-500 border-blue-500'
                      : 'border-gray-300'
                    }
                  `}>
                    {filters.priority.includes(priority.value) && (
                      <CheckIcon className="w-3 h-3 text-white" />
                    )}
                  </div>
                  <span>{priority.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-900 mb-2">Category</h3>
            <div className="space-y-2">
              {categories.map((category) => (
                <label
                  key={category.value}
                  className="flex items-center space-x-2 text-sm text-gray-700 cursor-pointer"
                  onClick={() => onFilterChange('category', category.value)}
                >
                  <div className={`
                    w-4 h-4 border rounded flex items-center justify-center
                    ${filters.category.includes(category.value)
                      ? 'bg-blue-500 border-blue-500'
                      : 'border-gray-300'
                    }
                  `}>
                    {filters.category.includes(category.value) && (
                      <CheckIcon className="w-3 h-3 text-white" />
                    )}
                  </div>
                  <span>{category.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 flex justify-end space-x-2">
          <button
            onClick={() => {
              priorities.forEach(p => onFilterChange('priority', p.value));
              categories.forEach(c => onFilterChange('category', c.value));
            }}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Reset
          </button>
          <button
            onClick={onToggle}
            className="px-4 py-2 bg-blue-500 text-white text-sm font-medium rounded-md hover:bg-blue-600"
          >
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}; 