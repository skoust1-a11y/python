import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { Auth0Provider } from '@auth0/auth0-react';


const domain = import.meta.env.VITE_AUTH0_DOMAIN as string | undefined
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID as string | undefined
const audience = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined

if (!domain || !clientId || !audience) {
  throw new Error('Missing required Auth0 environment variables. Please check your .env file.')
}


createRoot(document.getElementById('root')!).render(
  <StrictMode>
    { /* Task 2: Wrap the App component with Auth0Provider and configure it with domain, 
    clientId, and audience */}
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: 'http://localhost:5173',
        audience: audience,
      }}
    >
      <App/>
      </Auth0Provider>

  </StrictMode>,
)
