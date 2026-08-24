import React from 'react';
import { AlertCircle } from 'lucide-react';

export default function ErrorBanner({ error }) {
  if (!error) return null;
  
  return (
    <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-md flex items-start gap-3 my-4">
      <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
      <div>
        <h3 className="text-sm font-medium text-red-800">An error occurred</h3>
        <p className="text-sm text-red-700 mt-1">{error.message || error.toString()}</p>
      </div>
    </div>
  );
}
