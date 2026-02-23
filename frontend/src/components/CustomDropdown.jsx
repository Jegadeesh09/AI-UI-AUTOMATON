import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, Check } from 'lucide-react';

const CustomDropdown = ({ value, options, onChange, label, placeholder, disabled }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [openUp, setOpenUp] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleToggle = () => {
    if (disabled) return;
    if (!isOpen && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      // If less than 250px below (enough for ~5 items) and more space above
      if (spaceBelow < 250 && spaceAbove > spaceBelow) {
        setOpenUp(true);
      } else {
        setOpenUp(false);
      }
    }
    setIsOpen(!isOpen);
  };

  return (
    <div className={`relative w-full ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`} ref={containerRef}>
      <button
        type="button"
        onClick={handleToggle}
        disabled={disabled}
        className={`w-full bg-zinc-900 border border-zinc-800 rounded p-2 text-white flex justify-between items-center hover:border-zinc-700 transition-colors text-left ${disabled ? 'pointer-events-none' : ''}`}
      >
        <span className="truncate">{value || placeholder || `-- Select ${label} --`}</span>
        <ChevronDown size={16} className={`text-zinc-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      
      {isOpen && (
        <div className={`absolute z-[100] w-full ${openUp ? 'bottom-full mb-1' : 'mt-1'} bg-zinc-900 border border-zinc-800 rounded shadow-2xl overflow-hidden py-1 animate-in fade-in zoom-in-95 duration-100`}>
          <div className="max-h-[200px] overflow-y-auto custom-scrollbar">
            {options.length === 0 && <div className="px-4 py-2 text-sm text-zinc-500 italic">No options available</div>}
            {options.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => {
                  onChange(option);
                  setIsOpen(false);
                }}
                className={`w-full px-4 py-2 text-sm text-left flex items-center justify-between transition-colors
                  ${value === option ? 'bg-zinc-800 text-white' : 'text-zinc-300'}
                  hover:bg-white hover:text-black
                `}
              >
                <span>{option}</span>
                {value === option && <Check size={14} className="text-blue-400" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomDropdown;
