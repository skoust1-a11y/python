import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./layouts/AppLayout";
import { AuthLayout } from "./layouts/AuthLayout";
import { AdminPage } from "./pages/AdminPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { DocumentTypePage } from "./pages/DocumentTypePage";
import { EscalationsPage } from "./pages/EscalationsPage";
import { LoginPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { PortfolioPage } from "./pages/PortfolioPage";
import { QueryPage } from "./pages/QueryPage";
import { ScreensPage } from "./pages/ScreensPage";
import { UploadPage } from "./pages/UploadPage";
import { SignupPage } from "./pages/SignupPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { PublicOnlyRoute } from "./routes/PublicOnlyRoute";
import { RoleRoute } from "./routes/RoleRoute";

export function App() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
        </Route>
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="ask" element={<QueryPage />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="portfolios" element={<PortfolioPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="documents/type/:useCase" element={<DocumentTypePage />} />
          <Route path="screens" element={<ScreensPage />} />
          <Route element={<RoleRoute allow={["risk_manager", "compliance", "admin"]} />}>
            <Route path="escalations" element={<EscalationsPage />} />
          </Route>
          <Route element={<RoleRoute allow={["admin"]} />}>
            <Route path="admin" element={<AdminPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
