import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth";
import { AuthProvider } from "./context/AuthContext";
import { NotificationsProvider } from "./context/NotificationsContext";
import ChatPage from "./pages/ChatPage";
import CustomerDashboardPage from "./pages/CustomerDashboardPage";
import CustomerDetailPage from "./pages/CustomerDetailPage";
import DietPlanPage from "./pages/DietPlanPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import MyCoachPage from "./pages/MyCoachPage";
import MonitoringPage from "./pages/MonitoringPage";
import ProgressPage from "./pages/ProgressPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";
import RequestsPage from "./pages/RequestsPage";
import WorkoutPlanPage from "./pages/WorkoutPlanPage";

export default function App() {
  return (
    <AuthProvider>
      <NotificationsProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<LandingPage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />

            <Route element={<RequireAuth />}>
              <Route path="profile" element={<ProfilePage />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="customers" element={<CustomerDashboardPage />} />
              <Route path="customers/:customerId" element={<CustomerDetailPage />} />
              <Route path="workout-plan" element={<WorkoutPlanPage />} />
              <Route path="diet-plan" element={<DietPlanPage />} />
              <Route path="my-coach" element={<MyCoachPage />} />
              <Route path="monitoring" element={<MonitoringPage />} />
              <Route path="progress" element={<ProgressPage />} />
              <Route path="requests" element={<RequestsPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </NotificationsProvider>
    </AuthProvider>
  );
}
