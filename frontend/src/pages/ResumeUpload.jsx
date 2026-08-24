import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import { apiRequest } from '../api/client';
import Loading from '../components/Loading';
import ErrorBanner from '../components/ErrorBanner';
import { UploadCloud, FileText } from 'lucide-react';

export default function ResumeUpload() {
  const { userId } = useUser();
  const navigate = useNavigate();
  
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const data = await apiRequest('/api/v1/resume/parse', {
        method: 'POST',
        userId,
        body: formData,
        isFormData: true
      });
      
      // Navigate to skill input with pre-filled skills
      navigate('/', { state: { skills: data.extracted_skills } });
    } catch (err) {
      setError(err);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 text-center">
        <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <UploadCloud className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Upload Your Resume</h2>
        <p className="text-slate-500 mb-8">We'll extract your skills automatically using AI to find your best career matches.</p>

        <form onSubmit={handleUpload} className="space-y-6">
          <div className="border-2 border-dashed border-slate-300 rounded-xl p-8 hover:bg-slate-50 transition-colors relative">
            <input
              type="file"
              accept=".pdf,.docx"
              onChange={handleFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="flex flex-col items-center justify-center gap-2">
              <FileText className="w-10 h-10 text-slate-400" />
              <p className="text-sm font-medium text-slate-700">
                {file ? file.name : "Click or drag file to upload"}
              </p>
              <p className="text-xs text-slate-500">PDF or DOCX (max 5MB)</p>
            </div>
          </div>

          <ErrorBanner error={error} />

          <button
            type="submit"
            disabled={!file || loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {loading ? <Loading message="Extracting skills..." /> : "Analyze Resume"}
          </button>
        </form>
      </div>
    </div>
  );
}
