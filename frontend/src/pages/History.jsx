import React, { useState, useEffect } from 'react';
import { useUser } from '../context/UserContext';
import { apiRequest } from '../api/client';
import Loading from '../components/Loading';
import ErrorBanner from '../components/ErrorBanner';
import { Bookmark, Clock, Trash2, Target } from 'lucide-react';

export default function History() {
  const { userId } = useUser();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHistory = async () => {
    try {
      const data = await apiRequest(`/api/v1/history/${userId}`);
      setHistory(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const toggleBookmark = async (id, currentStatus) => {
    try {
      // Optimistic update
      setHistory(prev => prev.map(item => 
        item.id === id ? { ...item, is_bookmarked: !currentStatus } : item
      ));
      
      await apiRequest(`/api/v1/bookmark/${id}`, { method: 'POST', userId });
    } catch (err) {
      // Revert on error
      fetchHistory();
      console.error(err);
    }
  };

  const clearHistory = async () => {
    if (!window.confirm("Are you sure you want to delete all history?")) return;
    
    try {
      await apiRequest(`/api/v1/history/${userId}`, { method: 'DELETE', userId });
      setHistory([]);
    } catch (err) {
      console.error(err);
      alert("Failed to clear history.");
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
          <Clock className="w-8 h-8 text-indigo-500" />
          Your History
        </h2>
        {history.length > 0 && (
          <button 
            onClick={clearHistory}
            className="text-red-600 hover:bg-red-50 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" /> Clear All
          </button>
        )}
      </div>

      <ErrorBanner error={error} />

      {loading ? (
        <Loading message="Loading history..." />
      ) : history.length === 0 ? (
        <div className="bg-white p-12 text-center rounded-2xl shadow-sm border border-slate-200 text-slate-500">
          <Clock className="w-12 h-12 mx-auto text-slate-300 mb-4" />
          <p className="text-lg font-medium">No history found.</p>
          <p className="text-sm mt-1">Your generated recommendations will appear here.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {history.map((item) => (
            <div key={item.id} className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-5 h-5 text-indigo-500" />
                  <h3 className="font-bold text-slate-800 text-lg">{item.job_title}</h3>
                  <span className="bg-emerald-100 text-emerald-800 text-xs font-bold px-2 py-1 rounded-full ml-2">
                    {item.match_percentage}% Match
                  </span>
                </div>
                <p className="text-sm text-slate-500">
                  {new Date(item.timestamp).toLocaleString()}
                </p>
                <div className="mt-3 flex gap-2">
                  {item.roadmap ? (
                    <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-1 rounded border border-indigo-100 font-medium">
                      Roadmap Generated
                    </span>
                  ) : null}
                  {item.missing_skills.length > 0 && (
                    <span className="text-xs bg-amber-50 text-amber-700 px-2 py-1 rounded border border-amber-100 font-medium">
                      {item.missing_skills.length} Missing Skills
                    </span>
                  )}
                </div>
              </div>
              
              <button
                onClick={() => toggleBookmark(item.id, item.is_bookmarked)}
                className={`p-3 rounded-full transition-colors ${
                  item.is_bookmarked 
                    ? 'bg-amber-100 text-amber-600 hover:bg-amber-200' 
                    : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
                }`}
              >
                <Bookmark className="w-6 h-6" fill={item.is_bookmarked ? "currentColor" : "none"} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
