import React from 'react';
import type { PropertyData } from '../apiService';
import { MapPin, Home, IndianRupee, Train } from 'lucide-react';

interface PropertyCardProps {
  property: PropertyData;
}

export const PropertyCard: React.FC<PropertyCardProps> = ({ property }) => {
  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-100 hover:shadow-lg transition-shadow duration-300">
      {property.imageUrl ? (
        <img
          src={property.imageUrl}
          alt={property.title}
          className="w-full h-48 object-cover"
        />
      ) : (
        <div className="w-full h-48 bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center">
          <Home className="w-12 h-12 text-indigo-300" />
        </div>
      )}

      <div className="p-5">
        <h3 className="text-xl font-bold text-gray-900 mb-2 truncate">{property.title}</h3>

        <div className="flex items-center text-indigo-600 font-semibold mb-4">
          {/* <IndianRupee className="w-4 h-4 mr-1" /> */}
          <span className="text-lg">{property.price}</span>
        </div>

        <div className="space-y-2 mb-4">
          <div className="flex items-center text-gray-600">
            <Home className="w-4 h-4 mr-2" />
            <span className="text-sm">{property.bhk}</span>
          </div>

          <div className="flex items-center text-gray-600">
            <MapPin className="w-4 h-4 mr-2" />
            <span className="text-sm truncate">{property.locality}</span>
          </div>

          {property.commuteInsights && (
            <div className="flex items-start text-gray-600">
              <Train className="w-4 h-4 mr-2 mt-1 flex-shrink-0" />
              <span className="text-sm">{property.commuteInsights}</span>
            </div>
          )}
        </div>

        {property.amenities && property.amenities.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="flex flex-wrap gap-2">
              {property.amenities.slice(0, 3).map((amenity, index) => (
                <span
                  key={index}
                  className="px-2 py-1 bg-indigo-50 text-indigo-700 text-xs rounded-full font-medium"
                >
                  {amenity}
                </span>
              ))}
              {property.amenities.length > 3 && (
                <span className="px-2 py-1 bg-gray-50 text-gray-600 text-xs rounded-full font-medium">
                  +{property.amenities.length - 3} more
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
