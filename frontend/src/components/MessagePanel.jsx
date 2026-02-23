import React from 'react';
import { X, Trash2 } from 'lucide-react';

const MessagePanel = ({ isOpen, onClose, messages, totalTokens, onClear }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed top-0 right-0 w-80 h-full bg-zinc-950 border-l border-zinc-800 shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-300">
      <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-black">
        <h3 className="font-bold text-lg flex flex-col">
          <span>Execution Console</span>
          {totalTokens > 0 && (
            <span className="text-[10px] text-blue-400 font-medium mt-1">
              Aggregated token usage: {totalTokens}
            </span>
          )}
        </h3>
        <div className="flex items-center gap-2">
          <button 
            onClick={onClear}
            className="p-1.5 hover:bg-zinc-900 rounded-md text-zinc-500 hover:text-red-400 transition-colors"
            title="Clear Messages"
          >
            <Trash2 size={18} />
          </button>
          <button 
            onClick={onClose}
            className="p-1.5 hover:bg-zinc-900 rounded-md text-zinc-500 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-zinc-600 italic text-sm">
            <p>No messages yet</p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div 
              key={i} 
              className={`text-[13px] p-3 rounded border font-mono ${
                msg.log_type === 'token' 
                ? 'bg-blue-900/10 border-blue-900/30 text-blue-300' 
                : msg.log_type === 'error'
                ? 'bg-red-900/10 border-red-900/30 text-red-300'
                : 'bg-zinc-900/30 border-zinc-800 text-zinc-300'
              } animate-in fade-in slide-in-from-bottom-1 shadow-sm`}
            >
              <div className="flex justify-between items-start mb-1">
                <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-bold">
                  {msg.log_type || 'info'}
                </span>
                <span className="text-[9px] text-zinc-600">
                  {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </div>
              <p className="leading-relaxed whitespace-pre-wrap">{msg.message}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default MessagePanel;
