import React, { useEffect } from 'react';
import { CheckCircle, XCircle, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const Toast = ({ show, message, type, onClose }) => {
  useEffect(() => {
    if (show) {
      const timer = setTimeout(() => {
        onClose();
      }, 10000);
      return () => clearTimeout(timer);
    }
  }, [show, onClose]);

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 50, x: 0 }}
          animate={{ opacity: 1, y: 0, x: 0 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="fixed bottom-8 right-8 z-100 flex items-center gap-4 bg-white text-black p-4 rounded-lg shadow-2xl border border-zinc-200 min-w-[320px] max-w-450px"
        >
          <div className="shrink-0">
            {type === 'success' ? (
              <CheckCircle className="text-green-500" size={24} />
            ) : (
              <XCircle className="text-red-500" size={24} />
            )}
          </div>
          <div className="flex-1">
            <h4 className="font-bold text-sm text-black">{type === 'success' ? 'Success' : 'Error'}</h4>
            <p className="text-sm text-black leading-relaxed">{message}</p>
          </div>
          <button 
            onClick={onClose}
            className="shrink-0 text-zinc-400 hover:text-black transition-colors"
          >
            <X size={18} />
          </button>
          <div className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-lg ${type === 'success' ? 'bg-green-500' : 'bg-red-500'}`} />
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default Toast;
