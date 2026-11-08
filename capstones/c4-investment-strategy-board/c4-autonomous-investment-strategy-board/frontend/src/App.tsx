import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/layout/AppLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { PortfolioAnalyzerPage } from "@/pages/PortfolioAnalyzerPage";
import { StockAnalyzerPage } from "@/pages/StockAnalyzerPage";
import { UploadPortfolioPage } from "@/pages/UploadPortfolioPage";
import { WatchlistPage } from "@/pages/WatchlistPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="portfolio" element={<PortfolioAnalyzerPage />} />
          <Route path="stocks" element={<StockAnalyzerPage />} />
          <Route path="stocks/:symbol" element={<StockAnalyzerPage />} />
          <Route path="watchlist" element={<WatchlistPage />} />
          <Route path="upload" element={<UploadPortfolioPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
