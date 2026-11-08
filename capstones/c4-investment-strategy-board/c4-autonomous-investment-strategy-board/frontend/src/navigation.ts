import type { LucideIcon } from "lucide-react";
import {
  BriefcaseBusiness,
  LayoutDashboard,
  LineChart,
  Star,
  Upload,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  description: string;
  icon: LucideIcon;
  end?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  {
    to: "/",
    label: "Dashboard",
    description: "Market snapshot and a high-level view of an imported portfolio.",
    icon: LayoutDashboard,
    end: true,
  },
  {
    to: "/portfolio",
    label: "Portfolio Analyzer",
    description: "Ask questions about an imported portfolio and review structured results.",
    icon: BriefcaseBusiness,
  },
  {
    to: "/stocks",
    label: "Stock Analyzer",
    description: "Search, select, and analyze a single instrument independently of any portfolio.",
    icon: LineChart,
  },
  {
    to: "/watchlist",
    label: "Watchlist",
    description: "Monitor selected symbols and open them in Stock Analyzer.",
    icon: Star,
  },
  {
    to: "/upload",
    label: "Upload Portfolio",
    description: "Upload a CSV or XLSX file, preview validation, then confirm import.",
    icon: Upload,
  },
];

export function navLabelForPath(pathname: string): string {
  const match = NAV_ITEMS.find((item) =>
    item.end ? pathname === item.to : pathname === item.to || pathname.startsWith(`${item.to}/`),
  );
  return match?.label ?? "Investment Strategy Board";
}
