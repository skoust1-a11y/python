export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  properties?: PropertyData[];
}

interface ChatRequestBody {
  input: string;
  session_id: string;
}

export interface PropertyData {
  id: string | number;
  title: string;
  price: string;
  bhk: string;
  locality: string;
  amenities: string[];
  commuteInsights?: string;
  imageUrl?: string;
}

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:9000';

export const apiService = {
  // Use SSE for streaming chat responses
  async streamChat(
    message: string,
    sessionId: string,
    token: string,
    onChunk: (chunk: string) => void,
    onProperties?: (properties: PropertyData[]) => void
  ): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ input: message, session_id: sessionId }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      if (!response.body) {
        throw new Error('No readable stream available');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      
      if (buffer) {
        const lines = buffer.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          if (trimmed.startsWith('event:')) continue;
          if (trimmed.startsWith('data:')) {
            const data = trimmed.replace(/^data:\s*/, '');
            const normalized = data.toLowerCase().replace(/[\[\]]/g, '').trim();
            if (normalized === 'done') {
              return;
            }
            onChunk(data + '\n');
          } else {
            const normalized = trimmed.toLowerCase().replace(/[\[\]]/g, '').trim();
            if (normalized === 'done') {
              return;
            }
            const cleaned = trimmed.includes('data:')
              ? trimmed.substring(trimmed.indexOf('data:') + 5).trimStart()
              : trimmed;
            onChunk(cleaned + '\n');
          }
        }
      }
      break;
    }

    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;

      if (line.startsWith('data:')) {
        const data = line.substring(5).trimStart();
        const normalized = data.toLowerCase().replace(/[\[\]]/g, '').trim();
        if (normalized === 'done') {
          return;
        }
        onChunk(data + '\n');
      } else if (line.trim().startsWith('event:')) {
        continue;
      } else {
        const content = line.trim();
        if (!content) continue;
        const normalized = content.toLowerCase().replace(/[\[\]]/g, '').trim();
        if (normalized === 'done') {
          return;
        }
        const cleaned = content.includes('data:')
          ? content.substring(content.indexOf('data:') + 5).trimStart()
          : content;
        onChunk(cleaned + '\n');
      }
    }
  }
    } catch (error) {
      console.error('Error in streamChat:', error);
      throw error;
    }
  },
};


export async function streamChatMessage(
  input: string,
  sessionId: string,
  token: string,
  onMessage: (chunk: string) => void
): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
 
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }



  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ input, session_id: sessionId } as ChatRequestBody),
  });

  if (!response.ok || !response.body) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      
      if (buffer) {
        const lines = buffer.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          if (trimmed.startsWith('event:')) continue;
          if (trimmed.startsWith('data:')) {
            const data = trimmed.replace(/^data:\s*/, '');
            const normalized = data.toLowerCase().replace(/[\[\]]/g, '').trim();
            if (normalized === 'done') {
              return;
            }
            onMessage(data + '\n');
          } else {
            const normalized = trimmed.toLowerCase().replace(/[\[\]]/g, '').trim();
            if (normalized === 'done') {
              return;
            }
            const cleaned = trimmed.includes('data:')
              ? trimmed.substring(trimmed.indexOf('data:') + 5).trimStart()
              : trimmed;
            onMessage(cleaned + '\n');
          }
        }
      }
      break;
    }

    
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;

      if (line.startsWith('data:')) {
        const data = line.substring(5).trimStart();
        const normalized = data.toLowerCase().replace(/[\[\]]/g, '').trim();
        if (normalized === 'done') {
          return;
        }
        onMessage(data + '\n');
      } else if (line.trim().startsWith('event:')) {
        continue;
      } else {
        const content = line.trim();
        if (!content) continue;
        const normalized = content.toLowerCase().replace(/[\[\]]/g, '').trim();
        if (normalized === 'done') {
          return;
        }
        const cleaned = content.includes('data:')
          ? content.substring(content.indexOf('data:') + 5).trimStart()
          : content;
        onMessage(cleaned + '\n');
      }
    }
  }
}