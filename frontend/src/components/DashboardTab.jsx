import React, { useState, useEffect } from 'react';
import { BarChart3, PieChart, Activity, ExternalLink, ChevronRight, CheckCircle2, XCircle, Layers, Percent } from 'lucide-react';
import axios from 'axios';
import ReportModal from './ReportModal';
import CustomDropdown from './CustomDropdown';

const DashboardTab = () => {
  const [suiteNames, setSuiteNames] = useState([]);
  const [storyNames, setStoryNames] = useState(['All']);
  const [selectedSuite, setSelectedSuite] = useState('All');
  const [selectedStoryId, setSelectedStoryId] = useState('All');
  const [stats, setStats] = useState({ total_stories: 0, passed: 0, failed: 0, suites: [] });
  const [selectedStoryDetail, setSelectedStoryDetail] = useState(null);
  const [reportModal, setReportModal] = useState({ isOpen: false, url: '', storyId: '' });
  
  useEffect(() => {
    axios.get('http://localhost:8000/api/suites').then(res => {
      setSuiteNames(['All', ...res.data]);
    });
    fetchStats('All', 'All');
  }, []);

  useEffect(() => {
    if (selectedSuite !== 'All') {
        axios.get(`http://localhost:8000/api/stories?suite=${selectedSuite}`).then(res => {
            setStoryNames(['All', ...res.data.map(s => s.story_id)]);
        });
    } else {
        setStoryNames(['All']);
        setSelectedStoryId('All');
    }
  }, [selectedSuite]);

  const fetchStats = async (suite, storyId) => {
    try {
      const res = await axios.get(`http://localhost:8000/api/dashboard/stats?suite=${suite}&story_id=${storyId}`);
      setStats(res.data);
      setSelectedStoryDetail(null);
    } catch (err) {
      console.error('Failed to fetch dashboard stats', err);
    }
  };

  const handleSuiteChange = (suite) => {
    setSelectedSuite(suite);
    setSelectedStoryId('All');
    fetchStats(suite, 'All');
  };

  const handleStoryChange = (storyId) => {
    setSelectedStoryId(storyId);
    fetchStats(selectedSuite, storyId);
  };

  const totalScenarios = stats.passed + stats.failed;
  const passRate = totalScenarios > 0 ? Math.round((stats.passed / totalScenarios) * 100) : 0;

  // Flatten stories for the chart if "All" is selected
  const allStories = stats.suites.flatMap(s => s.stories);

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 h-full">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-12 space-y-8 animate-in fade-in duration-500 pb-8">
      <ReportModal 
        isOpen={reportModal.isOpen} 
        onClose={() => setReportModal({ ...reportModal, isOpen: false })} 
        reportUrl={reportModal.url}
        storyId={reportModal.storyId}
      />
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Automation Dashboard</h2>
          <p className="text-zinc-500 text-sm">Overall status of test suites and execution metrics</p>
        </div>
        
        <div className="flex gap-4 w-1/2 justify-end">
            <div className="w-48">
              <CustomDropdown 
                label="Suite"
                value={selectedSuite}
                options={suiteNames}
                onChange={handleSuiteChange}
                placeholder="All Suites"
              />
            </div>

            <div className={`w-48`}>
              <CustomDropdown 
                label="Story"
                value={selectedStoryId}
                options={storyNames}
                onChange={handleStoryChange}
                placeholder="All Stories"
                disabled={selectedSuite === 'All'}
              />
            </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="surface p-6 rounded-xl border border-zinc-800 shadow-lg bg-zinc-900/20">
          <div className="flex items-center gap-3 mb-4 text-blue-400">
            <Layers size={20} />
            <h3 className="text-sm font-bold uppercase tracking-widest">Total Suites</h3>
          </div>
          <p className="text-4xl font-bold">{stats.suites.length}</p>
          <div className="mt-4 text-[10px] text-zinc-500 uppercase font-bold tracking-tight">Categorized folders</div>
        </div>

        <div className="surface p-6 rounded-xl border border-zinc-800 shadow-lg bg-zinc-900/20">
          <div className="flex items-center gap-3 mb-4 text-blue-400">
            <Activity size={20} />
            <h3 className="text-sm font-bold uppercase tracking-widest">Total Stories</h3>
          </div>
          <p className="text-4xl font-bold">{stats.total_stories}</p>
          <div className="mt-4 text-[10px] text-zinc-500 uppercase font-bold tracking-tight">Across selected suites</div>
        </div>
        
        <div className="surface p-6 rounded-xl border border-zinc-800 shadow-lg bg-green-900/10">
          <div className="flex items-center gap-3 mb-4 text-green-500">
            <Percent size={20} />
            <h3 className="text-sm font-bold uppercase tracking-widest">Avg Pass %</h3>
          </div>
          <p className="text-4xl font-bold text-green-500">{passRate}%</p>
          <div className="mt-4 flex items-center gap-2 text-[10px] uppercase font-bold text-green-600/80">
             Successfully executed
          </div>
        </div>

        <div className="surface p-6 rounded-xl border border-zinc-800 shadow-lg bg-red-900/10">
          <div className="flex items-center gap-3 mb-4 text-red-500">
            <Percent size={20} />
            <h3 className="text-sm font-bold uppercase tracking-widest">Avg Fail %</h3>
          </div>
          <p className="text-4xl font-bold text-red-500">{totalScenarios > 0 ? 100 - passRate : 0}%</p>
          <div className="mt-4 text-[10px] text-zinc-500 uppercase font-bold tracking-tight">Requires attention</div>
        </div>
      </div>

      {/* Charts & Drill-down */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="surface p-6 rounded-xl border border-zinc-800 h-[450px] flex flex-col">
          <h3 className="text-sm font-bold uppercase tracking-widest mb-8 text-zinc-400">Story Performance Chart</h3>
          <div className="flex-1 flex items-end justify-between gap-2 px-2 overflow-x-auto pb-4 custom-scrollbar">
             {allStories.length === 0 ? (
               <div className="w-full h-full flex items-center justify-center text-zinc-600 italic">No execution data available</div>
             ) : (
               allStories.map((story, i) => {
                 const total = story.passed + story.failed;
                 const pRate = total > 0 ? (story.passed / total) * 100 : 0;
                 const fRate = total > 0 ? (story.failed / total) * 100 : 0;
                 const isNotRun = total === 0;

                 return (
                   <div 
                    key={i} 
                    className={`flex-1 min-w-[40px] max-w-[80px] bg-zinc-900/50 rounded-t-sm relative group cursor-pointer transition-all hover:bg-zinc-800 ${selectedStoryDetail?.story_id === story.story_id ? 'ring-2 ring-blue-500' : ''}`}
                    onClick={() => setSelectedStoryDetail(story)}
                   >
                      <div className="absolute inset-0 flex flex-col justify-end">
                        {isNotRun ? (
                          <div className="bg-zinc-800 w-full h-[10%] mb-0.5" title="Not Run"></div>
                        ) : (
                          <>
                            <div className="bg-red-500/80 w-full" style={{ height: `${fRate}%` }}></div>
                            <div className="bg-green-500/80 w-full" style={{ height: `${pRate}%` }}></div>
                          </>
                        )}
                      </div>
                      <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 rotate-45 text-[9px] whitespace-nowrap text-zinc-500 font-bold group-hover:text-zinc-300">
                        {story.story_id.substring(0, 10)}...
                      </div>
                   </div>
                 );
               })
             )}
          </div>
          <div className="mt-12 flex justify-center gap-6 text-[10px] font-bold uppercase tracking-widest">
             <div className="flex items-center gap-2 text-green-500"><div className="w-2 h-2 bg-green-500 rounded-full"></div> Passed</div>
             <div className="flex items-center gap-2 text-red-500"><div className="w-2 h-2 bg-red-500 rounded-full"></div> Failed</div>
             <div className="flex items-center gap-2 text-zinc-600"><div className="w-2 h-2 bg-zinc-600 rounded-full"></div> Not Run</div>
          </div>
        </div>

        <div className="surface p-6 rounded-xl border border-zinc-800 h-[450px] flex flex-col">
          <h3 className="text-sm font-bold uppercase tracking-widest mb-4 text-zinc-400">
            {selectedStoryDetail ? `Story Detail: ${selectedStoryDetail.story_id}` : 'Select a story to view scenarios'}
          </h3>
          
          {!selectedStoryDetail ? (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-600 gap-4">
               <PieChart size={48} className="opacity-20" />
               <p className="italic text-sm text-center px-12">Click on a bar in the story chart to see scenario-wise details and reports</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
               <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="bg-green-500/10 p-3 rounded border border-green-500/20 text-center">
                    <div className="text-2xl font-bold text-green-500">{selectedStoryDetail.passed}</div>
                    <div className="text-[10px] uppercase font-bold text-green-600/70">Passed</div>
                  </div>
                  <div className="bg-red-500/10 p-3 rounded border border-red-500/20 text-center">
                    <div className="text-2xl font-bold text-red-500">{selectedStoryDetail.failed}</div>
                    <div className="text-[10px] uppercase font-bold text-red-600/70">Failed</div>
                  </div>
                  <div className="bg-blue-500/10 p-3 rounded border border-blue-500/20 text-center">
                    <div className="text-2xl font-bold text-blue-400">{selectedStoryDetail.duration}s</div>
                    <div className="text-[10px] uppercase font-bold text-blue-600/70">Duration</div>
                  </div>
               </div>

               <div className="space-y-2">
                  <h4 className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 mb-2">Scenarios</h4>
                  {selectedStoryDetail.scenarios.map((scen, idx) => (
                    <button
                      key={idx}
                      onClick={() => setReportModal({ isOpen: true, url: `http://localhost:8000${scen.report_url}`, storyId: selectedStoryDetail.story_id })}
                      className="w-full flex items-center justify-between p-3 bg-black/40 border border-zinc-800 rounded hover:border-zinc-600 transition-colors group text-left"
                    >
                      <div className="flex items-center gap-3">
                        {scen.status === 'passed' ? <CheckCircle2 size={16} className="text-green-500" /> : <XCircle size={16} className="text-red-500" />}
                        <span className={`text-sm ${scen.status === 'passed' ? 'text-zinc-300' : 'text-red-300'}`}>{scen.name}</span>
                      </div>
                      <ExternalLink size={14} className="text-zinc-600 group-hover:text-white transition-colors" />
                    </button>
                  ))}
               </div>
            </div>
          )}
        </div>
      </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardTab;
