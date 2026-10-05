import { NavLink, Outlet } from "react-router-dom";

export function AuthLayout() {
  return (
    <div className="auth-shell">
      <div className="auth-card">
        <p className="kicker">Capstone · synthetic data</p>
        <h1>Finance Risk &amp; Investment Intelligence</h1>
        <nav className="tabs">
          <NavLink to="/login">Log in</NavLink>
          <NavLink to="/signup">Sign up</NavLink>
        </nav>
        <Outlet />
        <p className="disclaimer">
          Educational use only. Not investment advice. Outputs require a qualified human analyst.
        </p>
      </div>
    </div>
  );
}
