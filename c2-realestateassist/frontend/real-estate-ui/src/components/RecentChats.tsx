interface RecentSessionItem {
  id: string;
  title: string;
  summary: string;
  time: string;
}

const mockRecentSessions: RecentSessionItem[] = [
  { id: "1", title: "Morning commute review", summary: "2 BHK near metro and schools", time: "3h ago" },
  { id: "2", title: "Budget friendly search", summary: "Homes under ₹90k in Gurgaon", time: "Yesterday" },
  { id: "3", title: "Luxury insights", summary: "Riverfront and premium amenities", time: "2 days ago" },
];

const RecentChats: React.FC = () => (
  <div className="space-y-4">
    {mockRecentSessions.map((session) => (
      <div key={session.id} className="rounded-[24px] border border-slate-200/80 bg-slate-50 p-4 shadow-sm transition hover:border-slate-300 hover:bg-white">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h4 className="text-base font-semibold text-slate-900">{session.title}</h4>
            <p className="mt-1 text-sm leading-6 text-slate-600">{session.summary}</p>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{session.time}</span>
        </div>
      </div>
    ))}
  </div>
);

export default RecentChats;
