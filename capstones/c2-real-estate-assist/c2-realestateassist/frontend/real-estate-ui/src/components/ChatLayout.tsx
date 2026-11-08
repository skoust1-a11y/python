import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { ChatComponent } from "./ChatComponent";

const ChatLayout: React.FC = () => {
  const navigate = useNavigate();

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 rounded-[32px] border border-slate-200/70 bg-white/90 p-6 shadow-sm shadow-slate-200/20 backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Chat assistant</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">Ask the assistant anything about homes</h1>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-600">
            The existing chat UI and streaming experience remain unchanged inside the SaaS layout.
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate("/dashboard")}
          className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </button>
      </div>

      <ChatComponent />
    </section>
  );
};

export default ChatLayout;
