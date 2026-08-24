import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Target, CheckCircle2, XCircle } from 'lucide-react';

export default function CareerCard({ jobTitle, matchPercentage, matchedSkills, missingSkills }) {
  const navigate = useNavigate();

  const handleGenerateRoadmap = () => {
    navigate('/roadmap', {
      state: {
        targetJobTitle: jobTitle,
        missingSkills: missingSkills
      }
    });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col gap-4">
      <div className="flex justify-between items-start">
        <h3 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <Target className="w-5 h-5 text-indigo-500" />
          {jobTitle}
        </h3>
        <span className="bg-emerald-100 text-emerald-800 text-sm font-semibold px-3 py-1 rounded-full">
          {matchPercentage}% Match
        </span>
      </div>

      <div className="space-y-4">
        <div>
          <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            Matched Skills ({matchedSkills?.length || 0})
          </h4>
          <div className="flex flex-wrap gap-2">
            {matchedSkills?.map(skill => (
              <span key={skill} className="bg-emerald-50 text-emerald-700 text-xs px-2 py-1 rounded border border-emerald-200">
                {skill}
              </span>
            ))}
            {!matchedSkills?.length && <span className="text-sm text-slate-400">None</span>}
          </div>
        </div>

        <div>
          <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-2">
            <XCircle className="w-4 h-4 text-amber-500" />
            Missing Skills ({missingSkills?.length || 0})
          </h4>
          <div className="flex flex-wrap gap-2">
            {missingSkills?.map(skill => (
              <span key={skill} className="bg-amber-50 text-amber-700 text-xs px-2 py-1 rounded border border-amber-200">
                {skill}
              </span>
            ))}
            {!missingSkills?.length && <span className="text-sm text-slate-400">None</span>}
          </div>
        </div>
      </div>

      <div className="pt-4 mt-auto border-t border-slate-100">
        <button
          onClick={handleGenerateRoadmap}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          Generate Learning Roadmap
        </button>
      </div>
    </div>
  );
}
