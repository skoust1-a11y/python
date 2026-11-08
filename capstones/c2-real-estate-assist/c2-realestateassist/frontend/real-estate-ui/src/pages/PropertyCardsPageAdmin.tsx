import React from "react";
import { useNavigate } from "react-router-dom";
import { properties } from "../data/mockProperties";
import { PropertyCard } from "../components/PropertyCard";

const PropertyCardsPageAdmin: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-[32px] border border-slate-200/70 bg-white/90 p-6 shadow-sm shadow-slate-200/20 backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Property Gallery</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">Browse modern listings</h1>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-600">
            Explore property cards built from the existing mock property data with a clean, responsive experience.
          </p>
        </div>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
        {properties.map((property) => (
          <PropertyCard key={property.id} property={property} />
        ))}
      </div>
    </div>
  );
};

export default PropertyCardsPageAdmin;
