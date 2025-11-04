# Travel Agent Frontend

A modern React-based chat interface for an AI-powered travel and trip planning assistant. This frontend provides an intuitive chat experience with **real-time streaming responses**, where users can interact with a travel bot to get personalized travel recommendations, itinerary suggestions, and trip planning assistance.

## Features

- **Interactive Chat Interface**: Clean, modern chat UI with real-time messaging
- **Real-Time Streaming**: Token-by-token streaming responses for immediate feedback
- **Markdown Support**: Rich text rendering for bot responses with full markdown formatting (headings, lists, code blocks, links, tables, etc.)
- **Session Management**: Unique session tracking for conversation continuity
- **Responsive Design**: Centered layout that works on all screen sizes
- **Loading Indicators**: Visual feedback during AI response generation
- **Auto-Scroll**: Automatically scrolls to latest messages
- **TypeScript**: Full type safety and better development experience
- **Modern UI**: Beautiful styling with hover effects and smooth interactions

## Tech Stack

- **React 19** - Modern React with hooks
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and development server
- **React Markdown** - Markdown rendering for rich text with custom styling
- **UUID** - Session ID generation
- **CSS3** - Modern styling with flexbox, animations, and markdown-specific styles

## Prerequisites

- Node.js (version 16 or higher)
- npm or yarn package manager
- Backend API running on `http://localhost:8000` (see backend README for setup)

---

## Running the Application

### Linux

```bash
cd frontend/react-frontend
npm install
npm run dev
```

The server will start on `http://localhost:5173` (or the next available port).

### Windows

**PowerShell:**
```powershell
cd frontend\react-frontend
npm install
npm run dev
```

**Command Prompt:**
```cmd
cd frontend\react-frontend
npm install
npm run dev
```

Open your browser and navigate to `http://localhost:5173`

## Usage

### Starting a Conversation

1. Open the application in your browser
2. A unique session ID is automatically generated when the page loads
3. Type your travel question in the input field (e.g., "Where should I go for a beach vacation?")
4. Press Enter or click the "Send" button
5. The AI travel bot will respond with personalized recommendations, **streaming token-by-token in real-time**

### Example Queries

- "I want to plan a 7-day trip to Europe"
- "What are the best beaches in Thailand?"
- "Suggest a budget-friendly vacation for a family of 4"
- "What should I pack for a winter trip to Japan?"
- "Create an itinerary for a 5-day adventure in New Zealand"

### Markdown Support

The AI responses support full markdown formatting:

- **Headings**: `# H1`, `## H2`, `### H3`
- **Bold and Italic**: `**bold**`, `*italic*`
- **Lists**: Ordered (`1. Item`) and unordered (`- Item`)
- **Code**: Inline `` `code` `` and code blocks
- **Links**: Automatic link rendering with new tab opening
- **Tables**: Full table support with styling
- **Blockquotes**: `> Quote text`
- **Horizontal Rules**: `---`

All markdown elements are beautifully styled to match the chat interface theme.

## 🔧 Development

### Available Scripts

- `npm run dev` - Start development server with hot reload (runs on port 5173)


### Project Structure

```
src/
├── ChatComponent.tsx    # Main chat interface component with streaming support
├── apiService.ts        # API communication layer with SSE streaming handling
├── App.tsx              # Root application component
├── main.tsx             # Application entry point
├── App.css              # Global app styles
├── index.css            # Base styles and CSS reset
└── styles.css           # Chat component styles + markdown styling
```

### Key Components

#### ChatComponent.tsx
The main chat interface that handles:
- Message state management with streaming updates
- User input handling
- Real-time streaming API communication
- Session management with UUID
- Markdown rendering for AI responses
- Loading states and visual feedback
- Auto-scroll to latest messages

#### apiService.ts
Handles communication with the backend API:
- **Streaming Message Handling**: Reads Server-Sent Events (SSE) from backend
- **ReadableStream Processing**: Parses streaming chunks using Fetch API
- **Real-Time Updates**: Calls callback function for each received token
- **Error Handling**: Graceful error handling for network issues

## Streaming Implementation

The frontend implements **real-time streaming** using the Fetch API's ReadableStream:

1. **Request**: Sends POST request to `/chat` endpoint with user input and session ID
2. **Stream Reading**: Reads response body as a stream using `getReader()`
3. **Token Processing**: Decodes chunks and parses SSE format (`data: {content}`)
4. **UI Updates**: Updates message content in real-time as tokens arrive
5. **Completion**: Handles `[DONE]` marker to stop streaming



## Styling

The application uses a clean, modern design with comprehensive markdown styling:

### Chat Interface
- **Centered Layout**: Chat container is centered on the page
- **Card-based Design**: Rounded corners and subtle shadows
- **Color-coded Messages**: 
  - User messages: Light blue background (`#e3f2fd`)
  - Bot messages: Light green background (`#f1f8e9`)
- **Responsive Input**: Flexible input area with send button
- **Loading States**: Animated loading indicator with bouncing dots

### Markdown Styling
- **Headings**: Blue colored headers with appropriate sizing
- **Code Blocks**: Gray background with border and padding
- **Inline Code**: Highlighted with pink color
- **Links**: Blue color with hover underline effect
- **Lists**: Proper indentation and spacing
- **Tables**: Bordered tables with header styling
- **Blockquotes**: Left border with italic text

### CSS Architecture

- `index.css` - Global styles and CSS reset
- `App.css` - Root container and global components
- `styles.css` - Chat-specific styling, markdown styles, and animations

## API Integration

The frontend communicates with a backend API through the `apiService.ts` module using **Server-Sent Events (SSE)**:

```typescript
// Streaming API call
await streamChatMessage(userInput, sessionId, (chunk) => {
  // Handle each token as it arrives
  updateMessage(chunk);
});
```

## Features in Detail

### Real-Time Streaming
- Tokens appear as they're generated by the AI
- No waiting for complete response
- Better user experience with immediate feedback

### Session Persistence
- Each browser session gets a unique UUID
- Conversation history maintained across messages
- Context-aware responses from the AI

### Error Handling
- Network errors display user-friendly messages
- Streaming interruptions are handled gracefully
- Input validation prevents empty messages

### Responsive Design
- Works on desktop and mobile devices
- Scrollable message area for long conversations
- Adaptive input area



### Build Configuration

The Vite configuration is in `vite.config.ts`. For production, you may want to:
- Set base path if deploying to a subdirectory
- Configure proxy for API calls during development
- Optimize build output

## Troubleshooting

### Common Issues

1. **Streaming Not Working**: 
   - Ensure backend is running on port 8000
   - Check browser console for CORS errors
   - Verify backend has streaming enabled

2. **Markdown Not Rendering**: 
   - Ensure `react-markdown` is installed
   - Check that CSS styles are imported
   - Verify message content is being passed correctly

3. **Session Not Persisting**: 
   - Session IDs are stored in component state
   - Refreshing the page will create a new session
   - This is expected behavior for in-memory sessions

4. **CORS Errors**: 
   - Ensure backend CORS middleware includes `http://localhost:5173`
   - Check that backend is running and accessible

5. **Port Already in Use**: 
   - Vite uses port 5173 by default
   - Use `npm run dev -- --port 3000` to use a different port

## Key Implementation Details

- **Streaming**: Uses Fetch API with ReadableStream for SSE handling
- **State Management**: React hooks (useState, useEffect, useRef) for local state
- **Markdown**: ReactMarkdown with custom component overrides for links
- **Session Management**: UUID generation on component mount
- **Auto-Scroll**: useEffect hook with scrollIntoView for smooth scrolling
- **Loading States**: Disabled inputs and loading indicators during API calls
