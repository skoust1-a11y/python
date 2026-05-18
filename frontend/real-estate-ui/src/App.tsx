
import { useAuth0 } from '@auth0/auth0-react';
import ChatComponent from "./components/ChatComponent";

const ROLE_NAMESPACE = import.meta.env.VITE_AUTH0_ROLE_NAMESPACE || "https://stateful-agent.com/roles";

function App() {
 
// Task 2 - Use Auth0 hook to get authentication state and user info
// Task 2 - Determine if the user has the 'admin' role
 const { isAuthenticated, isLoading, user, loginWithRedirect, logout, getAccessTokenSilently } = useAuth0();

if (isLoading) return <div>Loading...</div>;
const idTokenRoles = (user && (user[`${ROLE_NAMESPACE}/roles`] as string[])) || [];
const isAdmin = idTokenRoles.includes("admin");
console.log(isAdmin);
  return (
    <div>
      {/* HEADER */}
      <header style={{display:'flex', alignItems:'center', justifyContent:'space-between', padding:'12px 24px', background:'#f3f7fa', borderBottom:'1px solid #e0e0e0'}}>
        <div style={{display:'flex', alignItems:'center'}}>
          
          <span style={{fontWeight:700, fontSize:22, letterSpacing:1}}>Trip & Travel Agent</span>
        </div>
        <div>
          {!isAuthenticated ? (
            <button onClick={() => loginWithRedirect({
      authorizationParams: {
        prompt: "login",
      },
    })}>Log In</button>
          ) : (
            <button onClick={() => logout({ logoutParams: { returnTo: 'http://localhost:5173' } })}>
              Log Out
            </button>
          )}
        </div>
      </header>
      {/* MAIN VIEW */}
      <main style={{marginTop:40, display:'flex', flexDirection:'column', alignItems:'center'}}>
        {!isAuthenticated && (
          <h2 style={{color:'#445'}}>Hi, Welcome to Trip and Travel Agent </h2>
        )}
        {isAuthenticated && isAdmin && (
          <div className="admin-message">
            <h2>Hi, welcome to Trip and Traveller Agent 👋</h2>
            <p>You are logged in as an <strong>Admin</strong>.</p>
          </div>
        )}
        {isAuthenticated && !isAdmin && <ChatComponent getAccessTokenSilently={getAccessTokenSilently} />}
      </main>
    </div>
  );
}

export default App;
