import React, { useState, useEffect, useRef } from 'react';
import { Settings, FileText, Play, Code, Cpu, MessageSquare, LayoutDashboard, Scan, Eye, Trash2 } from 'lucide-react';
import axios from 'axios';
import UploadTab from './components/UploadTab';
import ExecutionTab from './components/ExecutionTab';
import DashboardTab from './components/DashboardTab';
import SettingsModal from './components/SettingsModal';
import MessagePanel from './components/MessagePanel';
import Toast from './components/Toast';

function App() {
  const [activeTab, setActiveTab] = useState('upload');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isMessagePanelOpen, setIsMessagePanelOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [totalTokens, setTotalTokens] = useState(0);
  const [settings, setSettings] = useState({});
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });
  
  // Shared state for header buttons
  const [selectedSuite, setSelectedSuite] = useState('');
  const [storyName, setStoryName] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [hasBDD, setHasBDD] = useState(false);
  const [isUpdate, setIsUpdate] = useState(false);
  
  const ws = useRef(null);

  useEffect(() => {
    connectWS();
    fetchSettings();

    const handleError = (event) => {
      setToast({ show: true, message: event.message || 'An error occurred', type: 'error' });
    };
    window.addEventListener('error', handleError);

    // Override window.alert to show toaster
    const originalAlert = window.alert;
    window.alert = (message) => {
      setToast({ show: true, message, type: 'info' });
    };

    return () => {
      window.removeEventListener('error', handleError);
      window.alert = originalAlert;
      if (ws.current) {
        const socket = ws.current;
        ws.current = null; // Important: clear reference before closing
        socket.onclose = null; // Prevent the onclose handler from triggering a reconnect
        socket.close();
      }
    };
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/settings');
      setSettings(res.data);
    } catch (err) {
      console.error('Failed to fetch settings', err);
    }
  };

  const connectWS = () => {
    if (ws.current && (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING)) {
      return;
    }
    
    const socket = new WebSocket('ws://localhost:8000/ws/logs');
    ws.current = socket;

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'log') {
        setMessages(prev => {
          // Check for duplicate messages based on content and timestamp if available
          const isDuplicate = prev.length > 0 && 
            prev[0].message === data.message && 
            prev[0].timestamp === data.timestamp;
          
          if (isDuplicate) return prev;
          return [data, ...prev].slice(0, 50);
        });
        if (data.log_type === 'token' && data.metadata?.total_tokens) {
          setTotalTokens(data.metadata.total_tokens);
        }
      }
    };

    socket.onclose = () => {
      // Only reconnect if this is still the current socket
      if (ws.current === socket) {
        setTimeout(connectWS, 3000);
      }
    };

    socket.onerror = () => {
        socket.close();
    };
  };

  // const connectWS = () => {
  //   if (ws.current) return; // prevent duplicate connections

  //   const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  //   const socket = new WebSocket(
  //     `${protocol}://${window.location.hostname}:8000/ws/logs`
  //   );

  //   ws.current = socket;

  //   socket.onopen = () => {
  //     console.log("✅ WebSocket connected");
  //   };

  //   socket.onmessage = (event) => {
  //     try {
  //       const data = JSON.parse(event.data);
  //       if (data.type === "log") {
  //         setMessages((prev) => [data, ...prev].slice(0, 50));
  //       }
  //     } catch (e) {
  //       console.error("Invalid WS message", e);
  //     }
  //   };

  //   socket.onclose = () => {
  //     console.log("❌ WebSocket closed. Reconnecting...");
  //     ws.current = null;
  //     setTimeout(connectWS, 3000);
  //   };

  //   socket.onerror = (err) => {
  //     console.error("WebSocket error:", err);
  //     socket.close();
  //   };
  // };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'upload': return (
        <UploadTab 
          selectedSuite={selectedSuite} 
          setSelectedSuite={setSelectedSuite}
          storyName={storyName}
          setStoryName={setStoryName}
          isScanning={isScanning}
          setIsScanning={setIsScanning}
          hasBDD={hasBDD}
          setHasBDD={setHasBDD}
          isUpdate={isUpdate}
          setIsUpdate={setIsUpdate}
        />
      );
      case 'execution': return <ExecutionTab settings={settings} onRefreshSettings={fetchSettings} />;
      case 'dashboard': return <DashboardTab />;
      default: return <UploadTab />;
    }
  };

  return (
    <div className="min-h-screen bg-black text-white p-8 flex flex-col overflow-y-auto no-scrollbar">
      {/* Header */}
      <div className="w-full flex justify-between items-center mb-12 px-4">
        <div className="flex items-center gap-3">
          <div className="bg-white p-2 rounded-lg">
            <Cpu className="text-black" size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">AI UI Automation</h1>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setIsMessagePanelOpen(true)}
            className={`p-2 hover:bg-zinc-900 rounded-lg transition-colors relative ${isMessagePanelOpen ? 'text-white bg-zinc-900' : 'text-zinc-400 hover:text-white'}`}
            title="Messages"
          >
            <MessageSquare size={24} />
            {messages.length > 0 && (
              <span className="absolute top-2 right-2 w-2 h-2 bg-blue-500 rounded-full ring-2 ring-black"></span>
            )}
          </button>
          <button 
            onClick={() => setIsSettingsOpen(true)}
            className="p-2 hover:bg-zinc-900 rounded-lg transition-colors text-zinc-400 hover:text-white"
            title="Settings"
          >
            <Settings size={24} />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="w-full px-4">
        {/* Tabs Navigation */}
        <div className="flex justify-between items-center border-b border-zinc-900 mb-8">
          <div className="flex gap-8">
            <button 
              onClick={() => setActiveTab('upload')}
              className={`pb-4 text-sm font-medium transition-colors relative ${activeTab === 'upload' ? 'text-white' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              <div className="flex items-center gap-2">
                <FileText size={18} />
                Story Upload
              </div>
              {activeTab === 'upload' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-white" />}
            </button>
            <button 
              onClick={() => setActiveTab('execution')}
              className={`pb-4 text-sm font-medium transition-colors relative ${activeTab === 'execution' ? 'text-white' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              <div className="flex items-center gap-2">
                <Code size={18} />
                Scripts & Execution
              </div>
              {activeTab === 'execution' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-white" />}
            </button>
            <button 
              onClick={() => setActiveTab('dashboard')}
              className={`pb-4 text-sm font-medium transition-colors relative ${activeTab === 'dashboard' ? 'text-white' : 'text-zinc-500 hover:text-zinc-300'}`}
            >
              <div className="flex items-center gap-2">
                <LayoutDashboard size={18} />
                Dashboard
              </div>
              {activeTab === 'dashboard' && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-white" />}
            </button>
          </div>
        </div>

        {/* Tab Panels */}
        <div className="flex-1">
          {renderTabContent()}
        </div>
      </div>

      {/* Footer */}
      {/* <div className="max-w-6xl mx-auto mt-20 pt-8 border-t border-zinc-900 text-center">
        <p className="text-zinc-600 text-xs">© 2024 AI UI Automation Agent. All rights reserved.</p>
      </div> */}

      <Toast 
        show={toast.show} 
        message={toast.message} 
        type={toast.type} 
        onClose={() => setToast({ ...toast, show: false })} 
      />

      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => {
          setIsSettingsOpen(false);
          fetchSettings();
        }} 
      />
      
      <MessagePanel 
        isOpen={isMessagePanelOpen} 
        onClose={() => setIsMessagePanelOpen(false)} 
        messages={messages}
        totalTokens={totalTokens}
        onClear={() => {
          setMessages([]);
          setTotalTokens(0);
        }}
      />
    </div>
  );
}

export default App;
