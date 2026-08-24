import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Target, FileText, MessageSquare, Clock } from 'lucide-react';
import SkillInput from './pages/SkillInput';
import ResumeUpload from './pages/ResumeUpload';
import Roadmap from './pages/Roadmap';
import Chat from './pages/Chat';
import History from './pages/History';
import { UserProvider } from './context/UserContext';

function Navigation() {
  const location = useLocation();
  const path = location.pathname;

  const navItems = [
    { path: '/', label: 'Matches', icon: Target },
    { path: '/resume', label: 'Resume', icon: FileText },
    { path: '/chat', label: 'AI Advisor', icon: MessageSquare },
    { path: '/history', label: 'History', icon: Clock },
  ];

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="bg-indigo-600 text-white p-1.5 rounded-lg">
              <Target className="w-5 h-5" />
            </div>
            <span className="text-xl font-bold text-slate-800">BuildOnce</span>
          </div>
          <div className="flex gap-1 md:gap-4 overflow-x-auto no-scrollbar">
            {navItems.map(item => {
              const Icon = item.icon;
              const isActive = path === item.path || (item.path === '/' && path === '/roadmap');
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive 
                      ? 'bg-indigo-50 text-indigo-700' 
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden md:inline">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}

function App() {
  return (
    <UserProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
          <Navigation />
          <main className="flex-1 w-full max-w-6xl mx-auto p-4 md:p-8">
            <Routes>
              <Route path="/" element={<SkillInput />} />
              <Route path="/resume" element={<ResumeUpload />} />
              <Route path="/roadmap" element={<Roadmap />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/history" element={<History />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </UserProvider>
  );
}

export default App;
