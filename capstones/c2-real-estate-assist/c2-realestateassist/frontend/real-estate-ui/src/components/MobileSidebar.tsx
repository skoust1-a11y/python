import { NavLink } from "react-router-dom";
import { Home, MessageSquare, Building2, LogOut, X } from "lucide-react";
import { useAuth0 } from "@auth0/auth0-react";

interface MobileSidebarProps {
  open: boolean;
  onClose: () => void;
}

const navItems = [
  { label: "Dashboard", to: "/dashboard", icon: Home },
  { label: "Chat", to: "/chat", icon: MessageSquare },
  { label: "Property Cards", to: "/propertyCards", icon: Building2 },
];

const MobileSidebar: React.FC<MobileSidebarProps> = ({ open, onClose }) => {
  const { logout } = useAuth0();

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      <button type="button" onClick={onClose} className="absolute inset-0 bg-slate-950/40" aria-label="Close menu" />
      <aside className="relative z-50 flex w-80 flex-col gap-6 overflow-y-auto border-r border-slate-200 bg-white px-6 py-6 shadow-2xl">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Real Estate</p>
            <h2 className="text-xl font-semibold text-slate-900">Assistant</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 text-slate-700 transition hover:border-slate-300"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-3xl px-4 py-3 text-sm font-semibold transition ${
                    isActive ? "bg-slate-100 text-slate-900" : "text-slate-600 hover:bg-slate-50"
                  }`
                }
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <button
          type="button"
          onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
          className="mt-auto flex w-full items-center justify-center gap-2 rounded-3xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </aside>
    </div>
  );
};

export default MobileSidebar;
