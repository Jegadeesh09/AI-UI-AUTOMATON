import React from 'react';
import { X, Save } from 'lucide-react';

const ScriptEditorModal = ({ isOpen, onClose, code, onSave, onChange, storyId }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="surface w-full max-w-4xl h-[80vh] rounded-lg shadow-xl border border-zinc-800 flex flex-col">
        <div className="flex justify-between items-center p-6 border-b border-zinc-800 bg-zinc-950/50">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              <span className="text-blue-500 text-sm uppercase tracking-widest font-mono">Script Editor</span>
              <span>{storyId}</span>
            </h2>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>
        
        <div className="flex-1 p-0 bg-black relative">
          <textarea
            className="w-full h-full bg-transparent p-6 text-blue-100 font-mono text-sm resize-none focus:outline-none custom-scrollbar"
            value={code}
            onChange={(e) => onChange(e.target.value)}
            spellCheck="false"
          />
        </div>

        <div className="p-6 flex justify-end gap-3 border-t border-zinc-800 bg-zinc-950/50">
          <button onClick={onClose} className="px-4 py-2 text-zinc-400 hover:text-white transition-colors text-sm">Cancel</button>
          <button 
            onClick={onSave} 
            className="px-6 py-2 bg-white text-black font-bold rounded hover:bg-zinc-200 transition-colors flex items-center gap-2"
          >
            <Save size={18} />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
};

export default ScriptEditorModal;
