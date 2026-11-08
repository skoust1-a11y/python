import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "@/context/ThemeContext";
import { Layout } from "@/components/Layout";
import { DashboardPage } from "@/pages/DashboardPage";
import { UploadPage } from "@/pages/UploadPage";
import { ChatPage } from "@/pages/ChatPage";
import { DocumentViewerPage } from "@/pages/DocumentViewerPage";
import { SearchPage } from "@/pages/SearchPage";
import { FeedbackPage } from "@/pages/FeedbackPage";

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="upload" element={<UploadPage />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="documents" element={<DocumentViewerPage />} />
            <Route path="documents/:id" element={<DocumentViewerPage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="feedback" element={<FeedbackPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
