import { useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useLocation } from "react-router-dom";
import AdminComponent from "./AdminComponent";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ROLE_NAMESPACE = import.meta.env.VITE_AUTH0_ROLE_NAMESPACE || "https://stateful-agent.com/roles";

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {

  const { isAuthenticated, isLoading, loginWithRedirect,user } = useAuth0();
  const location = useLocation();
  const idTokenRoles = (user && (user[`${ROLE_NAMESPACE}/roles`] as string[])) || [];
  const isAdmin = idTokenRoles.includes("admin");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      loginWithRedirect({
        appState: {
          returnTo: location.pathname,
        },
      });
    }
  }, [isLoading, isAuthenticated, loginWithRedirect, location.pathname]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-700">
        <span className="rounded-3xl bg-white px-6 py-4 shadow-sm">Checking authentication...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{isAdmin?<AdminComponent/>:children}</>;
};

export default ProtectedRoute;
