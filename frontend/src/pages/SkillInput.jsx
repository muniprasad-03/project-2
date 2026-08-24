import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import { apiRequest } from '../api/client';
import CareerCard from '../components/CareerCard';
import Loading from '../components/Loading';
import ErrorBanner from '../components/ErrorBanner';
import { Plus, X, Search } from 'lucide-react';

export default function SkillInput() {
  const { userId } = useUser();
  const location = useLocation();
  const [skills, setSkills] = useState([]);
  const [inputVal, setInputVal] = useState('');
  const [topK, setTopK] = useState(5);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  // Check if we came from resume upload with pre-filled skills
  useEffect(() => {
    if (location.state?.skills && Array.isArray(location.state.skills)) {
      setSkills(location.state.skills);
      // Auto-submit if we have skills
      fetchRecommendations(location.state.skills, topK);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state]);

  const handleAddSkill = (e) => {
    e.preventDefault();
    if (inputVal.trim() && !skills.includes(inputVal.trim())) {
      setSkills([...skills, inputVal.trim()]);
    }
    setInputVal('');
  };

  const removeSkill = (skillToRemove) => {
    setSkills(skills.filter(s => s !== skillToRemove));
  };

  const fetchRecommendations = async (skillsToUse, k) => {
    if (skillsToUse.length === 0) return;
    
    setLoading(true);
    setError(null);
    try {
      const data = await apiRequest('/api/v1/recommend/skills', {
        method: 'POST',
        userId,
        body: {
          user_skills: skillsToUse,
          top_k: parseInt(k)
        }
      });
      setResults(data.matches);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    fetchRecommendations(skills, topK);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-slate-200">
        <h2 className="text-2xl font-bold text-slate-800 mb-6">Find Your Career Path</h2>
        
        <form onSubmit={handleAddSkill} className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Add your skills (e.g., Python, Project Management)
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              className="flex-1 rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-4 py-2 border"
              placeholder="Type a skill and press Enter"
            />
            <button
              type="submit"
              className="bg-slate-100 text-slate-600 hover:bg-slate-200 px-4 py-2 rounded-lg transition-colors flex items-center gap-1"
            >
              <Plus className="w-4 h-4" /> Add
            </button>
          </div>
        </form>

        {skills.length > 0 && (
          <div className="mb-8 p-4 bg-slate-50 rounded-lg border border-slate-100">
            <h3 className="text-sm font-medium text-slate-500 mb-3 uppercase tracking-wider">Your Skills</h3>
            <div className="flex flex-wrap gap-2">
              {skills.map(skill => (
                <span key={skill} className="bg-white text-indigo-700 px-3 py-1.5 rounded-full border border-indigo-100 flex items-center gap-2 text-sm font-medium shadow-sm">
                  {skill}
                  <button onClick={() => removeSkill(skill)} className="text-indigo-400 hover:text-indigo-600 focus:outline-none">
                    <X className="w-4 h-4" />
                  </button>
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center gap-4 justify-between pt-6 border-t border-slate-100">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-700">Results to show:</label>
            <select 
              value={topK} 
              onChange={(e) => setTopK(e.target.value)}
              className="rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-1.5 pl-3 pr-8 border"
            >
              <option value="3">3</option>
              <option value="5">5</option>
              <option value="10">10</option>
            </select>
          </div>
          
          <button
            onClick={handleSubmit}
            disabled={skills.length === 0 || loading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-medium py-2 px-6 rounded-lg transition-colors flex items-center gap-2"
          >
            {loading ? <Loading message="Matching..." /> : <><Search className="w-4 h-4" /> Get Recommendations</>}
          </button>
        </div>
      </div>

      <ErrorBanner error={error} />

      {loading && <Loading message="Analyzing your skills against thousands of careers..." />}

      {!loading && results && (
        <div className="space-y-6">
          <h3 className="text-xl font-bold text-slate-800">Top Career Matches</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {results.map((match, idx) => (
              <CareerCard
                key={idx}
                jobTitle={match.job_title}
                matchPercentage={match.match_percentage}
                matchedSkills={match.matched_skills}
                missingSkills={match.missing_skills}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
