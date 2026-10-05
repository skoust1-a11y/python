import { FormEvent, type ReactNode, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useProfile } from "../auth/ProfileContext";

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {children}
    </svg>
  );
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const { profiles, profileId, setProfileId, create, remove } = useProfile();
  const nav = useNavigate();
  const loc = useLocation();
  const [name, setName] = useState("");
  const canEsc = user && ["risk_manager", "compliance", "admin"].includes(user.role);
  const canAdmin = user?.role === "admin";
  const selected = profiles.find((p) => p.profile_id === profileId);
  const showBack = loc.pathname.startsWith("/app/documents/type/");

  function onLogout() {
    logout();
    nav("/login");
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    await create(name.trim());
    setName("");
  }

  return (
    <div className="app-shell">
      <aside className="nav-side">
        <NavLink to="/app" end className="brand-block">
          <span className="brand-mark">FR</span>
          <span>
            <strong>Finance Risk</strong>
            <span>Intelligence</span>
          </span>
        </NavLink>
        <div className="profile-box">
          <label>
            Profile
            <select value={profileId} onChange={(e) => setProfileId(e.target.value)}>
              {profiles.map((p) => (
                <option key={p.profile_id} value={p.profile_id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <form onSubmit={onCreate} className="profile-new">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New profile" maxLength={80} />
            <button type="submit">Add</button>
          </form>
          {selected?.kind === "user" && (
            <button type="button" className="ghost" onClick={() => remove(profileId)}>
              Delete profile
            </button>
          )}
          <p className="muted">Portfolios and screens are shared.</p>
        </div>
        <nav>
          <NavLink to="/app" end>
            <Icon>
              <path d="M4 11.5 12 4l8 7.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z" />
            </Icon>
            Overview
          </NavLink>
          <NavLink to="/app/documents">
            <Icon>
              <path d="M7 3.5h7l4 4V20a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1z" />
              <path d="M14 3.5V8h4" />
            </Icon>
            Documents
          </NavLink>
          <NavLink to="/app/upload">
            <Icon>
              <path d="M12 16V7" />
              <path d="m8 10 4-4 4 4" />
              <path d="M5 19h14" />
            </Icon>
            Upload
          </NavLink>
          <NavLink to="/app/ask">
            <Icon>
              <path d="M5 6h14v9H8l-3 3z" />
            </Icon>
            Ask Knowledge
          </NavLink>
          <NavLink to="/app/portfolios">
            <Icon>
              <rect x="4" y="6" width="16" height="13" rx="1.5" />
              <path d="M8 6V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v1" />
            </Icon>
            Portfolios
          </NavLink>
          <NavLink to="/app/screens">
            <Icon>
              <circle cx="11" cy="11" r="6.5" />
              <path d="m16 16 4 4" />
            </Icon>
            Screens
          </NavLink>
          {canEsc && (
            <NavLink to="/app/escalations">
              <Icon>
                <path d="M12 4 3.5 19h17L12 4z" />
                <path d="M12 10v4" />
                <path d="M12 16.5h.01" />
              </Icon>
              Escalations
            </NavLink>
          )}
          {canAdmin && (
            <NavLink to="/app/admin">
              <Icon>
                <circle cx="12" cy="8" r="3" />
                <path d="M5 19c1.2-3 3.8-4.5 7-4.5S17.8 16 19 19" />
              </Icon>
              Admin
            </NavLink>
          )}
        </nav>
        <div className="user-dock">
          <span className="email">{user?.email}</span>
          <span className="badge">{user?.role}</span>
          <button type="button" className="ghost" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </aside>
      <div className="main">
        {showBack && (
          <header>
            <button type="button" className="ghost" onClick={() => nav("/app/documents")}>
              Back
            </button>
          </header>
        )}
        <Outlet />
      </div>
    </div>
  );
}
