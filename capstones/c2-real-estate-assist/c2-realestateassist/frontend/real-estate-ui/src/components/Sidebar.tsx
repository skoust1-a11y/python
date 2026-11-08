import React from "react";
import { NavLink } from "react-router-dom";
import { Home, MessageSquare, Building2, LogOut } from "lucide-react";
import { useAuth0 } from "@auth0/auth0-react";

const Sidebar: React.FC = () => {
  const { logout } = useAuth0();

  const navItems = [
    { label: "Dashboard", to: "/dashboard", icon: Home },
    { label: "Chat", to: "/chat", icon: MessageSquare },
    { label: "Property Cards", to: "/propertyCards", icon: Building2 },
  ];

  return (
    <aside className="w-64 h-screen flex-shrink-0 bg-white border-r shadow-md flex flex-col">
      <div className="flex items-center gap-3 border-b border-gray-100 px-6 py-6">
        <div className="rounded-2xl bg-indigo-600 px-3 py-2 text-white">RE</div>
        <div>
          <p className="text-sm uppercase tracking-wider text-gray-500">Real Estate</p>
          <h2 className="text-xl font-semibold text-slate-900">Assistant</h2>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-4 py-6">
        <ul className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition ${
                      isActive ? "bg-gray-100 text-slate-900 shadow-sm" : "text-gray-600 hover:bg-gray-50 hover:text-slate-900"
                    }`
                  }
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t border-gray-100 px-4 py-6">
        <button
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
          onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
        >
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
