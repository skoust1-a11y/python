import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Send, Loader2, User, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useAuth0 } from '@auth0/auth0-react';
import { type ChatMessage, apiService, type PropertyData } from '../apiService';
import { PropertyCard } from './PropertyCard';
import { getWithoutHeaders } from '../network_utils/apiService';
import { fetchSessions } from '../network_utils/URL_CONSTANTS';

export const ChatComponent: React.FC = () => {
  const { getAccessTokenSilently } = useAuth0();
  const [messages, setMessages] = useState<ChatMessage[]>([{
    role: 'assistant',
    content: 'Hello! I am your Real Estate Assistant. How can I help you find your dream home today?'
  }]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  // const sessionIdNew = useMemo(() => window.crypto?.randomUUID?.() ?? `session-${Date.now()}`, []);
  const[sessionId,setSessionId] = useState("")


  useEffect(()=>{
  const gen_id = async() => {
    try{
      const res = await getWithoutHeaders(fetchSessions)
      if (res.ok){
        setSessionId(res.data.session_id)
      }
      else{
        setSessionId("")
      }    

    }
    catch(error){
      console.log("The Generate Id Error:",error)
    }
  }
  gen_id()

  },[])


  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = input.trim();
    setInput('');

    const userMessage: ChatMessage = { role: 'user', content: userMsg };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Placeholder for the assistant's response that we will update in real-time
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    let currentResponse = '';
    let currentProperties: PropertyData[] = [];

    try {
      const token = await getAccessTokenSilently();

      await apiService.streamChat(
        userMsg,
        sessionId,
        token,
        (chunk) => {
          currentResponse += chunk;
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              content: currentResponse
            };
            return updated;
          });
        }
      );
    } catch (error) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: 'assistant',
          content: 'Sorry, I encountered an error while processing your request. Please try again.'
        };
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100">
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-end gap-3`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-gradient-to-r from-purple-500 to-indigo-500 text-white'
                }`}>
                {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
              </div>

              <div className={`flex flex-col gap-3 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`px-4 py-3 rounded-2xl ${msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-none'
                    : 'bg-gray-100 text-gray-800 rounded-bl-none shadow-sm'
                  }`}>
                  {msg.role === 'user' ? (
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  ) : (
                    <div className="prose prose-sm max-w-none">
                      {msg.content ? (
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      ) : isLoading && index === messages.length - 1 ? (
                        <div className="flex items-center gap-1 h-5">
                          <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      ) : null}
                    </div>
                  )}
                </div>

                {/* {msg.properties && msg.properties.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full mt-2">
                    {msg.properties.map(prop => (
                      <PropertyCard key={prop.id} property={prop} />
                    ))}
                  </div>
                )} */}
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-gray-50 border-t border-gray-200">
        <form onSubmit={handleSubmit} className="flex gap-2 relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isLoading}
            className="flex-1 px-4 py-3 rounded-full border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white shadow-sm pr-12 transition-all duration-200"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="absolute right-1.5 top-1.5 bottom-1.5 aspect-square bg-indigo-600 text-white rounded-full flex items-center justify-center hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
          >
            {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </form>
      </div>
    </div>
  );
};
