import React from 'react';
import { X, Download } from 'lucide-react';

const ExtentReportModal = ({ isOpen, onClose, reportUrl, storyId }) => {
  if (!isOpen) return null;

  const handleDownload = () => {
    window.location.href = `http://localhost:8000/api/download-report/${storyId}`;
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="surface w-full max-w-7xl rounded-lg shadow-xl border border-zinc-800 flex flex-col h-[95vh]">
        <div className="flex justify-between items-center p-4 border-b border-zinc-800 bg-zinc-900/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-white text-black rounded flex items-center justify-center font-bold text-xs">ER</div>
            <h2 className="text-lg font-bold">Extent Report - {storyId}</h2>
          </div>
          <div className="flex items-center gap-4">
            <button 
              onClick={handleDownload}
              className="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-sm font-medium transition-colors flex items-center gap-2"
              title="Download Report"
            >
              <Download size={16} />
              <span>Download HTML</span>
            </button>
            <button onClick={onClose} className="text-zinc-400 hover:text-white transition-colors p-1 hover:bg-zinc-800 rounded">
              <X size={24} />
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-hidden bg-white">
          <iframe 
            src={reportUrl} 
            className="w-full h-full border-none"
            title="Extent Report"
          />
        </div>
      </div>
    </div>
  );
};

export default ExtentReportModal;
