import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { Auth0Provider } from '@auth0/auth0-react'

const domain = import.meta.env.VITE_AUTH0_DOMAIN || "";
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID || "";
const audience = import.meta.env.VITE_AUTH0_AUDIENCE || "";
const redirectUri = window.location.origin;

console.log("================ Auth0 Config Debug ================");
console.log("Domain:", domain);
console.log("Client ID:", clientId);
console.log("Audience:", audience);
console.log("Redirect URI:", redirectUri);
console.log("====================================================");

if (!domain || !clientId) {
  console.error("FATAL ERROR: Auth0 Domain or Client ID is missing. Check your .env file and restart Vite.");
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: audience
      }}
    >
      <App />
    </Auth0Provider>
  </React.StrictMode>,
)
