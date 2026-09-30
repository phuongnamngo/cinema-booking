import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import { queryClient } from "@/api/queryClient";
import { useAuth } from "@/auth/store";
import App from "./App";
import "./index.css";

// Khôi phục phiên TRƯỚC khi render và NGOÀI React, để StrictMode không chạy nó hai lần
void useAuth.getState().bootstrap();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);