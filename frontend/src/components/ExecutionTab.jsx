import React, { useState, useEffect } from 'react';
import { Play, FileText, RefreshCw, AlertCircle, CheckCircle, Loader2, Trash2, ExternalLink, ChevronDown, ChevronRight, Code, BookOpen } from 'lucide-react';
import axios from 'axios';
import Toast from './Toast';
import ReportModal from './ReportModal';
import ConfirmationModal from './ConfirmationModal';
import ScriptEditorModal from './ScriptEditorModal';

const ExecutionTab = ({ settings, onRefreshSettings }) => {
  const [suites, setSuites] = useState([]);
  const [expandedSuites, setExpandedSuites] = useState({});
  const [executing, setExecuting] = useState(null);
  const [results, setResults] = useState({});
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });
  const [reportModal, setReportModal] = useState({ isOpen: false, url: '', storyId: '', suite: '' });
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: null, type: 'delete' });

  const fetchScripts = async () => {
    const res = await axios.get('http://localhost:8000/api/scripts');
    setSuites(res.data);
  };

  useEffect(() => {
    fetchScripts();
  }, []);

  const toggleSuite = (suiteName) => {
    setExpandedSuites(prev => ({
      ...prev,
      [suiteName]: !prev[suiteName]
    }));
  };

  const runTest = async (storyId, suite) => {
    setExecuting(storyId);
    try {
      const res = await axios.post(
        'http://localhost:8000/api/run-test',
        { story_id: storyId, suite: suite }  
      );
      const data = res.data;
      setResults(prev => ({ ...prev, [storyId]: data }));
      fetchScripts(); // Refresh to update has_report status

      // Show toast
      let message = "";
      let type = data.success ? "success" : "error";
      
      const stdout = data.stdout || "";
      const passedMatch = stdout.match(/(\d+) passed/);
      const failedMatch = stdout.match(/(\d+) failed/);
      
      const passedCount = passedMatch ? parseInt(passedMatch[1]) : 0;
      const failedCount = failedMatch ? parseInt(failedMatch[1]) : 0;

      if (data.success) {
        if (failedCount === 0) {
          message = "The script is passed, view the report for the detailed output";
        } else {
          message = `${passedCount} scenario passed, ${failedCount} failed. View the report for the detailed output`;
        }
      } else {
        if (passedCount > 0 && failedCount > 0) {
           message = `${passedCount} scenario passed, ${failedCount} failed. View the report for the detailed output`;
           type = "error"; // Use error theme for mixed results as requested
        } else {
           message = "The script is failed, view the report for the detailed output";
        }
      }

      setToast({
        show: true,
        message: message,
        type: type
      });

    } catch (err) {
      const errorData = {
        exit_code: -1,
        stderr:
          err.response?.data?.detail ||
          err.response?.data ||
          err.message ||
          "Unknown execution error"
      };

      setResults(prev => ({
        ...prev,
        [storyId]: errorData
      }));

    } finally {
      setExecuting(null);
    }
  };
  //   catch (err) {
  //     alert('Execution failed: ' + (err.response?.data?.detail || err.message));
  //   } finally {
  //     setExecuting(null);
  //   }
  // };

  const deleteScript = async (storyId, suite) => {
    setConfirmModal({
        isOpen: true,
        title: "Are you sure?",
        message: `Are you sure you want to delete the script for "${storyId}"? This action cannot be undone.`,
        confirmText: "Delete",
        onConfirm: () => executeDelete(storyId, suite)
    });
  };

  const executeDelete = async (storyId, suite) => {
    setConfirmModal({ ...confirmModal, isOpen: false });
    try {
      await axios.delete(`http://localhost:8000/api/script/${storyId}?scope=script_only&suite=${suite}`);
      const newResults = { ...results };
      delete newResults[storyId];
      setResults(newResults);
      setToast({ show: true, message: `Script for ${storyId} deleted`, type: 'success' });
    } catch (err) {
      setToast({ show: true, message: 'Deletion failed: ' + (err.response?.data?.detail || err.message), type: 'error' });
    }
  };

  const selfHeal = async (storyId, suite) => {
    setConfirmModal({
        isOpen: true,
        title: "Heal Script?",
        message: "This will run the harvester agent to update the script. Continue?",
        confirmText: "Yes",
        cancelText: "No",
        onConfirm: () => executeSelfHeal(storyId, suite)
    });
  };

  const executeSelfHeal = async (storyId, suite) => {
    setConfirmModal({ ...confirmModal, isOpen: false });
    setExecuting(storyId);
    try {
      const res = await axios.post(`http://localhost:8000/api/self-heal/${storyId}?suite=${suite}`);
      const report = res.data.result?.healing_report;
      let message = 'Self-healing completed! The script has been updated.';
      if (report && report.healed_steps > 0) {
        message = `Self-healing completed! ${report.healed_steps} steps were automatically repaired by AI.`;
      }
      setToast({
        show: true,
        message: message,
        type: 'success'
      });
      fetchScripts();
    } catch (err) {
      setToast({
        show: true,
        message: 'Self-healing failed: ' + (err.response?.data?.detail || err.message),
        type: 'error'
      });
    } finally {
      setExecuting(null);
    }
  };

  const [editorModal, setEditorModal] = useState({ isOpen: false, code: '', storyId: '', suite: '' });

  const openEditor = async (storyId, suite) => {
    try {
        const res = await axios.get(`http://localhost:8000/api/script-content/${storyId}?suite=${suite}`);
        setEditorModal({ isOpen: true, code: res.data.code, storyId, suite });
    } catch (err) {
        setToast({ show: true, message: 'Failed to load script: ' + err.message, type: 'error' });
    }
  };

  const saveScript = async () => {
    try {
        await axios.post(`http://localhost:8000/api/script-content/${editorModal.storyId}`, {
            code: editorModal.code,
            suite: editorModal.suite
        });
        setToast({ show: true, message: 'Script saved successfully', type: 'success' });
        setEditorModal({ ...editorModal, isOpen: false });
    } catch (err) {
        setToast({ show: true, message: 'Failed to save script: ' + err.message, type: 'error' });
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <div className="lg:col-span-12 space-y-6">
      <ConfirmationModal 
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmText={confirmModal.confirmText}
        cancelText={confirmModal.cancelText}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal({ ...confirmModal, isOpen: false })}
      />
      <Toast 
        show={toast.show} 
        message={toast.message} 
        type={toast.type} 
        onClose={() => setToast({ ...toast, show: false })} 
      />
      {suites.length === 0 && (
        <div className="surface p-12 rounded-lg text-center text-zinc-500">
          No scripts generated yet. Go to the Upload tab to get started.
        </div>
      )}
      
      {suites.map(suiteGroup => (
        <div key={suiteGroup.suite} className="space-y-3">
          <button 
            onClick={() => toggleSuite(suiteGroup.suite)}
            className="w-full flex items-center justify-between p-4 bg-zinc-900/30 rounded-lg border border-zinc-800 hover:bg-zinc-900/50 transition-colors group"
          >
            <div className="flex items-center gap-3">
              <BookOpen size={18} className="text-blue-400" />
              <span className="font-bold text-zinc-200">{suiteGroup.suite}</span>
              <span className="text-xs px-2 py-0.5 bg-zinc-800 text-zinc-500 rounded-full group-hover:text-zinc-300">
                {suiteGroup.scripts.length} Scripts
              </span>
            </div>
            {expandedSuites[suiteGroup.suite] ? <ChevronDown size={20} className="text-zinc-500" /> : <ChevronRight size={20} className="text-zinc-500" />}
          </button>

          {expandedSuites[suiteGroup.suite] && (
            <div className="pl-6 space-y-4 animate-in slide-in-from-top-2 duration-200">
              {suiteGroup.scripts.length === 0 ? (
                <div className="text-xs text-zinc-600 italic py-2">No scripts in this suite</div>
              ) : (
                suiteGroup.scripts.map(script => (
                  <div key={script.story_id} className="surface p-6 rounded-lg flex flex-col gap-4 border-l-2 border-blue-600/30">
                    <div className="flex justify-between items-center">
                      <div>
                        <h3 className="font-bold text-lg">{script.story_id}</h3>
                        <p className="text-[10px] text-zinc-500 uppercase tracking-widest">{script.filename}</p>
                      </div>
                      <div className="flex gap-2">
                        {settings?.SHOW_CODE_ICON && (
                          <button 
                            onClick={() => openEditor(script.story_id, suiteGroup.suite)}
                            className="btn-secondary flex items-center justify-center p-2 text-blue-400 hover:text-blue-300"
                            title="View/Edit Script Code"
                          >
                            <Code size={16} />
                          </button>
                        )}
                        <button 
                          onClick={() => deleteScript(script.story_id, suiteGroup.suite)}
                          disabled={executing === script.story_id}
                          className="btn-secondary text-red-400 hover:text-red-500 hover:bg-red-500/10 flex items-center justify-center p-2"
                          title="Delete Script"
                        >
                          <Trash2 size={16} />
                        </button>
                        <button 
                          onClick={() => selfHeal(script.story_id, suiteGroup.suite)}
                          disabled={executing === script.story_id}
                          className="btn-secondary flex items-center gap-2"
                          title="Self Heal XPath"
                        >
                          <RefreshCw size={16} className={executing === script.story_id ? 'animate-spin' : ''} />
                          Heal
                        </button>
                        <button 
                          onClick={() => setReportModal({
                            isOpen: true,
                            url: `http://localhost:8000/suites/${suiteGroup.suite}/reports/${script.story_id}/index.html`,
                            storyId: script.story_id,
                            suite: suiteGroup.suite
                          })}
                          disabled={executing === script.story_id}
                          className={`btn-secondary flex items-center gap-2 ${(!script.has_report && !results[script.story_id]) ? 'opacity-50' : ''}`}
                          title={(!script.has_report && !results[script.story_id]) ? "No report available yet" : "Show Allure Report"}
                        >
                          <ExternalLink size={16} />
                          Allure Report
                        </button>
                        <button 
                          onClick={() => runTest(script.story_id, suiteGroup.suite)}
                          disabled={executing === script.story_id}
                          className="btn-primary flex items-center gap-2 min-w-[120px] justify-center"
                        >
                          {executing === script.story_id ? <Loader2 className="animate-spin" size={16} /> : <Play size={16} />}
                          Run Agent
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      ))}
      <ReportModal 
        isOpen={reportModal.isOpen} 
        onClose={() => setReportModal({ ...reportModal, isOpen: false })} 
        reportUrl={reportModal.url}
        storyId={reportModal.storyId}
      />
      
      <ScriptEditorModal 
        isOpen={editorModal.isOpen}
        onClose={() => setEditorModal({ ...editorModal, isOpen: false })}
        code={editorModal.code}
        onChange={(code) => setEditorModal({ ...editorModal, code })}
        onSave={saveScript}
        storyId={editorModal.storyId}
      />
      </div>
    </div>
  );
};

export default ExecutionTab;
