interface AnalyticsCardProps {
  title: string;
  value: string | number;
  trend: string;
  caption: string;
}

const AnalyticsCard: React.FC<AnalyticsCardProps> = ({ title, value, trend, caption }) => (
  <div className="rounded-[28px] border border-slate-200/80 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
    <p className="text-sm uppercase tracking-[0.28em] text-slate-500">{title}</p>
    <div className="mt-4 flex items-baseline gap-3">
      <span className="text-3xl font-semibold text-slate-900">{value}</span>
      <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">
        {trend}
      </span>
    </div>
    <p className="mt-3 text-sm text-slate-500">{caption}</p>
  </div>
);

export default AnalyticsCard;
