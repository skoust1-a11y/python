import React from "react";
import { properties } from "../data/mockProperties";
import { PropertyCard } from "../components/PropertyCard";

const SavedProperties: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Saved properties</h3>
        <p className="text-sm text-gray-500 mt-1">Properties you have bookmarked for follow-up.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {properties.slice(0, 12).map((p) => (
          <PropertyCard key={p.id} property={p} />
        ))}
      </div>
    </div>
  );
};

export default SavedProperties;
