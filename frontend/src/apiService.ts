// src/apiService.ts

// Task 1: Define the API base URL and request body structure (input, session_id) 
// in your React app to connect with the FastAPI /chat endpoint
const API_BASE_URL : string = 'http://localhost:8000';

const CHAT_URL = API_BASE_URL + '/chat'

const SESSION_ID = API_BASE_URL + '/new-session'

interface ChatRequestBody {
  input: string;
  session_id: string;
}



//Task 2: Implement streamChatMessage() to send input and sessionId to /chat via fetch() and 
// validate the response before streaming.


//Tas 3: Read and decode streamed chunks from the response, parse lines for data: events, and update messages 
//in real time until [DONE] is received.

export async function streamChatMessage(
  input: string,
  sessionId: string,
  onMessage: (chunk: string) => void
): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };

  const response = await fetch(CHAT_URL, {
    method: 'POST',
    headers,
    body: JSON.stringify({ input, session_id: sessionId } as ChatRequestBody),
  });

  if (!response.ok || !response.body) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  // Read stream
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    
    if (done) {
      // Process any remaining buffer when stream ends
      if (buffer) {
        const lines = buffer.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed && trimmed.startsWith('data:')) {
            // Extract data after "data: " prefix, preserving content
            const data = trimmed.replace(/^data:\s*/, '');
            const normalizedData = data.toLowerCase().replace(/[\[\]]/g, '').trim();
            if (normalizedData === 'done') {
              return;
            }
            if (data) {
              // Preserve line breaks for proper markdown rendering
              onMessage(data + '\n');
            }
          } else if (trimmed) {
            // Fallback: accept non-SSE-prefixed content
            const normalizedLine = trimmed.toLowerCase().replace(/[\[\]]/g, '').trim();
            if (normalizedLine === 'done') {
              return;
            }
            // Strip stray "data:" if present within the line
            const cleaned = trimmed.includes('data:')
              ? trimmed.substring(trimmed.indexOf('data:') + 5).trimStart()
              : trimmed;
            // Preserve line breaks for proper markdown rendering
            onMessage(cleaned + '\n');
          }
        }
      }
      break;
    }

    // Decode chunk and add to buffer
    buffer += decoder.decode(value, { stream: true });
    
    // Process complete lines (ending with \n)
    const lines = buffer.split('\n');
    // Keep the last potentially incomplete line in buffer
    buffer = lines.pop() || '';

    for (const line of lines) {
      // Don't trim the line yet - we need to check if it starts with data:
      if (!line.trim()) {
        // Skip empty lines
        continue;
      }

      // Check if line starts with data: (case-sensitive for SSE)
      if (line.startsWith('data:')) {
        // Extract data after "data: " prefix
        // Use substring to preserve any leading/trailing spaces in the actual content
        const data = line.substring(5).trimStart(); // Remove "data:" prefix, keep content as-is
        
        // Check if this is the done signal
        const normalizedData = data.toLowerCase().replace(/[\[\]]/g, '').trim();
        if (normalizedData === 'done') {
          return;
        }
        
        // Call onMessage with the data (even if empty, as it might be intentional)
        // Preserve line breaks for proper markdown rendering
        onMessage(data + '\n');
      } else if (line.trim().startsWith('event:')) {
        // Ignore event lines
        continue;
      } else {
        // Fallback: accept non-SSE-prefixed lines
        const content = line.trim();
        if (!content) continue;
        const normalizedLine = content.toLowerCase().replace(/[\[\]]/g, '').trim();
        if (normalizedLine === 'done') {
          return;
        }
        // Strip stray "data:" if present within the line
        const cleaned = content.includes('data:')
          ? content.substring(content.indexOf('data:') + 5).trimStart()
          : content;
        // Preserve line breaks for proper markdown rendering
        onMessage(cleaned + '\n');
      }
      // Ignore any other lines (comments, etc.)
    }
  }
}
