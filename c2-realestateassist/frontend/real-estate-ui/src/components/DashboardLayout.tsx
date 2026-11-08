import React, { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import Sidebar from "./Sidebar";
import TopNavbar from "./TopNavbar";
import MobileSidebar from "./MobileSidebar";

const DashboardLayout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const location = useLocation();
  const { user } = useAuth0();

  const pageTitle = location.pathname.includes("/chat")
    ? "Chat"
    : location.pathname.includes("/propertyCards")
    ? "Property Cards"
    : location.pathname === "/dashboard"
    ? "Dashboard"
    : "Dashboard";

  return (
    <div className="min-h-full sticky bg-slate-100 text-slate-900">
      <MobileSidebar open={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
      <div className="lg:flex lg:h-screen overflow-hidden">
        <div className="hidden lg:block h-screen sticky top-0">
          <Sidebar />
        </div>
        <div className="flex-1 h-screen overflow-hidden flex flex-col">
          <TopNavbar pageTitle={pageTitle} userName={user?.name || "Agent"} onOpenMenu={() => setIsSidebarOpen(true)} />
          <main className="flex-1 overflow-y-auto px-4 py-5 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-7xl">
              <div className="mb-6 rounded-[32px] border border-slate-200/70 bg-white/90 p-5 shadow-sm shadow-slate-200/20 backdrop-blur-xl">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Real Estate Assistant</p>
                    <h1 className="text-2xl font-semibold text-slate-900">Dashboard overview</h1>
                  </div>
                  <div className="rounded-3xl bg-slate-50 px-4 py-3 text-sm text-slate-700">Explore chat and property workflows</div>
                </div>
              </div>
              <div className="">
              <Outlet />
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
};

export default DashboardLayout;
