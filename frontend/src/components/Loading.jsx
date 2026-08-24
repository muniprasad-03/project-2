import React from 'react';
import { Loader2 } from 'lucide-react';

export default function Loading({ message = "Loading..." }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 space-y-4 text-slate-500">
      <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      <p className="font-medium animate-pulse">{message}</p>
    </div>
  );
}
