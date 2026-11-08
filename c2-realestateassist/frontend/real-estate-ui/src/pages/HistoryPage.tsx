import React from "react";
import SessionHistory from "../components/SessionHistory";

const HistoryPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">All sessions</h3>
        <p className="text-sm text-gray-500 mt-1">Full session history and exports.</p>
      </div>

      <SessionHistory />
    </div>
  );
};

export default HistoryPage;
