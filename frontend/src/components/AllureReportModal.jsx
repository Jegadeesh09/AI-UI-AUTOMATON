import React from 'react';
import { X, Download } from 'lucide-react';

const AllureReportModal = ({ isOpen, onClose, reportUrl, storyId }) => {
  if (!isOpen) return null;

  const handleDownload = () => {
    window.location.href = `http://localhost:8000/api/download-report/${storyId}`;
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="surface w-full max-w-6xl rounded-lg shadow-xl border border-zinc-800 flex flex-col h-[90vh]">
        <div className="flex justify-between items-center p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold">Allure Report - {storyId}</h2>
          </div>
          <div className="flex items-center gap-4">
            <button 
              onClick={handleDownload}
              className="text-zinc-400 hover:text-white transition-colors flex items-center gap-2 text-sm font-medium"
              title="Download Report"
            >
              <Download size={20} />
              <span>Download</span>
            </button>
            <button onClick={onClose} className="text-zinc-400 hover:text-white transition-colors">
              <X size={24} />
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-hidden bg-white">
          <iframe 
            src={reportUrl} 
            className="w-full h-full border-none"
            title="Allure Report"
          />
        </div>
      </div>
    </div>
  );
};

export default AllureReportModal;
