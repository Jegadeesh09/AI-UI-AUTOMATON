import React from 'react';
import { X, Check, RotateCcw } from 'lucide-react';

const BDDModal = ({ isOpen, bddContent, onApprove, onClose, storyId, viewOnly = false }) => {
  const [editedBDD, setEditedBDD] = React.useState(bddContent);

  React.useEffect(() => {
    setEditedBDD(bddContent);
  }, [bddContent]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 flex justify-center z-[60] p-4">
      <div className="surface w-full max-w-[65vw] rounded-lg shadow-xl border border-zinc-800 flex flex-col max-h-[100vh]">
        <div className="flex justify-between items-center p-6 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold">{viewOnly ? 'View/Edit BDD' : 'Verify BDD Steps'} - {storyId}</h2>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>
        
        <div className="flex-1 min-h-0 overflow-hidden flex flex-col p-6">
          <p className="text-sm text-zinc-400 mb-4">
            Please verify or edit the BDD steps below. Manual corrections can be made before proceeding to script generation.
          </p>
          <textarea 
            className="flex-1 bg-black border border-zinc-800 rounded-lg p-4 text-white font-mono text-sm resize-none focus:outline-none focus:ring-1 focus:ring-white/20 custom-scrollbar"
            value={editedBDD}
            onChange={(e) => setEditedBDD(e.target.value)}
          />
        </div>

        <div className="p-6 flex justify-end gap-3 border-t border-zinc-800">
          <button 
            onClick={onClose} 
            className={`px-4 py-2 text-zinc-400 hover:text-white transition-colors flex items-center gap-2 ${viewOnly ? 'bg-zinc-800 rounded px-6' : ''}`}
          >
            {viewOnly ? 'Close' : 'Cancel'}
          </button>
          {viewOnly ? (
            <button 
              onClick={() => onApprove(editedBDD)} 
              className="px-6 py-2 bg-white text-black font-bold rounded hover:bg-zinc-200 transition-colors flex items-center gap-2"
            >
              <RotateCcw size={18} className="rotate-180" /> Edit & Proceed
            </button>
          ) : (
            <button 
              onClick={() => onApprove(editedBDD)} 
              className="px-6 py-2 bg-white text-black font-bold rounded hover:bg-zinc-200 transition-colors flex items-center gap-2"
            >
              <Check size={18} /> Approve & Generate Script
            </button>
          )}
        </div>
      </div>
      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #3f3f46;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #52525b;
        }
      `}} />
    </div>
  );
};

export default BDDModal;
