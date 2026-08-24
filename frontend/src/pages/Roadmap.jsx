import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import { apiRequest } from '../api/client';
import Loading from '../components/Loading';
import ErrorBanner from '../components/ErrorBanner';
import { Map, ArrowLeft, ExternalLink } from 'lucide-react';

export default function Roadmap() {
  const location = useLocation();
  const navigate = useNavigate();
  const { userId } = useUser();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [roadmap, setRoadmap] = useState(null);

  const targetJobTitle = location.state?.targetJobTitle;
  const missingSkills = location.state?.missingSkills;

  useEffect(() => {
    if (!targetJobTitle || !missingSkills) {
      navigate('/');
      return;
    }

    const generateRoadmap = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiRequest('/api/v1/roadmap/generate', {
          method: 'POST',
          userId,
          body: {
            target_job_title: targetJobTitle,
            missing_skills: missingSkills
          }
        });
        setRoadmap(data.roadmap);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    generateRoadmap();
  }, [targetJobTitle, missingSkills, userId, navigate]);

  if (!targetJobTitle) return null;

  return (
    <div className="max-w-3xl mx-auto">
      <button 
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-slate-500 hover:text-slate-800 mb-6 font-medium transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to matches
      </button>

      <div className="mb-8">
        <h2 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
          <Map className="w-8 h-8 text-indigo-500" />
          Roadmap to {targetJobTitle}
        </h2>
        <p className="text-slate-500 mt-2 text-lg">
          Your personalized learning path to acquire {missingSkills?.length} missing skills.
        </p>
      </div>

      <ErrorBanner error={error} />

      {loading && (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-200">
          <Loading message="Generating your personalized weekly roadmap using AI..." />
        </div>
      )}

      {roadmap && (
        <div className="space-y-6">
          {roadmap.map((week, idx) => (
            <div key={idx} className="bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-slate-200">
              <h3 className="text-xl font-bold text-indigo-900 mb-4 pb-4 border-b border-slate-100 flex items-center gap-3">
                <span className="bg-indigo-100 text-indigo-700 w-8 h-8 rounded-full flex items-center justify-center text-sm">
                  {idx + 1}
                </span>
                {week.week}
              </h3>
              
              <div className="space-y-6">
                <div>
                  <h4 className="font-semibold text-slate-700 mb-2">Focus Areas</h4>
                  <ul className="list-disc pl-5 space-y-1 text-slate-600">
                    {week.focus.map((item, i) => <li key={i}>{item}</li>)}
                  </ul>
                </div>
                
                <div>
                  <h4 className="font-semibold text-slate-700 mb-2">Actionable Tasks</h4>
                  <ul className="space-y-2">
                    {week.tasks.map((task, i) => (
                      <li key={i} className="flex items-start gap-3 text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
                        <div className="w-5 h-5 rounded border border-slate-300 bg-white shrink-0 mt-0.5"></div>
                        <span>{task}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                
                <div>
                  <h4 className="font-semibold text-slate-700 mb-2">Resources</h4>
                  <div className="flex flex-wrap gap-2">
                    {week.resources.map((res, i) => (
                      <span key={i} className="inline-flex items-center gap-1.5 text-sm bg-blue-50 text-blue-700 px-3 py-1.5 rounded-full border border-blue-100">
                        {res} <ExternalLink className="w-3 h-3" />
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
