import React from "react";
import { useAuth0 } from "@auth0/auth0-react";

const Navbar: React.FC = () => {
  const { user } = useAuth0();

  return (
    <header className="flex items-center justify-between gap-4 bg-white/60 backdrop-blur-sm px-4 py-3 rounded-lg shadow-sm">
      <div className="flex items-center gap-3">
        <div className="text-lg font-bold text-slate-900">Real Estate Assistant</div>
        <div className="hidden md:block text-sm text-slate-600">AI-powered property recommendations</div>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden md:block text-sm text-slate-600">{user?.email}</div>
      </div>
    </header>
  );
};

export default Navbar;
