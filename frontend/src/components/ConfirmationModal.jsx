import React from 'react';
import { X } from 'lucide-react';

const ConfirmationModal = ({ isOpen, title, message, onConfirm, onCancel, confirmText = "Delete", cancelText = "Cancel" }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[100] p-4 backdrop-blur-sm">
      <div className="bg-[#fdfcfb] w-full max-w-sm rounded-2xl shadow-2xl flex flex-col p-8 relative animate-in fade-in zoom-in-95 duration-200">
        <button 
          onClick={onCancel} 
          className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-600 transition-colors bg-zinc-100 p-1 rounded-full"
        >
          <X size={16} />
        </button>
        
        <div className="text-center space-y-3 mt-2">
          <h2 className="text-2xl font-bold text-black" style={{ overflowWrap: 'anywhere' }}>{title || "Are you sure?"}</h2>
          <p className="text-black text-sm leading-relaxed" style={{ overflowWrap: 'anywhere' }}>
            {message || "Are you sure you want to delete this item? This action cannot be undone."}
          </p>
        </div>

        <div className="flex gap-3 mt-8">
          <button 
            onClick={onCancel} 
            className="flex-1 px-4 py-3 border border-zinc-300 text-zinc-700 font-semibold rounded-xl hover:bg-zinc-50 transition-colors"
          >
            {cancelText}
          </button>
          <button 
            onClick={onConfirm} 
            className="flex-1 px-4 py-3 bg-black text-white border border-black font-bold rounded-xl hover:bg-zinc-900 transition-all shadow-lg active:scale-95"
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmationModal;
