import { useState, useRef, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import ReactMarkdown from 'react-markdown';
import { Send, LogIn, LogOut, Home, MapPin, Building } from 'lucide-react';
import './App.css'; // Optional extra styles, using index.css mainly

type Message = {
  id: string;
  sender: 'user' | 'agent';
  text: string;
};

// Generate a random session ID once per page load
const SESSION_ID = Math.random().toString(36).substring(2, 15);

function App() {
  const { loginWithRedirect, logout, user, isAuthenticated, isLoading, getAccessTokenSilently } = useAuth0();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'agent',
      text: "Hello! I'm your AI Real Estate Assistant. Let me know what kind of home you're looking for, your budget, and any preferred locations!"
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputValue.trim() || isTyping) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: inputValue.trim(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsTyping(true);

    try {
      const token = await getAccessTokenSilently();

      const response = await fetch('http://localhost:9000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query: userMsg.text,
          session_id: SESSION_ID
        })
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }

      const data = await response.json();

      const agentMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'agent',
        text: data.response
      };

      setMessages(prev => [...prev, agentMsg]);

    } catch (error) {
      console.error(error);
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'agent',
        text: "I'm sorry, I encountered an error connecting to the server. Please ensure the backend is running and you are logged in."
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  // Pre-process markdown to wrap property options in stylized div containers
  const preprocessMarkdown = (text: string) => {
    // Look for Option X: and wrap the whole block until double newline
    // This is a simple regex to make them look like cards
    let processed = text;
    // Replace Option headers to add some markdown bolding if they aren't already
    processed = processed.replace(/Option (\d+):/g, '### 🏠 Option $1:');
    return processed;
  };

  if (isLoading) {
    return (
      <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div className="loader" style={{ width: '50px', height: '50px' }}></div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <header>
        <div className="logo">
          <Building style={{ display: 'inline', marginRight: '8px', verticalAlign: 'text-bottom' }} />
          C2 EstateAssist
        </div>
        <div>
          {isAuthenticated ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                {user?.name || user?.email}
              </span>
              <button className="btn btn-secondary" onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}>
                <LogOut size={16} style={{ marginRight: '8px', verticalAlign: 'text-bottom' }} />
                Logout
              </button>
            </div>
          ) : (
            <button
              className="btn"
              onClick={() => {
                console.log("Login button clicked");
                loginWithRedirect().catch((err) => console.error("Login failed:", err));
              }}
            >
              <LogIn size={16} style={{ marginRight: '8px', verticalAlign: 'text-bottom' }} />
              Login
            </button>
          )}
        </div>
      </header>

      {!isAuthenticated ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '2rem' }}>
          <Home size={64} color="var(--accent-color)" style={{ marginBottom: '1rem' }} />
          <h1 style={{ marginBottom: '1rem', fontSize: '2.5rem' }}>Find Your Dream Home</h1>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', lineHeight: '1.6', marginBottom: '2rem' }}>
            Our AI-powered real estate assistant helps you discover suitable homes based on budget, commute preferences, lifestyle needs, and neighborhood insights.
          </p>
          <button className="btn" style={{ padding: '1rem 2rem', fontSize: '1.1rem' }} onClick={() => {
            console.log("Attempting to redirect to Auth0...");
            loginWithRedirect().catch(err => console.error("Login failed:", err));
          }}>
            Log in to get started
          </button>
        </div>
      ) : (
        <>
          <div className="chat-container">
            {messages.map((msg) => (
              <div key={msg.id} className={`message ${msg.sender}`}>
                <div className="message-bubble">
                  {msg.sender === 'agent' ? (
                    <ReactMarkdown
                      components={{
                        h3: ({ node, ...props }) => {
                          // If it's a property option, style it as a card header
                          const isOption = typeof props.children === 'string' && props.children.includes('Option');
                          return <h3 className={isOption ? "property-title" : ""} {...props} />
                        },
                        li: ({ node, ...props }) => {
                          return (
                            <li className="property-detail">
                              <MapPin size={14} color="#3b82f6" style={{ flexShrink: 0 }} />
                              <span>{props.children}</span>
                            </li>
                          )
                        }
                      }}
                    >
                      {preprocessMarkdown(msg.text)}
                    </ReactMarkdown>
                  ) : (
                    msg.text
                  )}
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="message agent">
                <div className="message-bubble typing-indicator">
                  Agent is thinking <div className="dot-flashing"></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="input-area">
            <form className="input-form" onSubmit={handleSend}>
              <input
                type="text"
                className="chat-input"
                placeholder="E.g., I'm looking for an apartment in Mumbai near schools..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={isTyping}
              />
              <button
                type="submit"
                className="send-btn"
                disabled={!inputValue.trim() || isTyping}
                title="Send message"
              >
                {isTyping ? <div className="loader" /> : <Send size={20} />}
              </button>
            </form>
          </div>
        </>
      )}
    </div>
  );
}

export default App;
