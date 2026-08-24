import React, { useState } from 'react';
import { useUser } from '../context/UserContext';
import { apiRequest } from '../api/client';
import { Send, Bot, User } from 'lucide-react';

export default function Chat() {
  const { userId } = useUser();
  const [messages, setMessages] = useState([
    { role: 'ai', content: "Hello! I'm your AI career advisor. What questions do you have about your career matches or roadmap?" }
  ]);
  const [inputVal, setInputVal] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!inputVal.trim() || loading) return;

    const userMsg = inputVal.trim();
    setInputVal('');
    
    const newMessages = [...messages, { role: 'user', content: userMsg }];
    setMessages(newMessages);
    setLoading(true);

    try {
      const data = await apiRequest('/api/v1/chat/advise', {
        method: 'POST',
        userId,
        body: {
          message: userMsg,
          history: newMessages.map(m => ({ role: m.role, content: m.content }))
        }
      });
      
      setMessages([...newMessages, { role: 'ai', content: data.reply }]);
    } catch (err) {
      setMessages([...newMessages, { role: 'ai', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto h-[calc(100vh-12rem)] flex flex-col bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="bg-indigo-600 p-4 text-white flex items-center gap-3">
        <Bot className="w-6 h-6" />
        <h2 className="text-lg font-bold">Career Advisor AI</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 bg-slate-50">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
              msg.role === 'user' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-200 text-slate-700'
            }`}>
              {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
            </div>
            <div className={`px-4 py-3 rounded-2xl max-w-[80%] ${
              msg.role === 'user' 
                ? 'bg-indigo-600 text-white rounded-tr-sm' 
                : 'bg-white text-slate-800 border border-slate-200 rounded-tl-sm shadow-sm'
            }`}>
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-4">
            <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5" />
            </div>
            <div className="px-4 py-3 rounded-2xl bg-white border border-slate-200 rounded-tl-sm shadow-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 bg-white border-t border-slate-200">
        <form onSubmit={sendMessage} className="flex gap-2">
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Ask about skills, interviews, or career transitions..."
            className="flex-1 rounded-xl border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 py-3 px-4 border bg-slate-50"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!inputVal.trim() || loading}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white px-5 rounded-xl transition-colors flex items-center justify-center"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
