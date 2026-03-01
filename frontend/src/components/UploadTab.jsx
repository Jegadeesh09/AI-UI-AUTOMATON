import React, { useState, useEffect } from 'react';
import { Upload, Play, CheckCircle, Loader2, FileSpreadsheet, FileJson, FileText, Database, AlertCircle, Trash2, Eye, Sparkles, Scan, Plus } from 'lucide-react';
import axios from 'axios';
import BDDModal from './BDDModal';
import Toast from './Toast';
import ConfirmationModal from './ConfirmationModal';
import ErrorAlertModal from './ErrorAlertModal';
import CustomDropdown from './CustomDropdown';

const UploadTab = ({ 
  selectedSuite, setSelectedSuite, 
  storyName, setStoryName, 
  isScanning, setIsScanning,
  hasBDD, setHasBDD,
  isUpdate, setIsUpdate
}) => {
  const [story, setStory] = useState('');
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dataFiles, setDataFiles] = useState([]);
  const [uploadingData, setUploadingData] = useState(false);
  const [existingStories, setExistingStories] = useState([]);
  const [suites, setSuites] = useState([]);
  const [showNewSuiteInput, setShowNewSuiteInput] = useState(false);
  const [newSuiteName, setNewSuiteName] = useState('');
  const [showNewStoryInput, setShowNewStoryInput] = useState(false);
  const [selectedScripts, setSelectedScripts] = useState([]);
  const [isParallelRunning, setIsParallelRunning] = useState(false);
  const [bddModal, setBddModal] = useState({ isOpen: false, content: '', storyId: '' });
  const [errorModal, setErrorModal] = useState({ isOpen: false, data: null });
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: null });

  useEffect(() => {
    fetchDataFiles();
    fetchSuites();
    if (selectedSuite) fetchExistingStories(selectedSuite);

    return () => {
    };
  }, [selectedSuite, storyName, isScanning, isUpdate]);

  const fetchSuites = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/suites');
      setSuites(res.data);
    } catch (err) {
      console.error('Failed to fetch suites', err);
    }
  };

  const handleCreateSuite = async () => {
    if (!newSuiteName.trim()) return;
    try {
      await axios.post('http://localhost:8000/api/suites', { name: newSuiteName });
      fetchSuites();
      setSelectedSuite(newSuiteName);
      setNewSuiteName('');
      setShowNewSuiteInput(false);
      setToast({ show: true, message: `Suite "${newSuiteName}" created`, type: 'success' });
    } catch (err) {
      setToast({ show: true, message: 'Failed to create suite: ' + (err.response?.data?.detail || err.message), type: 'error' });
    }
  };

  const fetchDataFiles = async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/data-files');
      setDataFiles(res.data);
    } catch (err) {
      console.error('Failed to fetch data files', err);
    }
  };

  const fetchExistingStories = async (suite = selectedSuite) => {
    if (!suite) return;
    try {
      const res = await axios.get(`http://localhost:8000/api/stories?suite=${suite}`);
      setExistingStories(res.data);
      // Update hasBDD for the currently selected story
      const current = res.data.find(s => s.story_id === storyName);
      if (current) setHasBDD(current.has_bdd);
    } catch (err) {
      console.error('Failed to fetch existing stories', err);
    }
  };

  const handleSuiteSelect = (suite) => {
    setSelectedSuite(suite);
    if (suite) {
      fetchExistingStories(suite);
    } else {
      setExistingStories([]);
    }
    setStory('');
    setStoryName('');
    setIsUpdate(false);
    setShowNewStoryInput(false);
  };

  const handleCheckboxChange = (storyId) => {
    setSelectedScripts(prev =>
      prev.includes(storyId) ? prev.filter(id => id !== storyId) : [...prev, storyId]
    );
  };

  const runParallelTests = async () => {
    if (selectedScripts.length === 0) {
      setToast({ show: true, message: 'Please select at least one script to run.', type: 'info' });
      return;
    }

    setIsParallelRunning(true);
    setToast({ show: true, message: `Starting parallel execution of ${selectedScripts.length} scripts...`, type: 'info' });

    try {
      const res = await axios.post('http://localhost:8000/api/run-tests-parallel', {
        suite: selectedSuite,
        stories: selectedScripts
      });

      setToast({
        show: true,
        message: `Parallel execution completed. Passed: ${res.data.passed}, Failed: ${res.data.failed}`,
        type: res.data.failed === 0 ? 'success' : 'error'
      });
    } catch (err) {
      setToast({ show: true, message: 'Parallel execution failed: ' + err.message, type: 'error' });
    } finally {
      setIsParallelRunning(false);
    }
  };

  const pollJobStatus = async (jobId) => {
    try {
      const res = await axios.get(`http://localhost:8000/api/job-status/${jobId}`);
      if (res.data.phase) {
        setPhase(res.data.phase);
      }
      if (res.data.status === 'completed') {
        setResult(res.data);
        setLoading(false);
        setPhase('');
        setToast({
          show: true,
          message: "Script generated successfully",
          type: 'success'
        });
      } else if (res.data.status === 'failed') {
        const errorMsg = res.data.error || "";
        try {
            // Find JSON block in case it's wrapped in other text
            const jsonMatch = errorMsg.match(/\{.*\}/s);
            const cleanJson = jsonMatch ? jsonMatch[0] : errorMsg;
            const parsedError = JSON.parse(cleanJson);
            
            if (parsedError.type === 'HARVEST_FAILURE') {
                // Remove alert modal, log instead
                // setErrorModal({ isOpen: true, data: parsedError });
                setToast({ show: true, message: "Harvesting failed. See messages for details.", type: 'error' });
                setError(parsedError.message);
            } else {
                setError(errorMsg);
            }
        } catch (e) {
            if (errorMsg.includes("429") || errorMsg.toLowerCase().includes("limit exceeded")) {
                setToast({ show: true, message: "Script not generated due to API limit exceeded error", type: 'error' });
                setError(null);
            } else {
                setError(errorMsg);
            }
        }
        setLoading(false);
        setPhase('');
      } else {
        // Continue polling
        setTimeout(() => pollJobStatus(jobId), 2000);
      }
    } catch (err) {
      setError('Failed to get job status: ' + err.message);
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!story || !storyName) {
        setToast({ show: true, message: 'Please provide both Story Name and Story Text', type: 'error' });
        return;
    }

    // Duplicate check
    try {
        const scriptsRes = await axios.get('http://localhost:8000/api/scripts');
        const scriptExists = scriptsRes.data.some(s => s.story_id === storyName);

        if (scriptExists && !isUpdate) {
             setToast({
                show: true,
                message: "Script creation is not allowed with duplicate names",
                type: 'error'
            });
            return;
        }
    } catch (e) {
        // ignore
    }

    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await axios.post('http://localhost:8000/api/upload-story', { 
        story_text: story,
        story_id: storyName,
        is_update: isUpdate,
        generate_only_bdd: true,
        suite: selectedSuite
      });
      
      setBddModal({
        isOpen: true,
        content: res.data.bdd_content,
        storyId: res.data.story_id,
        viewOnly: false
      });
      setLoading(false);
      fetchExistingStories();
    }catch (err) {
      let message = 'Upload failed. Please try again.';

      if (err.response?.status === 429) {
        message = 'API limit quota is exceeded';
      } else if (err.message === 'Network Error') {
        message = 'Network error ( Backend server is not reachable ) or API key not valid. Please pass a valid API key. ';
      } else if (err.response?.data?.detail) {
        message = err.response.data.detail;
      }
      setToast({
        show: true,
        message,
        type: 'error'
      });
      setLoading(false);
    }
  //  catch (err) {
  //       if (err.response?.status === 429) {
  //           setToast({
  //               show: true,
  //               message: "API limit quota is exceeded",
  //               type: 'error'
  //           });
  //       } else {
  //           setError('Upload failed: ' + (err.response?.data?.detail || err.message));
  //       }
  //       setLoading(false);
  //   }
  };

  const pollScanStatus = async () => {
    if (!isScanning) return;
    try {
        const res = await axios.get('http://localhost:8000/api/scan-status');
        if (res.data.status === 'completed' || res.data.status === 'success') {
            setIsScanning(false);
            if (res.data.bdd_content) {
                setBddModal({
                    isOpen: true,
                    content: res.data.bdd_content,
                    storyId: storyName || 'RecordedSession',
                    viewOnly: false
                });
            }
        } else if (res.data.status === 'empty') {
            setIsScanning(false);
            setToast({ show: true, message: 'Scan stopped: No actions recorded', type: 'info' });
        } else if (res.data.status === 'recording') {
            setTimeout(pollScanStatus, 2000);
        } else {
            setIsScanning(false);
        }
    } catch (err) {
        console.error('Scan polling error:', err);
        // Don't necessarily stop on first error, but maybe log it
        setTimeout(pollScanStatus, 5000);
    }
  };

  useEffect(() => {
    if (isScanning) {
        pollScanStatus();
    }
  }, [isScanning]);

  const checkSuite = () => {
    if (!selectedSuite) {
      setToast({ show: true, message: "Please select/create the test suite to make it actions", type: 'info' });
      return false;
    }
    return true;
  };

  const handleScan = async () => {
    if (!checkSuite()) return;
    if (isScanning) {
        setLoading(true);
        setPhase('Processing scan data...');
        try {
            const res = await axios.post(`http://localhost:8000/api/stop-scan?suite=${selectedSuite}`);
            setIsScanning(false);
            setLoading(false);
            if (res.data.bdd_content) {
                const finalStoryId = res.data.story_id || storyName || 'RecordedSession';
                setBddModal({
                    isOpen: true,
                    content: res.data.bdd_content,
                    storyId: finalStoryId,
                    viewOnly: false
                });
                if (res.data.story_id) setStoryName(res.data.story_id);
                fetchExistingStories(selectedSuite);
            }
        } catch (err) {
            setToast({ show: true, message: 'Failed to stop scan: ' + err.message, type: 'error' });
            setLoading(false);
            setIsScanning(false);
        }
    } else {
        try {
            await axios.post('http://localhost:8000/api/start-scan');
            setIsScanning(true);
            setToast({ show: true, message: 'Scan started. Please interact with the browser.', type: 'success' });
        } catch (err) {
            setToast({ show: true, message: 'Failed to start scan: ' + err.message, type: 'error' });
        }
    }
  };

  const handleApproveBDD = async (approvedBDD) => {
    setBddModal({ ...bddModal, isOpen: false });
    setLoading(true);
    setPhase('Script generation started');
    
    try {
      const res = await axios.post('http://localhost:8000/api/approve-bdd', {
        story_id: bddModal.storyId,
        story_text: story,
        bdd_content: approvedBDD,
        suite: selectedSuite
      });
      fetchExistingStories(selectedSuite);
      pollJobStatus(res.data.job_id);
    } catch (err) {
        if (err.response?.status === 429) {
            setToast({
                show: true,
                message: "API limit quota is exceeded",
                type: 'error'
            });
        } else {
            setError('Script generation failed: ' + (err.response?.data?.detail || err.message));
        }
        setLoading(false);
    }
  };

  const handleStoryFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setStoryName(file.name);
    setIsUpdate(false);
    
    const reader = new FileReader();
    reader.onload = (e) => {
      setStory(e.target.result);
    };
    reader.readAsText(file);
  };

  const handleStorySelect = async (name) => {
    if (!name) {
        setStory('');
        setStoryName('');
        setIsUpdate(false);
        setHasBDD(false);
        return;
    }
    
    if (!Array.isArray(existingStories)) return;

    const storyInfo = existingStories.find(s => s.story_id === name);
    // If it's a new story that hasn't been saved yet, don't try to fetch it
    if (!storyInfo) {
        setStoryName(name);
        setIsUpdate(false);
        setHasBDD(false);
        return;
    }

    try {
        const res = await axios.get(`http://localhost:8000/api/story/${name}?suite=${selectedSuite}`);
        if (res.data) {
            setStory(res.data.story_text || '');
            setStoryName(res.data.story_id || name);
            setIsUpdate(true);
            setHasBDD(storyInfo.has_bdd || false);
        }
    } catch (err) {
        setToast({ show: true, message: 'Failed to load story: ' + (err.response?.data?.detail || err.message), type: 'error' });
    }
  };

  const handleViewBDD = async (name) => {
    try {
        const res = await axios.get(`http://localhost:8000/api/bdd/${name}?suite=${selectedSuite}`);
        setBddModal({
            isOpen: true,
            content: res.data.bdd_content,
            storyId: name,
            viewOnly: true
        });
    } catch (err) {
        setToast({ show: true, message: 'Failed to load BDD: ' + (err.response?.data?.detail || err.message), type: 'error' });
    }
  };

  const handleDeleteStory = (name) => {
    setConfirmModal({
        isOpen: true,
        title: "Delete Story?",
        message: `Are you sure you want to delete "${name}"? This will delete the story text, BDD file, trace logs, and test scripts.`,
        onConfirm: () => executeDeleteStory(name)
    });
  };

  const executeDeleteStory = async (name) => {
    setConfirmModal({ ...confirmModal, isOpen: false });
    try {
        await axios.delete(`http://localhost:8000/api/script/${name}?scope=full&suite=${selectedSuite}`);
        setToast({ show: true, message: `Story "${name}" and all associated data deleted`, type: 'success' });
        if (storyName === name) {
            setStory('');
            setStoryName('');
            setIsUpdate(false);
        }
        fetchExistingStories();
    } catch (err) {
        setToast({ show: true, message: 'Deletion failed: ' + (err.response?.data?.detail || err.message), type: 'error' });
    }
  };

  const handleDeleteSuite = (name) => {
    const stories = existingStories.map(s => s.story_id).join(', ');
    setConfirmModal({
        isOpen: true,
        title: "Delete Suite?",
        message: `These are stories stored under this suite: ${stories || 'None'}. Are you sure delete the items?`,
        onConfirm: () => executeDeleteSuite(name)
    });
  };

  const executeDeleteSuite = async (name) => {
    setConfirmModal({ ...confirmModal, isOpen: false });
    try {
        await axios.delete(`http://localhost:8000/api/suite/${name}`);
        setToast({ show: true, message: `Suite "${name}" and all associated data deleted`, type: 'success' });
        fetchSuites();
        setSelectedSuite('Default');
        fetchExistingStories('Default');
        setStory('');
        setStoryName('');
        setIsUpdate(false);
    } catch (err) {
        setToast({ show: true, message: 'Deletion failed: ' + (err.response?.data?.detail || err.message), type: 'error' });
    }
  };

  const handleDeleteDataFile = async (filename) => {
    setConfirmModal({
        isOpen: true,
        title: "Delete Data File?",
        message: `Are you sure you want to delete "${filename}"?`,
        onConfirm: async () => {
            setConfirmModal({ ...confirmModal, isOpen: false });
            try {
                await axios.delete(`http://localhost:8000/api/data-file/${filename}`);
                setToast({ show: true, message: `Data file "${filename}" deleted`, type: 'success' });
                fetchDataFiles();
            } catch (err) {
                setToast({ show: true, message: 'Deletion failed: ' + (err.response?.data?.detail || err.message), type: 'error' });
            }
        }
    });
  };

  const handleDataFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploadingData(true);
    try {
      await axios.post('http://localhost:8000/api/upload-data', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      fetchDataFiles();
      setToast({ show: true, message: 'Data file uploaded successfully', type: 'success' });
    } catch (err) {
      setToast({ show: true, message: 'Data upload failed: ' + (err.response?.data?.detail || err.message), type: 'error' });
    } finally {
      setUploadingData(false);
    }
  };

  const getFileIcon = (filename) => {
    if (filename.endsWith('.csv')) return <FileText size={16} className="text-blue-400" />;
    if (filename.endsWith('.json')) return <FileJson size={16} className="text-yellow-400" />;
    if (filename.endsWith('.xlsx') || filename.endsWith('.xls')) return <FileSpreadsheet size={16} className="text-green-400" />;
    return <FileText size={16} />;
  };

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 h-full">
      <ConfirmationModal 
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal({ ...confirmModal, isOpen: false })}
      />
      <Toast 
        show={toast.show} 
        message={toast.message} 
        type={toast.type} 
        onClose={() => setToast({ ...toast, show: false })} 
      />
      <BDDModal 
        isOpen={bddModal.isOpen}
        bddContent={bddModal.content}
        storyId={bddModal.storyId}
        viewOnly={bddModal.viewOnly}
        onApprove={handleApproveBDD}
        onClose={() => setBddModal({ ...bddModal, isOpen: false })}
      />
      <ErrorAlertModal 
        isOpen={errorModal.isOpen}
        errorData={errorModal.data}
        onClose={() => setErrorModal({ ...errorModal, isOpen: false })}
      />
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pb-8">
        <div className="lg:col-span-8 space-y-6">
        <div className="surface p-6 rounded-lg transition-all duration-300 relative">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold">User Story</h3>
            <div className="flex gap-2">
              <button 
                className={`px-3 py-1.5 rounded border border-zinc-800 text-[11px] transition-all flex items-center gap-2 ${isScanning ? 'text-red-500 animate-blink-red' : 'text-zinc-400 hover:text-white btn-secondary'}`}
                onClick={handleScan}
                disabled={!selectedSuite}
              >
                <Scan size={14} /> {isScanning ? 'Stop Scan' : 'Scan'}
              </button>
              <button 
                className={`px-3 py-1.5 btn-secondary border border-zinc-800 rounded text-[11px] text-zinc-400 hover:text-white transition-colors flex items-center gap-2 ${(!isUpdate || !hasBDD) ? 'opacity-50' : ''}`}
                onClick={() => {
                  if (checkSuite()) {
                    if (isUpdate && hasBDD) handleViewBDD(storyName);
                  }
                }}
              >
                <Eye size={14} /> BDD
              </button>
              <button 
                className={`px-3 py-1.5 btn-secondary border border-zinc-800 rounded text-[11px] text-zinc-400 hover:text-red-500 hover:bg-red-500/10 transition-colors flex items-center gap-2 ${!isUpdate ? 'opacity-50' : ''}`}
                onClick={() => {
                   if (checkSuite()) {
                     if (isUpdate) handleDeleteStory(storyName);
                   }
                }}
              >
                <Trash2 size={14} /> Delete
              </button>
            </div>
          </div>

          <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
             <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">Test Suite</label>
                <div className="flex gap-2">
                   <div className="relative flex-1">
                      <CustomDropdown 
                        label="Suite"
                        value={selectedSuite}
                        options={suites}
                        onChange={handleSuiteSelect}
                        placeholder="-- Select Suite --"
                      />
                   </div>
                   <button 
                     className={`px-3 flex items-center gap-2 rounded border transition-all ${showNewSuiteInput ? 'bg-zinc-800 border-zinc-700 text-white' : 'btn-secondary'}`}
                     onClick={() => setShowNewSuiteInput(!showNewSuiteInput)}
                     title="New Suite"
                   >
                     <Plus size={16} />
                   </button>
                   <button 
                     className="px-3 flex items-center gap-2 rounded border border-zinc-800 btn-secondary text-red-400 hover:text-red-500 hover:bg-red-500/10"
                     onClick={() => handleDeleteSuite(selectedSuite)}
                     title="Delete Suite"
                   >
                     <Trash2 size={16} />
                   </button>
                   {selectedSuite && (
                      <button
                        onClick={runParallelTests}
                        disabled={isParallelRunning || selectedScripts.length === 0}
                        className="px-4 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:hover:bg-emerald-600 text-white text-[11px] font-bold rounded flex items-center gap-2 transition-all"
                      >
                        {isParallelRunning ? <Loader2 className="animate-spin" size={14} /> : <Play size={14} />}
                        Run Agent
                      </button>
                   )}
                </div>
                {showNewSuiteInput && (
                   <div className="mt-2 flex gap-2 animate-in fade-in slide-in-from-top-1">
                      <input 
                        type="text"
                        className="flex-1 bg-zinc-950 border border-zinc-800 rounded p-2 text-white text-sm outline-none focus:border-zinc-700"
                        placeholder="New suite name"
                        value={newSuiteName}
                        onChange={e => setNewSuiteName(e.target.value)}
                        autoFocus
                      />
                      <button 
                        className="px-3 py-1 bg-white text-black hover:bg-zinc-200 rounded text-xs font-bold transition-colors"
                        onClick={handleCreateSuite}
                      >
                        Create
                      </button>
                   </div>
                )}
             </div>
             <div className={`${!selectedSuite ? 'opacity-30' : ''}`}>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">Story File Name</label>
                <div className="flex gap-2">
                   <div className="relative flex-1" onClick={() => !selectedSuite && checkSuite()}>
                      <div className="flex gap-2 items-center bg-zinc-950 border border-zinc-800 rounded p-1">
                        <div className="flex-1">
                          <CustomDropdown
                            label="Story"
                            value={storyName}
                            options={Array.isArray(existingStories) ? existingStories.map(s => s.story_id) : []}
                            onChange={handleStorySelect}
                            placeholder="-- Select Story --"
                            disabled={!selectedSuite}
                          />
                        </div>
                        {storyName && (
                          <input
                            type="checkbox"
                            className="w-4 h-4 rounded border-zinc-700 bg-zinc-800 text-blue-600 focus:ring-blue-500 mr-2"
                            checked={selectedScripts.includes(storyName)}
                            onChange={() => handleCheckboxChange(storyName)}
                          />
                        )}
                      </div>
                   </div>
                   <button 
                     className={`px-3 flex items-center gap-2 rounded border transition-all ${showNewStoryInput ? 'bg-zinc-800 border-zinc-700 text-white' : 'btn-secondary'}`}
                     onClick={() => {
                        if (checkSuite()) {
                            setShowNewStoryInput(!showNewStoryInput); 
                            if(!showNewStoryInput) { setStoryName(''); setStory(''); setIsUpdate(false); }
                        }
                     }}
                     title="New Story"
                   >
                     <Plus size={16} />
                   </button>
                   <label 
                        className={`px-3 flex items-center gap-2 rounded border border-zinc-800 btn-secondary cursor-pointer transition-colors`} 
                        title="Upload .txt"
                        onClick={() => !selectedSuite && checkSuite()}
                    >
                        <Upload size={16} />
                        <input 
                            type="file" 
                            className="hidden" 
                            accept=".txt" 
                            onChange={(e) => selectedSuite && handleStoryFileUpload(e)} 
                            disabled={!selectedSuite} 
                        />
                    </label>
                </div>
                {showNewStoryInput && (
                   <div className="mt-2 flex gap-2 animate-in fade-in slide-in-from-top-1">
                      <input 
                        type="text"
                        className="flex-1 bg-zinc-950 border border-zinc-800 rounded p-2 text-white text-sm outline-none focus:border-zinc-700"
                        placeholder="e.g. LoginStory"
                        value={storyName}
                        onChange={e => {
                            setStoryName(e.target.value);
                            setIsUpdate(false);
                        }}
                        autoFocus
                      />
                      <button 
                        className="px-3 py-1 bg-white text-black hover:bg-zinc-200 rounded text-xs font-bold transition-colors"
                        onClick={() => setShowNewStoryInput(false)}
                      >
                        Add
                      </button>
                   </div>
                )}
             </div>
          </div>

          <textarea 
            className="w-full h-80 bg-black border border-zinc-800 rounded-lg p-4 text-white resize-none focus:outline-none focus:ring-1 focus:ring-white/20 custom-scrollbar overflow-y-auto"
            placeholder="As a user, I want to login to the system so that I can access my dashboard... Mention data files in quotes, e.g., 'data.csv'"
            value={story}
            onChange={e => setStory(e.target.value)}
          />
          <div className="mt-4 flex justify-end">
            <button 
              onClick={handleUpload}
              disabled={loading || !storyName || !story}
              className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? <Loader2 className="animate-spin" size={18} /> : <Play size={18} />}
              {loading ? 'Generating...' : 'Generate Automation Script'}
            </button>
          </div>
        </div>

        {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 text-red-400 animate-in fade-in slide-in-from-top-2">
                <AlertCircle size={20} />
                <p className="text-sm font-medium">{error}</p>
            </div>
        )}

        {result && (
          <div className="surface p-6 rounded-lg animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center gap-2 text-green-500 mb-4">
              <CheckCircle size={20} />
              <h4 className="font-semibold">Generation Successful!</h4>
            </div>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-zinc-400 mb-1">Generated Story ID</p>
                <code className="bg-zinc-900 px-2 py-1 rounded text-white">{result.story_id}</code>
              </div>
              {result.result?.data_context && (
                <div>
                    <p className="text-sm text-zinc-400 mb-1">Detected Data Context</p>
                    <div className="flex items-center gap-2 bg-zinc-900 px-2 py-1 rounded text-white text-xs">
                        <Database size={14} />
                        {result.result.data_context.filename} ({result.result.data_context.structure?.join(', ') || 'no columns detected'})
                    </div>
                </div>
              )}
              {result.result?.healing_report && (
                <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800">
                  <p className="text-sm font-medium text-zinc-400 mb-2 flex items-center gap-2">
                    <Sparkles size={16} className="text-yellow-500" />
                    AI Healing Report
                  </p>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-zinc-500">Total Steps:</span>
                      <span className="ml-2 font-mono text-white">{result.result.healing_report.total_steps}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500">Healed Steps:</span>
                      <span className="ml-2 font-mono text-yellow-500">{result.result.healing_report.healed_steps}</span>
                    </div>
                  </div>
                  {result.result.healing_report.details?.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <p className="text-[10px] uppercase text-zinc-600 font-bold">Healed Actions</p>
                      {result.result.healing_report.details.map((detail, idx) => (
                        <div key={idx} className="text-[11px] p-2 bg-black/30 rounded border border-zinc-800/50">
                          <div className="text-yellow-400 mb-1">Goal: {detail.step_original}</div>
                          <div className="text-zinc-400 italic">"{detail.healed_action?.reason}"</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {/* BDD display commented out as per requirement
              <div>
                <p className="text-sm text-zinc-400 mb-1">BDD Gherkin</p>
                <pre className="bg-black p-4 rounded border border-zinc-800 text-xs overflow-x-auto">
                  {result.result?.bdd}
                </pre>
              </div>
              */}
            </div>
          </div>
        )}
      </div>

        <div className="lg:col-span-4 space-y-6 lg:sticky lg:top-0">
          <div className="surface p-6 rounded-lg border-zinc-800">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-semibold text-white">Data Documents</h3>
              <label className="cursor-pointer flex items-center gap-2 px-3 py-1.5 bg-white text-black hover:bg-zinc-200 rounded text-xs font-bold transition-colors" title="Upload new data file">
                {uploadingData ? <Loader2 className="animate-spin" size={14} /> : <Upload size={14} />}
                <span>Upload</span>
                <input type="file" className="hidden" onChange={handleDataFileUpload} accept=".csv,.json,.xlsx,.xls" disabled={uploadingData} />
              </label>
            </div>
          
          <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
            {dataFiles.length === 0 ? (
              <p className="text-zinc-500 text-sm italic">No data files uploaded yet.</p>
            ) : (
              dataFiles.map(file => (
                <div key={file} className="flex items-center justify-between p-3 bg-zinc-900/50 border border-zinc-800 rounded hover:border-zinc-700 transition-colors group">
                  <div className="flex items-center gap-3 overflow-hidden">
                    {getFileIcon(file)}
                    <span className="text-sm truncate" title={file}>{file}</span>
                  </div>
                  <button
                    onClick={() => handleDeleteDataFile(file)}
                    className="text-zinc-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all p-1"
                    title="Delete File"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>

          <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg text-[11px] text-blue-200 leading-relaxed">
            <p className="font-bold mb-1 flex items-center gap-1 text-blue-400 uppercase tracking-wider">
                <Database size={12} /> Tip
            </p>
            Mention data filenames in quotes in your story (e.g., "users.csv"). The AI will detect it and generate validation steps.
          </div>
        </div>
      </div>
    </div>
    </div>
  );
};

export default UploadTab;
