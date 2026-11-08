import React from "react";

const mockSessions = [
  { id: "s1", title: "March - Property hunt", date: "2026-05-10" },
  { id: "s2", title: "April - Budget 80k", date: "2026-05-12" },
  { id: "s3", title: "May - Family relocation", date: "2026-05-15" },
];

const SessionHistory: React.FC = () => {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900">Recent sessions</h3>
      <ul className="mt-3 space-y-2 text-sm text-gray-600">
        {mockSessions.map((s) => (
          <li key={s.id} className="flex items-center justify-between rounded-md px-3 py-2 hover:bg-gray-50">
            <div>
              <div className="font-medium text-slate-900">{s.title}</div>
              <div className="text-xs text-gray-400">{s.date}</div>
            </div>
            <div className="text-xs text-gray-500">View</div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default SessionHistory;
