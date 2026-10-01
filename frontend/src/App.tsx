import { lazy } from "react";
import { Route, Routes } from "react-router";
import { RequireAuth } from "@/auth/RequireAuth";
import { RequireRole } from "@/auth/RequireRole";
import { Layout } from "@/components/Layout";
import { NotFound } from "@/components/ui";
import { AccountPage } from "@/features/auth/AccountPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { BookingPage } from "@/features/bookings/BookingPage";
import { MyBookingsPage } from "@/features/bookings/MyBookingsPage";
import { HomePage } from "@/features/movies/HomePage";
import { MovieDetailPage } from "@/features/movies/MovieDetailPage";
import { ShowtimePage } from "@/features/showtimes/ShowtimePage";

const CheckInPage = lazy(() =>
  import("@/features/staff/CheckInPage").then((m) => ({ default: m.CheckInPage })),
);
const DashboardPage = lazy(() =>
  import("@/features/admin/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="movies/:id" element={<MovieDetailPage />} />
        <Route path="showtimes/:id" element={<ShowtimePage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route element={<RequireAuth />}>
          <Route path="account" element={<AccountPage />} />
          <Route path="bookings" element={<MyBookingsPage />} />
          <Route path="bookings/:code" element={<BookingPage />} />
        </Route>
        <Route element={<RequireRole roles={["staff", "admin"]} />}>
          <Route path="staff/checkin" element={<CheckInPage />} />
        </Route>
        <Route element={<RequireRole roles={["admin"]} />}>
          <Route path="dashboard" element={<DashboardPage />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}