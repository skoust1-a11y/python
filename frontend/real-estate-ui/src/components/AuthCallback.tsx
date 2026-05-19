import { useEffect } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useLocation, useNavigate } from "react-router-dom";

const AuthCallback: React.FC = () => {
  const { isLoading, isAuthenticated, loginWithRedirect } = useAuth0();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (isLoading) return;

    const hasAuthParams =
      location.search.includes("code=") ||
      location.search.includes("state=") ||
      location.search.includes("error=");

    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
      return;
    }

    if (!hasAuthParams) {
      loginWithRedirect({
        appState: {
          returnTo: "/dashboard",
        },
      });
    }
  }, [isLoading, isAuthenticated, loginWithRedirect, location.search, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-700">
      <div className="rounded-3xl bg-white px-6 py-4 shadow-sm">
        Signing you in...
      </div>
    </div>
  );
};

export default AuthCallback;
