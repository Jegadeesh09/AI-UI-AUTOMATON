import React from 'react';
import { X, Download, AlertTriangle, ExternalLink } from 'lucide-react';

const ErrorAlertModal = ({ isOpen, onClose, errorData }) => {
  if (!isOpen || !errorData) return null;

  const handleDownload = () => {
    window.open(`http://localhost:8000${errorData.pdf_url}`, '_blank');
  };

  // return (
  //   <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-[100] p-4 backdrop-blur-md">
  //     <div className="surface w-full max-w-2xl rounded-2xl shadow-2xl border border-red-900/30 flex flex-col p-8 relative animate-in fade-in zoom-in-95 duration-300">
  //       <button 
  //         onClick={onClose} 
  //         className="absolute top-4 right-4 text-zinc-400 hover:text-white transition-colors p-2"
  //       >
  //         <X size={24} />
  //       </button>
        
  //       <div className="flex items-center gap-4 mb-6">
  //         <div className="bg-red-100/20 p-3 rounded-full">
  //           <AlertTriangle className="text-red-500" size={16} />
  //         </div>
  //         <div>
  //           <h2 className="text-1xl font-bold text-white">Harvesting Failed</h2>
  //           <p className="text-zinc-500 text-sm">Generation stopped due to a critical error</p>
  //         </div>
  //       </div>

  //       <div className="bg-black/20 rounded-xl p-6 border border-zinc-800 mb-6">
  //         <p className="text-white text-lg leading-relaxed mb-6 font-medium">
  //           {errorData.message}
  //         </p>
          
  //         {errorData.screenshot && (
  //           <div className="rounded-lg overflow-hidden border border-zinc-800 bg-zinc-900">
  //               <p className="text-[2px] uppercase text-zinc-600 font-bold p-2 border-b border-zinc-800">Failure Screenshot</p>
  //               <img 
  //                 src={`http://localhost:8000/screenshots/${errorData.screenshot.replace(/\\\\/g, '/').split('screenshots/').pop()}`} 
  //                 alt="Failure" 
  //                 className="w-full h-auto max-h-[300px] object-contain"
  //               />
  //           </div>
  //         )}
  //       </div>

  //       <div className="flex gap-4">
  //         <button 
  //           onClick={onClose} 
  //           className="flex-1 px-6 py-3 border border-zinc-800 text-zinc-400 font-semibold rounded-xl hover:bg-zinc-900 transition-colors"
  //         >
  //           Close
  //         </button>
  //         <button 
  //           onClick={handleDownload} 
  //           className="flex-1 px-6 py-3 bg-red-600 text-white font-semibold rounded-xl hover:bg-red-500 transition-all flex items-center justify-center gap-2 shadow-lg shadow-red-900/20"
  //         >
  //           <Download size={20} />
  //           Download PDF Report
  //         </button>
  //       </div>
  //     </div>
  //   </div>
  // );
  return (
    <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-[90] p-6 backdrop-blur-md">
      <div className="surface w-full max-w-4xl min-h-[74vh] max-h-[74vh] rounded-2xl shadow-2xl border border-red-600/30 flex flex-col relative animate-in fade-in zoom-in-60 duration-300 overflow-hidden">

        {/* Sticky Header */}
        <div className="sticky top-0 z-10 bg-black/90 backdrop-blur-md p-6 border-b border-zinc-800 flex items-center gap-4">
          <div className="bg-red-100/20 p-3 rounded-full">
            <AlertTriangle className="text-red-500" size={20} />
          </div>

          <div className="flex-1">
            <h2 className="text-x font-bold text-white">Harvesting Failed</h2>
            <p className="text-zinc-500 text-sm">
              Generation stopped due to a critical error
            </p>
          </div>

          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white transition-colors p-2"
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 p-6 overflow-hidden">
          <div className="w-full h-80 bg-black border border-zinc-800 rounded-lg p-4 text-white resize-none focus:outline-none focus:ring-1 focus:ring-white/20 custom-scrollbar overflow-y-auto">
            <p
              className="text-white text-sm leading-relaxed mb-6 font-callibri whitespace-pre-line"
              dangerouslySetInnerHTML={{ __html: errorData.message }}
            />
            {/* <p className="text-white text-sm leading-relaxed mb-6 font-callibri whitespace-pre-line">
              {errorData.message}
            </p> */}

            {errorData.screenshot && (
              <div className="rounded-lg overflow-hidden  border-zinc-800 bg-zinc-1200 p-2 mt-4">
                {/* <p className="text-[10px] uppercase text-zinc-600 font-bold p-2 border-b border-zinc-800">
                  Failure Screenshot
                </p> */}
                <img
                  src={`http://localhost:8000/screenshots/${errorData.screenshot
                    .replace(/\\\\/g, '/')
                    .split('screenshots/')
                    .pop()}`}
                  alt="Failure"
                  className="w-full h-auto max-h-[300px] object-contain"
                />
              </div>
            )}
          </div>
        </div>

        {/* Sticky Footer */}
        <div className="sticky bottom-0 z-10 bg-black/90 backdrop-blur-md p-1 border-zinc-800 flex relative">
          <button
            onClick={onClose}
            className="absolute left-160 bottom-2.5 px-5 py-3 border-zinc-800 text-zinc-400 font-semibold rounded-xl hover:bg-zinc-900 transition-colors"
          >
            Close
          </button>

          <button
            onClick={handleDownload}
            className=" absolute right-6 bottom-2.5 px-5 py-3 bg-white text-black font-semibold rounded-xl hover:bg-gray-100 transition-all flex items-center justify-center gap-1 shadow-lg"
          >
            <Download size={20} />
            Download
          </button>
        </div>

      </div>
    </div>
  );
};

export default ErrorAlertModal;
