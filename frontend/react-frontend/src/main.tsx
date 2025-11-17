import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { Auth0Provider } from '@auth0/auth0-react';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    { /* Task 2: Wrap the App component with Auth0Provider and configure it with domain, 
    clientId, and audience */}


  </StrictMode>,
)
