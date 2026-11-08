import { Link } from "react-router-dom";
import { PageHeader } from "@/components";

export function NotFoundPage() {
  return (
    <>
      <PageHeader title="Page not found" description="That route is not part of this application." />
      <p className="text-sm text-slate-600">
        Return to the{" "}
        <Link className="font-medium text-brand-700 hover:underline" to="/">
          Dashboard
        </Link>
        .
      </p>
    </>
  );
}
