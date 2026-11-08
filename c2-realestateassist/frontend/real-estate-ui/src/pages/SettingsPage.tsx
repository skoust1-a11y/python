import React from "react";

const SettingsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Settings</h3>
        <p className="text-sm text-gray-500 mt-1">Manage account, preferences, and integrations.</p>
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <h4 className="text-md font-semibold text-slate-900">Preferences</h4>
        <div className="mt-3 space-y-2 text-sm text-gray-600">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Streaming mode</div>
              <div className="text-xs text-gray-400">Toggle SSE streaming behavior</div>
            </div>
            <div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" />
                <div className="w-11 h-6 bg-gray-200 rounded-full peer-checked:bg-indigo-600 peer-focus:ring-2 peer-focus:ring-indigo-300 transition" />
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
