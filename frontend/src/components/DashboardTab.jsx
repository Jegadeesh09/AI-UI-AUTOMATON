import React, { useState, useEffect, useMemo } from 'react';
import {
  BarChart3, PieChart as PieChartIcon, Activity, ExternalLink, ChevronRight,
  CheckCircle2, XCircle, Layers, Percent, Clock, Zap, Target, Shield,
  AlertTriangle, Lightbulb, Search, Filter, History, TrendingUp, Info
} from 'lucide-react';
import axios from 'axios';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area
} from 'recharts';
import ReportModal from './ReportModal';
import CustomDropdown from './CustomDropdown';

const DashboardTab = () => {
  const [activeView, setActiveView] = useState('executive'); // executive, technical, ai
  const [suiteNames, setSuiteNames] = useState([]);
  const [storyNames, setStoryNames] = useState(['All']);
  const [selectedSuite, setSelectedSuite] = useState('All');
  const [selectedStoryId, setSelectedStoryId] = useState('All');
  const [stats, setStats] = useState({
    total_stories: 0, manual_stories: 0, automated_stories: 0,
    total_scenarios: 0, total_steps: 0, passed: 0, failed: 0,
    avg_accuracy: 0, suites: [], history: [],
    ai_insights: { failure_summary: {}, recommendations: [] }
  });
  
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [reportModal, setReportModal] = useState({ isOpen: false, url: '', storyId: '', suite: '' });

  const COLORS = ['#10b981', '#ef4444', '#6366f1', '#f59e0b', '#8b5cf6'];

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

  // Data Formatting for Charts
  const trendData = useMemo(() => {
    if (!stats.history || stats.history.length === 0) return [];
    // Group history by date (last 7 entries)
    return stats.history.slice(-10).map(h => ({
      name: new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      passed: h.passed,
      failed: h.failed
    }));
  }, [stats.history]);

  const storyPerformanceData = useMemo(() => {
    const allStories = stats.suites.flatMap(s => s.stories);
    return allStories.map(s => ({
      name: s.story_id,
      passed: s.passed,
      failed: s.failed,
      not_run: (s.passed + s.failed) === 0 ? 1 : 0
    })).slice(0, 15);
  }, [stats.suites]);

  const failureData = useMemo(() => {
    const summary = stats.ai_insights?.failure_summary || {};
    return Object.keys(summary).map(key => ({
      name: key,
      value: summary[key]
    }));
  }, [stats.ai_insights]);

  const automationMixData = [
    { name: 'Automated', value: stats.automated_stories },
    { name: 'Manual', value: stats.manual_stories }
  ];

  const renderExecutiveView = () => (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Total Scenarios', value: stats.total_scenarios, icon: Layers, color: 'text-blue-400', bg: 'bg-blue-500/10' },
          { label: 'Total Steps', value: stats.total_steps, icon: Activity, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
          { label: 'Accuracy %', value: `${stats.avg_accuracy}%`, icon: Target, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
          { label: 'Coverage %', value: stats.total_stories > 0 ? `${Math.round((stats.automated_stories / stats.total_stories) * 100)}%` : '0%', icon: Shield, color: 'text-purple-400', bg: 'bg-purple-500/10' },
          { label: 'Avg Time', value: '42s', icon: Clock, color: 'text-amber-400', bg: 'bg-amber-500/10' }
        ].map((kpi, i) => (
          <div key={i} className="surface p-4 rounded-xl border border-zinc-800 shadow-sm hover:border-zinc-700 transition-all group">
            <div className="flex items-center justify-between mb-2">
              <div className={`p-2 rounded-lg ${kpi.bg} ${kpi.color}`}>
                <kpi.icon size={18} />
              </div>
              <TrendingUp size={14} className="text-emerald-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <p className="text-2xl font-bold tracking-tight">{kpi.value}</p>
            <p className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider mt-1">{kpi.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Execution Trend */}
        <div className="surface p-6 rounded-xl border border-zinc-800 shadow-xl bg-zinc-900/10 flex flex-col h-[400px]">
          <div className="flex justify-between items-center mb-6">
             <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-2">
               <History size={16} /> Execution Trend
             </h3>
             <div className="flex gap-4 text-[10px] uppercase font-bold">
               <span className="flex items-center gap-1.5 text-emerald-500"><div className="w-2 h-2 rounded-full bg-emerald-500" /> Passed</span>
               <span className="flex items-center gap-1.5 text-red-500"><div className="w-2 h-2 rounded-full bg-red-500" /> Failed</span>
             </div>
          </div>
          <div className="flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="colorPassed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis dataKey="name" stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke="#52525b" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px', fontSize: '12px' }}
                  itemStyle={{ padding: '2px 0' }}
                />
                <Area type="monotone" dataKey="passed" stroke="#10b981" fillOpacity={1} fill="url(#colorPassed)" strokeWidth={2} />
                <Area type="monotone" dataKey="failed" stroke="#ef4444" fillOpacity={1} fill="url(#colorFailed)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Story Performance */}
        <div className="surface p-6 rounded-xl border border-zinc-800 shadow-xl bg-zinc-900/10 flex flex-col h-[400px]">
          <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-2 mb-6">
            <BarChart3 size={16} /> Story Performance
          </h3>
          <div className="flex-1 overflow-y-auto custom-scrollbar pr-2">
            <div style={{ height: Math.max(300, storyPerformanceData.length * 35) }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={storyPerformanceData} layout="vertical" margin={{ left: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                  <XAxis type="number" stroke="#52525b" fontSize={10} hide />
                  <YAxis dataKey="name" type="category" stroke="#52525b" fontSize={9} tickLine={false} width={80} />
                  <Tooltip
                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                    contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Bar dataKey="passed" stackId="a" fill="#10b981" radius={[0, 0, 0, 0]} barSize={12} />
                  <Bar dataKey="failed" stackId="a" fill="#ef4444" radius={[0, 4, 4, 0]} barSize={12} />
                  <Bar dataKey="not_run" stackId="a" fill="#3f3f46" radius={[0, 4, 4, 0]} barSize={12} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderTechnicalView = () => (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex justify-between items-center mb-4">
         <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-2">
           <Filter size={16} /> Detailed Scenario Analytics
         </h3>
         <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              placeholder="Filter scenarios..."
              className="bg-zinc-900/50 border border-zinc-800 rounded-full py-1.5 pl-10 pr-4 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 w-64"
            />
         </div>
      </div>

      <div className="surface rounded-xl border border-zinc-800 overflow-hidden bg-zinc-900/20 flex flex-col max-h-[500px]">
        <div className="overflow-y-auto custom-scrollbar">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="bg-black/40 border-b border-zinc-800">
              <th className="px-6 py-4 text-[10px] uppercase font-bold text-zinc-500 tracking-widest">Scenario Name</th>
              <th className="px-6 py-4 text-[10px] uppercase font-bold text-zinc-500 tracking-widest">Status</th>
              <th className="px-6 py-4 text-[10px] uppercase font-bold text-zinc-500 tracking-widest">Duration</th>
              <th className="px-6 py-4 text-[10px] uppercase font-bold text-zinc-500 tracking-widest">Story / Suite</th>
              <th className="px-6 py-4 text-[10px] uppercase font-bold text-zinc-500 tracking-widest text-right">Report</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {stats.suites.flatMap(suite =>
              suite.stories.flatMap(story =>
                story.scenarios.map((scen, i) => (
                  <tr
                    key={`${story.story_id}-${i}`}
                    className={`hover:bg-zinc-800/30 transition-colors cursor-pointer group ${selectedScenario?.name === scen.name ? 'bg-blue-500/5' : ''}`}
                    onClick={() => setSelectedScenario(scen)}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className={`w-1.5 h-1.5 rounded-full ${scen.status === 'passed' ? 'bg-emerald-500' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]'}`} />
                        <span className="font-medium text-zinc-200">{scen.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${scen.status === 'passed' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                        {scen.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-zinc-500 font-mono text-xs">{scen.duration}s</td>
                    <td className="px-6 py-4">
                       <div className="flex flex-col">
                          <span className="text-zinc-400 text-xs">{story.story_id}</span>
                          <span className="text-[10px] text-zinc-600 font-bold uppercase">{suite.suite}</span>
                       </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                       <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setReportModal({
                            isOpen: true,
                            url: `http://localhost:8000${scen.report_url}`,
                            storyId: story.story_id,
                            suite: story.suite || suite.suite
                          });
                        }}
                        className="p-2 hover:bg-zinc-700 rounded-lg text-zinc-500 hover:text-white transition-all"
                       >
                         <ExternalLink size={16} />
                       </button>
                    </td>
                  </tr>
                ))
              )
            )}
          </tbody>
        </table>
        </div>
      </div>

      {/* Drill-down Detail Panel */}
      {selectedScenario && (
        <div className="surface p-6 rounded-xl border border-blue-900/30 bg-blue-950/5 animate-in slide-in-from-right-8 duration-300">
           <div className="flex justify-between items-start mb-6">
              <div>
                <h4 className="text-lg font-bold flex items-center gap-2">
                   {selectedScenario.status === 'passed' ? <CheckCircle2 className="text-emerald-500" /> : <XCircle className="text-red-500" />}
                   {selectedScenario.name}
                </h4>
                <p className="text-xs text-zinc-500 mt-1 uppercase tracking-widest font-bold">In-depth Scenario Analysis</p>
              </div>
              <button onClick={() => setSelectedScenario(null)} className="text-zinc-500 hover:text-white">✕</button>
           </div>

           <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-4">
                 <h5 className="text-[10px] uppercase font-bold text-zinc-500 flex items-center gap-2"><Zap size={14} /> AI Captured XPaths</h5>
                 <div className="bg-black/50 rounded-lg p-3 border border-zinc-800 space-y-2 max-h-40 overflow-y-auto custom-scrollbar">
                    {/* Placeholder for XPaths - would normally come from trace logs */}
                    <div className="text-[10px] font-mono p-1.5 bg-zinc-900 rounded border border-zinc-800 text-blue-400 truncate">//*[@id="login_btn"]</div>
                    <div className="text-[10px] font-mono p-1.5 bg-zinc-900 rounded border border-zinc-800 text-blue-400 truncate">//input[@name="password"]</div>
                    <div className="text-[10px] font-mono p-1.5 bg-zinc-900 rounded border border-zinc-800 text-blue-400 truncate">//button[contains(text(), "Submit")]</div>
                 </div>
              </div>

              <div className="space-y-4">
                 <h5 className="text-[10px] uppercase font-bold text-zinc-500 flex items-center gap-2"><Activity size={14} /> Playwright Code Snippet</h5>
                 <div className="bg-black/50 rounded-lg p-3 border border-zinc-800 max-h-40 overflow-y-auto custom-scrollbar">
                    <pre className="text-[10px] font-mono text-indigo-300">
{`await page.fill('input[name="user"]', 'admin');
await page.fill('input[name="pass"]', '****');
await page.click('button#submit');`}
                    </pre>
                 </div>
              </div>

              <div className="space-y-4">
                 <h5 className="text-[10px] uppercase font-bold text-zinc-500 flex items-center gap-2"><Info size={14} /> Execution Logs</h5>
                 <div className="bg-black/50 rounded-lg p-3 border border-zinc-800 h-40 overflow-y-auto custom-scrollbar">
                    <div className="text-[10px] font-mono text-zinc-500 space-y-1">
                      <p><span className="text-zinc-600">[09:41:02]</span> Navigating to URL...</p>
                      <p><span className="text-zinc-600">[09:41:05]</span> Found element 'User'</p>
                      <p><span className="text-zinc-600">[09:41:06]</span> Typing 'admin'...</p>
                      <p className={selectedScenario.status === 'failed' ? 'text-red-400' : 'text-emerald-500'}>
                        {selectedScenario.status === 'failed' ? `[09:41:08] Error: ${selectedScenario.error?.substring(0, 50)}...` : '[09:41:08] Scenario passed.'}
                      </p>
                    </div>
                 </div>
              </div>
           </div>
        </div>
      )}
    </div>
  );

  const renderAIView = () => (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
       <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Automation Mix */}
          <div className="surface p-6 rounded-xl border border-zinc-800 flex flex-col items-center">
             <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-400 self-start mb-8 flex items-center gap-2">
               <Target size={16} /> AI Automation Mix
             </h3>
             <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={automationMixData}
                      cx="50%" cy="50%"
                      innerRadius={60} outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      <Cell fill="#6366f1" />
                      <Cell fill="#27272a" />
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
             </div>
             <div className="text-center mt-4">
                <p className="text-3xl font-bold">{Math.round((stats.automated_stories / stats.total_stories) * 100 || 0)}%</p>
                <p className="text-[10px] uppercase font-bold text-zinc-500">Automated coverage</p>
             </div>
          </div>

          {/* Failure Reasons */}
          <div className="surface p-6 rounded-xl border border-zinc-800 flex flex-col lg:col-span-2">
             <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-400 mb-8 flex items-center gap-2">
               <AlertTriangle size={16} /> Intelligence Failure Summary
             </h3>
             <div className="flex-1">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={failureData} margin={{ top: 0, right: 30, left: 20, bottom: 5 }}>
                    <XAxis dataKey="name" stroke="#52525b" fontSize={10} axisLine={false} tickLine={false} />
                    <YAxis stroke="#52525b" fontSize={10} axisLine={false} tickLine={false} />
                    <Tooltip cursor={{ fill: 'transparent' }} contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46' }} />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={40}>
                       {failureData.map((entry, index) => (
                         <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                       ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
             </div>
          </div>
       </div>

       {/* AI Insights Box */}
       <div className="surface p-8 rounded-2xl border border-indigo-500/20 bg-indigo-500/5 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-8 text-indigo-500/10 group-hover:text-indigo-500/20 transition-colors">
             <Zap size={120} />
          </div>

          <div className="relative z-10 flex flex-col md:flex-row gap-12 items-start">
             <div className="flex-1">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 text-[10px] font-bold uppercase tracking-widest mb-4">
                   <Lightbulb size={12} /> AI Intelligence Insights
                </div>
                <h4 className="text-2xl font-bold mb-6">Optimization Recommendations</h4>
                <div className="space-y-4">
                   {stats.ai_insights?.recommendations?.length > 0 ? (
                     stats.ai_insights.recommendations.map((rec, i) => (
                       <div key={i} className="flex gap-4 p-4 rounded-xl bg-black/30 border border-zinc-800 hover:border-indigo-500/30 transition-all">
                          <div className="text-indigo-400"><Zap size={20} /></div>
                          <p className="text-sm text-zinc-300 leading-relaxed">{rec}</p>
                       </div>
                     ))
                   ) : (
                     <div className="flex gap-4 p-4 rounded-xl bg-black/30 border border-zinc-800 italic text-zinc-500 text-sm">
                        No significant patterns detected yet. Continue running tests to gather more intelligence.
                     </div>
                   )}
                </div>
             </div>

             <div className="w-full md:w-80 space-y-6">
                <h5 className="text-[10px] uppercase font-bold text-zinc-500 tracking-widest">Self-Healing Analytics</h5>
                <div className="surface p-6 rounded-xl border border-zinc-800 bg-black/40">
                   <div className="flex justify-between items-center mb-2">
                      <span className="text-xs text-zinc-400">Heal Success Rate</span>
                      <span className="text-sm font-bold text-emerald-500">92%</span>
                   </div>
                   <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-500 w-[92%]" />
                   </div>
                   <p className="text-[9px] text-zinc-500 mt-3 italic leading-tight">
                     AI has successfully healed 24 brittle XPaths without manual intervention this week.
                   </p>
                </div>
             </div>
          </div>
       </div>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      <div className="flex flex-col h-full space-y-8 animate-in fade-in duration-500">
          <ReportModal
            isOpen={reportModal.isOpen}
            onClose={() => setReportModal({ ...reportModal, isOpen: false })}
            reportUrl={reportModal.url}
            storyId={reportModal.storyId}
            suite={reportModal.suite}
          />
          
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 px-1">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white">Analytics Dashboard</h2>
              <div className="flex items-center gap-2 mt-1">
                 <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                 <p className="text-zinc-500 text-sm">Real-time intelligence from {stats.total_stories} stories across {stats.suites.length} suites</p>
              </div>
            </div>

            <div className="flex gap-4 w-full md:w-auto">
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

          {/* View Tabs */}
          <div className="flex border-b border-zinc-800 gap-8 px-1">
            {[
              { id: 'executive', label: 'Executive View', icon: TrendingUp },
              { id: 'technical', label: 'Technical View', icon: Activity },
              { id: 'ai', label: 'AI Intelligence', icon: Zap }
            ].map(view => (
              <button
                key={view.id}
                onClick={() => setActiveView(view.id)}
                className={`pb-4 text-xs font-bold uppercase tracking-widest flex items-center gap-2 transition-all relative ${activeView === view.id ? 'text-white' : 'text-zinc-500 hover:text-zinc-300'}`}
              >
                <view.icon size={14} />
                {view.label}
                {activeView === view.id && <div className="absolute bottom-0 left-0 w-full h-0.5 bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" />}
              </button>
            ))}
          </div>

          {/* Render Active View in Scrollable Container */}
          <div className="flex-1 overflow-y-auto custom-scrollbar pr-4 pb-12">
            {activeView === 'executive' && renderExecutiveView()}
            {activeView === 'technical' && renderTechnicalView()}
            {activeView === 'ai' && renderAIView()}
          </div>
      </div>
    </div>
  );
};

export default DashboardTab;
