// src/components/ChatComponent.tsx
import React, { useState, useEffect, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import ReactMarkdown from "react-markdown";
import { streamChatMessage } from "./apiService";
import "./styles.css";

interface Message {
  role: "user" | "assistant";
  content: string;
}

// Loading indicator component
const LoadingIndicator = () => (
  <div className="loading-indicator">
    <span>AI is processing</span>
    <div className="loading-dots">
      <div className="loading-dot"></div>
      <div className="loading-dot"></div>
      <div className="loading-dot"></div>
    </div>
  </div>
);

const ChatComponent: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize unique session
  useEffect(() => {
    setSessionId(uuidv4());
  }, []);

  // Auto-scroll when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const sendMessage = async () => {
    if (!input.trim() || !sessionId || isLoading) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    const userInput = input;
    setInput("");
    setIsLoading(true);

    // Add a placeholder assistant message for streaming updates
    const assistantIndex = messages.length + 1;
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);


// Task 1 : Display streaming AI responses received from backend 
// and handle errors gracefully.
// Task 1 : Display streaming AI responses received from backend 
// and handle errors gracefully.
  const contentRef = { current: '' };

    const updateContent = (newChunk: string) => {
      contentRef.current += newChunk;
      
      // Update immediately using the ref to avoid stale closures
      setMessages((prev) => {
        const updated = [...prev];
        // Find the last assistant message and update it with accumulated content
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].role === 'assistant') {
            updated[i] = {
              ...updated[i],
              content: contentRef.current, // Use ref value, not closure
            };
            break;
          }
        }
        return updated;
      });
    };

    try {
      await streamChatMessage(userInput, sessionId, (chunk) => {
        // Skip if chunk is "[DONE]" or "done"
        const normalizedChunk = chunk.toLowerCase().replace(/[\[\]]/g, '');
        if (normalizedChunk === 'done') {
          // Final update when done to ensure all content is displayed
          setMessages((prev) => {
            const updated = [...prev];
            for (let i = updated.length - 1; i >= 0; i--) {
              if (updated[i].role === 'assistant') {
                updated[i] = {
                  ...updated[i],
                  content: contentRef.current,
                };
                break;
              }
            }
            return updated;
          });
          return;
        }
        
        updateContent(chunk);
      });
    } catch (error) {
      setMessages((prev) => {
        const updated = [...prev];
        // Replace the last assistant message with error message
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].role === 'assistant') {
            updated[i] = {
              ...updated[i],
              content: 'Something went wrong while streaming the response.',
            };
            break;
          }
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };



  return (
    <div className="chat-container">
      <h2 className="title">Trip & Travel Planner Chat</h2>

      <div className="chat-box">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <strong>{msg.role === "user" ? "You: " : "Agent: "}</strong>
            {msg.role === "assistant" ? (
              <ReactMarkdown
                components={{
                  // Open links in new tab for better UX
                  a: ({ node, ...props }: any) => (
                    <a target="_blank" rel="noopener noreferrer" {...props} />
                  ),
                }}
              >
                {msg.content}
              </ReactMarkdown>
            ) : (
              msg.content
            )}
          </div>
        ))}
        {isLoading && (
          <div className="message assistant">
            <LoadingIndicator />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <input
          type="text"
          value={input}
          placeholder="Where would you like to go?"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          disabled={isLoading}
        />
        <button onClick={sendMessage} disabled={isLoading || !input.trim()}>
          {isLoading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
};

export default ChatComponent;
