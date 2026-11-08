import { useAuth0 } from "@auth0/auth0-react";
import { Crown, Heading2Icon, LogOutIcon, Menu, ShieldCheck, UserCircle2Icon } from "lucide-react";

interface TopNavbarProps {
  pageTitle: string;
  userName: string;
  onOpenMenu: () => void;
}

const TopBarAdmin = () => {
    const { logout } = useAuth0();


    return(
        <>
          <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/85 backdrop-blur-xl px-4 py-4 shadow-sm sm:px-6">
    <div className="flex items-center justify-between gap-3">
      <button
        type="button"
        className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
        aria-label="Open navigation"
      >
        <ShieldCheck className="h-5 w-5" />
      </button>
      <div>
        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Workspace</p>
        <h1 className="text-lg font-semibold text-slate-900">Admin page</h1>
      </div>
      <div className="min-w-[2.75rem]" />
    </div>
    <div className="mt-4 flex items-center justify-between gap-3 rounded-3xl bg-slate-50 p-4 text-lg text-slate-700 shadow-sm">
      <span>Welcome, <strong className="text-slate-900">Admin</strong></span>
        <button
        type="button"
        onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
        className="hover:cursor-pointer inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
        aria-label="Open navigation"
      >
        <LogOutIcon className="h-5 w-5" />
      </button>
    </div>
  </header>
        </>
    )



};

export default TopBarAdmin;
