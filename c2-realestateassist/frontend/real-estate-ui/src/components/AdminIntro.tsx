import { ShieldCheck, Users, Settings, BarChart3 } from "lucide-react";

const AdminIntro = () => {
  return (
    <div className="w-full mx-auto rounded-3xl border border-gray-200 bg-white p-6 md:p-8 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
        
        {/* Left Content */}
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-4 py-1.5 text-sm font-medium text-blue-700">
            <ShieldCheck size={16} />
            Admin Dashboard
          </div>

          <h1 className="mt-5 text-3xl md:text-4xl font-bold tracking-tight text-gray-900 leading-tight">
            Manage your platform with complete control
          </h1>

          <p className="mt-4 text-base md:text-lg text-gray-600 leading-relaxed">
            Monitor users, manage settings, analyze performance, and keep
            everything running smoothly from one centralized admin panel.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
              Fast Management
            </div>

            <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
              Secure Access
            </div>

            <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
              Real-time Insights
            </div>
          </div>
        </div>

        {/* Right Cards */}
        <div className="grid grid-cols-2 gap-4 w-full lg:max-w-md">
          <div className="rounded-2xl border border-gray-200 bg-gradient-to-br from-blue-50 to-white p-5 shadow-sm">
            <Users className="text-blue-600" size={28} />
            <h3 className="mt-4 text-lg font-semibold text-gray-900">
              Users
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              Manage user accounts and permissions.
            </p>
          </div>

          <div className="rounded-2xl border border-gray-200 bg-gradient-to-br from-purple-50 to-white p-5 shadow-sm">
            <Settings className="text-purple-600" size={28} />
            <h3 className="mt-4 text-lg font-semibold text-gray-900">
              Settings
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              Configure platform preferences easily.
            </p>
          </div>

          <div className="col-span-2 rounded-2xl border border-gray-200 bg-gradient-to-r from-gray-50 to-white p-5 shadow-sm">
            <div className="flex items-start gap-4">
              <div className="rounded-xl bg-green-100 p-3">
                <BarChart3 className="text-green-600" size={26} />
              </div>

              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  Analytics & Monitoring
                </h3>
                <p className="mt-1 text-sm text-gray-600">
                  Track activity, system health, and performance metrics with
                  detailed analytics tools.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminIntro;