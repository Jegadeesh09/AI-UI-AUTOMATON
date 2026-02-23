import React, { useState, useEffect, useRef } from 'react';
import { X, Plus, ToggleLeft, ToggleRight, Sparkles, Monitor, Eye, EyeOff } from 'lucide-react';
import axios from 'axios';
import Toast from './Toast';
import CustomDropdown from './CustomDropdown';

const SettingsModal = ({ isOpen, onClose }) => {
  const [settings, setSettings] = useState({
    GEMINI_API_KEY: '',
    GPT_API_KEY: '',
    DEEPSEEK_API_KEY: '',
    OLLAMA_BASE_URL: 'http://localhost:11434',
    MODEL_NAME: '',
    LLM_PROVIDER: 'Gemini',
    IS_PAID_LLM: true,
    HEADLESS_AGENT: true,
    HEADLESS_SCRIPT: true,
    SHOW_CODE_ICON: true,
    CUSTOM_MODELS: []
  });

  const [customModelInput, setCustomModelInput] = useState('');
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });
  const [showCustomInput, setShowCustomInput] = useState(false);

  const providerModels = {
    Gemini: ['gemini-3-pro', 'gemini-1.5-flash', 'gemini-1.5-pro'],
    OpenAI: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    DeepSeek: ['deepseek-chat', 'deepseek-coder'],
    Local: ['llama3', 'mistral', 'codellama', 'phi3']
  };

  useEffect(() => {
    if (isOpen) {
      axios.get('http://localhost:8000/api/settings').then(res => {
        setSettings(prev => ({...prev, ...res.data}));
      });
    }
  }, [isOpen]);

  const handleSave = () => {
    axios.post('http://localhost:8000/api/settings', settings)
      .then(() => {
        setToast({ show: true, message: 'Settings saved successfully', type: 'success' });
        setTimeout(onClose, 1000);
      })
      .catch(err => setToast({ show: true, message: 'Error saving settings: ' + err.message, type: 'error' }));
  };

  const addCustomModel = () => {
    if (customModelInput && !settings.CUSTOM_MODELS.includes(customModelInput)) {
      setSettings({
        ...settings,
        CUSTOM_MODELS: [...settings.CUSTOM_MODELS, customModelInput],
        MODEL_NAME: customModelInput
      });
      setCustomModelInput('');
      setShowCustomInput(false);
    }
  };

  if (!isOpen) return null;

  const currentModels = settings.IS_PAID_LLM 
    ? [...(providerModels[settings.LLM_PROVIDER] || []), ...settings.CUSTOM_MODELS]
    : [...providerModels.Local, ...settings.CUSTOM_MODELS];

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <Toast 
        show={toast.show} 
        message={toast.message} 
        type={toast.type} 
        onClose={() => setToast({ ...toast, show: false })} 
      />
      <div className="surface w-full max-w-lg rounded-lg shadow-xl border border-zinc-800 flex flex-col max-h-[85vh]">
        <div className="flex justify-between items-center p-6 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold">Settings</h2>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          {/* LLM Mode Toggle */}
          <div className="flex items-center justify-between p-4 bg-zinc-900/50 rounded-lg border border-zinc-800">
            <div className="flex items-center gap-3">
              {settings.IS_PAID_LLM ? <Sparkles className="text-yellow-500" size={20} /> : <Monitor className="text-blue-500" size={20} />}
              <div>
                <p className="font-medium">{settings.IS_PAID_LLM ? 'Paid LLM (API)' : 'Local LLM (Ollama)'}</p>
                <p className="text-xs text-zinc-500">{settings.IS_PAID_LLM ? 'Using external cloud providers' : 'Running on your machine'}</p>
              </div>
            </div>
            <button 
              onClick={() => setSettings({...settings, IS_PAID_LLM: !settings.IS_PAID_LLM})}
              className="text-white"
            >
              {settings.IS_PAID_LLM ? <ToggleRight size={40} className="text-green-500" /> : <ToggleLeft size={40} className="text-zinc-600" />}
            </button>
          </div>

          {settings.IS_PAID_LLM && (
            <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
              <div>
                <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider mb-2">Provider</label>
                <CustomDropdown 
                  label="Provider"
                  value={settings.LLM_PROVIDER}
                  options={['Gemini', 'OpenAI', 'DeepSeek']}
                  onChange={val => setSettings({...settings, LLM_PROVIDER: val})}
                />
              </div>

              {settings.LLM_PROVIDER === 'Gemini' && (
                <div>
                  <label className="block text-sm font-medium text-zinc-400 mb-1">Gemini API Key</label>
                  <input 
                    type="password"
                    className="w-full bg-zinc-900 border border-zinc-800 rounded p-2 text-white focus:ring-1 focus:ring-white/20 outline-none"
                    value={settings.GEMINI_API_KEY}
                    onChange={e => setSettings({...settings, GEMINI_API_KEY: e.target.value})}
                    placeholder="Enter Gemini API Key"
                  />
                </div>
              )}

              {settings.LLM_PROVIDER === 'OpenAI' && (
                <div>
                  <label className="block text-sm font-medium text-zinc-400 mb-1">OpenAI API Key</label>
                  <input 
                    type="password"
                    className="w-full bg-zinc-900 border border-zinc-800 rounded p-2 text-white focus:ring-1 focus:ring-white/20 outline-none"
                    value={settings.GPT_API_KEY}
                    onChange={e => setSettings({...settings, GPT_API_KEY: e.target.value})}
                    placeholder="sk-..."
                  />
                </div>
              )}

              {settings.LLM_PROVIDER === 'DeepSeek' && (
                <div>
                  <label className="block text-sm font-medium text-zinc-400 mb-1">DeepSeek API Key</label>
                  <input 
                    type="password"
                    className="w-full bg-zinc-900 border border-zinc-800 rounded p-2 text-white focus:ring-1 focus:ring-white/20 outline-none"
                    value={settings.DEEPSEEK_API_KEY}
                    onChange={e => setSettings({...settings, DEEPSEEK_API_KEY: e.target.value})}
                    placeholder="ds-..."
                  />
                </div>
              )}
            </div>
          )}

          {!settings.IS_PAID_LLM && (
            <div className="animate-in fade-in slide-in-from-top-2">
              <label className="block text-sm font-medium text-zinc-400 mb-1">Ollama Base URL</label>
              <input 
                type="text"
                className="w-full bg-zinc-900 border border-zinc-800 rounded p-2 text-white focus:ring-1 focus:ring-white/20 outline-none"
                value={settings.OLLAMA_BASE_URL}
                onChange={e => setSettings({...settings, OLLAMA_BASE_URL: e.target.value})}
                placeholder="http://localhost:11434"
              />
            </div>
          )}

          {/* Headless Mode Toggles */}
          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 bg-zinc-900/50 rounded-lg border border-zinc-800">
              <div className="flex items-center gap-3">
                <Monitor className="text-zinc-400" size={20} />
                <div>
                  <p className="font-medium text-sm">Headless Mode Agent</p>
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider">For Harvesting phase</p>
                </div>
              </div>
              <button 
                onClick={() => setSettings({...settings, HEADLESS_AGENT: !settings.HEADLESS_AGENT})}
                className="text-white"
              >
                {settings.HEADLESS_AGENT ? <ToggleRight size={32} className="text-green-500" /> : <ToggleLeft size={32} className="text-zinc-600" />}
              </button>
            </div>

            <div className="flex items-center justify-between p-4 bg-zinc-900/50 rounded-lg border border-zinc-800">
              <div className="flex items-center gap-3">
                <Monitor className="text-zinc-400" size={20} />
                <div>
                  <p className="font-medium text-sm">Headless Mode Script</p>
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider">For Execution phase</p>
                </div>
              </div>
              <button 
                onClick={() => setSettings({...settings, HEADLESS_SCRIPT: !settings.HEADLESS_SCRIPT})}
                className="text-white"
              >
                {settings.HEADLESS_SCRIPT ? <ToggleRight size={32} className="text-green-500" /> : <ToggleLeft size={32} className="text-zinc-600" />}
              </button>
            </div>

            <div className="flex items-center justify-between p-4 bg-zinc-900/50 rounded-lg border border-zinc-800">
              <div className="flex items-center gap-3">
                {settings.SHOW_CODE_ICON ? <Eye className="text-zinc-400" size={20} /> : <EyeOff className="text-zinc-400" size={20} />}
                <div>
                  <p className="font-medium text-sm">Show Code Icon</p>
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider">In Script & Execution Tab</p>
                </div>
              </div>
              <button 
                onClick={() => setSettings({...settings, SHOW_CODE_ICON: !settings.SHOW_CODE_ICON})}
                className="text-white"
              >
                {settings.SHOW_CODE_ICON ? <ToggleRight size={32} className="text-green-500" /> : <ToggleLeft size={32} className="text-zinc-600" />}
              </button>
            </div>
          </div>


          <div className="pt-4 border-t border-zinc-800">
            <div className="flex justify-between items-center mb-2">
              <label className="block text-sm font-medium text-zinc-400">Model Name</label>
              <button 
                onClick={() => setShowCustomInput(!showCustomInput)}
                className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
              >
                <Plus size={12} /> Add Custom
              </button>
            </div>

            {showCustomInput ? (
              <div className="flex gap-2 mb-3">
                <input 
                  type="text"
                  className="flex-1 bg-zinc-900 border border-zinc-800 rounded p-2 text-white text-sm outline-none"
                  value={customModelInput}
                  onChange={e => setCustomModelInput(e.target.value)}
                  placeholder="Enter model identifier"
                  autoFocus
                />
                <button 
                  onClick={addCustomModel}
                    className="px-3 py-1 bg-white hover:bg-zinc-200 text-black rounded text-sm transition-colors"
                >
                  Add
                </button>
              </div>
            ) : (
              <CustomDropdown 
                label="Model"
                value={settings.MODEL_NAME}
                options={currentModels}
                onChange={val => setSettings({...settings, MODEL_NAME: val})}
              />
            )}
          </div>
        </div>

        <div className="p-6 flex justify-end gap-3 border-t border-zinc-800">
          <button onClick={onClose} className="px-4 py-2 text-zinc-400 hover:text-white transition-colors">Cancel</button>
          <button onClick={handleSave} className="px-6 py-2 bg-white text-black font-bold rounded hover:bg-zinc-200 transition-colors">Save Changes</button>
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

export default SettingsModal;
