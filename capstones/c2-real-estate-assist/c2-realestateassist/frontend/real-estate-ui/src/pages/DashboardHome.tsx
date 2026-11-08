import React from "react";
import { useNavigate } from "react-router-dom";
import AnalyticsCard from "../components/AnalyticsCard";
import RecentChats from "../components/RecentChats";
import { properties } from "../data/mockProperties";
import { PropertyCard } from "../components/PropertyCard";

const DashboardHome: React.FC = () => {
  const navigate = useNavigate();
  const featuredProperties = properties.slice(0, 3);

  return (
    <div className="space-y-8 overflow-y-auto">
      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
        <div className="space-y-6 rounded-[32px] border border-slate-200/70 bg-white/90 p-6 shadow-sm shadow-slate-200/20 backdrop-blur-xl">
          <div className="space-y-3">
            <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Dashboard</p>
            <h1 className="text-3xl font-semibold text-slate-900">SaaS command center</h1>
            <p className="max-w-2xl text-sm leading-7 text-slate-600">
              Manage your assistant conversations and property browsing from a single modern workspace.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => navigate("/chat")}
              className="rounded-[28px] border border-slate-200 bg-slate-50 px-6 py-5 text-left text-sm font-semibold text-slate-900 transition hover:bg-white hover:shadow-sm"
            >
              <p className="uppercase tracking-[0.24em] text-slate-500">Open Chat</p>
              <span className="mt-3 block text-xl">Launch the AI conversation flow</span>
            </button>
            <button
              type="button"
              onClick={() => navigate("/propertyCards")}
              className="rounded-[28px] border border-slate-200 bg-slate-50 px-6 py-5 text-left text-sm font-semibold text-slate-900 transition hover:bg-white hover:shadow-sm"
            >
              <p className="uppercase tracking-[0.24em] text-slate-500">Browse Properties</p>
              <span className="mt-3 block text-xl">View curated property cards</span>
            </button>
          </div>
        </div>

        <div className="space-y-6 rounded-[32px] border border-slate-200/70 bg-white/90 p-6 shadow-sm shadow-slate-200/20 backdrop-blur-xl">
          <h2 className="text-xl font-semibold text-slate-900">Analytics</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <AnalyticsCard title="Active sessions" value="14" trend="+18%" caption="Compared to yesterday" />
            <AnalyticsCard title="Chat requests" value="1.2k" trend="+9%" caption="Monthly average" />
            <AnalyticsCard title="Properties reviewed" value="86" trend="+12%" caption="This week" />
            <AnalyticsCard title="Response quality" value="94%" trend="+3%" caption="Based on service metrics" />
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="space-y-6 rounded-[32px] border border-slate-200/70 bg-white/90 p-6 shadow-sm shadow-slate-200/20 backdrop-blur-xl">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Recent activity</p>
              <h2 className="text-2xl font-semibold text-slate-900">Recent sessions</h2>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
              updated moments ago
            </span>
          </div>
          <RecentChats />
        </div>

        <div className="space-y-6 rounded-[32px] border border-slate-200/70 bg-white/90 p-6 shadow-sm shadow-slate-200/20 backdrop-blur-xl">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Featured homes</p>
              <h2 className="text-2xl font-semibold text-slate-900">Recommended properties</h2>
            </div>
          </div>
          <div className="grid gap-4">
            {featuredProperties.map((property) => (
              <PropertyCard key={property.id} property={property} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardHome;


