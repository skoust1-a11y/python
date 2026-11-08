import React from "react";

interface DashboardCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
}

const DashboardCard: React.FC<DashboardCardProps> = ({ title, value, subtitle }) => {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-md">
      <p className="text-sm text-gray-500">{title}</p>
      <div className="mt-2 flex items-baseline justify-between">
        <h3 className="text-2xl font-semibold text-slate-900">{value}</h3>
        {subtitle && <span className="text-xs text-gray-400">{subtitle}</span>}
      </div>
    </div>
  );
};

export default DashboardCard;
