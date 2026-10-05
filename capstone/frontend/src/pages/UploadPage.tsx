import { useNavigate } from "react-router-dom";
import { PortfolioUploadForm } from "../components/PortfolioUploadForm";

export function UploadPage() {
  const nav = useNavigate();
  return (
    <section className="page">
      <h2>Upload portfolio</h2>
      <p className="muted">
        Add a book from a holdings CSV. After upload you can review it on Portfolios and ask questions on Ask Knowledge.
      </p>
      <PortfolioUploadForm onUploaded={(id) => nav(`/app/portfolios?id=${id}`)} />
    </section>
  );
}
