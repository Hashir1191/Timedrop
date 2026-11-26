import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { getMe, SESSION_EXPIRED_EVENT } from "./api";
import { AuthContext, type AuthState } from "./auth";
import Login from "./pages/Login";
import LandingPage from "./pages/LandingPage";
import Layout from "./components/Layout";
import CustomerLayout from "./components/CustomerLayout";
import PartnerLayout from "./components/PartnerLayout";
import MerchantLayout from "./components/MerchantLayout";
import Dashboard from "./pages/Dashboard";
import Parcels from "./pages/Parcels";
import Slots from "./pages/Slots";
import Bookings from "./pages/Bookings";
import CustomerDashboard from "./pages/CustomerDashboard";
import CustomerParcels from "./pages/CustomerParcels";
import NewParcel from "./pages/NewParcel";
import ScheduleParcel from "./pages/ScheduleParcel";
import DeliveryPartners from "./pages/DeliveryPartners";
import PartnerDashboard from "./pages/PartnerDashboard";
import MerchantDashboard from "./pages/MerchantDashboard";
import MerchantShipments from "./pages/MerchantShipments";
import PhoneSettings from "./pages/PhoneSettings";
import Intake from "./pages/Intake";
import WarehousePage from "./pages/Warehouse";
import Analytics from "./pages/Analytics";
import PartnerAvailability from "./pages/PartnerAvailability";
import ServiceAreas from "./pages/ServiceAreas";
import BlackoutDates from "./pages/BlackoutDates";
import AuditLog from "./pages/AuditLog";
import NotificationQueue from "./pages/NotificationQueue";
import SystemHealth from "./pages/SystemHealth";
import SupportCenter from "./pages/SupportCenter";
import SupportInbox from "./pages/SupportInbox";
import MerchantApplications from "./pages/MerchantApplications";
import MerchantApply from "./pages/MerchantApply";

export default function App() {
  const [auth, setAuth] = useState<AuthState>({ token: localStorage.getItem("timedrop_token"), user: null, loading: true });
  useEffect(() => {
    const clearExpiredSession = () => {
      localStorage.removeItem("timedrop_token");
      setAuth({ token: null, user: null, loading: false });
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, clearExpiredSession);

    const token = auth.token;
    if (!token) {
      setAuth({ token: null, user: null, loading: false });
    } else {
      getMe(token).then(user => setAuth({ token, user, loading: false })).catch(() => {
        clearExpiredSession();
      });
    }

    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, clearExpiredSession);
  }, []);
  const logout = () => { localStorage.removeItem("timedrop_token"); setAuth({ token: null, user: null, loading: false }); };
  if (auth.loading) return <div className="screen-center"><div className="loader" /></div>;
  const role = auth.user?.role;
  const authenticatedLayout = role === "admin" ? <Layout /> : role === "delivery_partner" ? <PartnerLayout /> : role === "merchant" ? <MerchantLayout /> : <CustomerLayout />;
  return <AuthContext.Provider value={{ ...auth, setAuth, logout }}><Routes>
    <Route path="/login" element={auth.user ? <Navigate to="/" replace /> : <Login />} />
    <Route path="/merchant/apply" element={auth.user ? <Navigate to="/" replace /> : <MerchantApply />} />
    {auth.user ? <Route path="/" element={authenticatedLayout}>
      {role === "admin" ? <>
        <Route index element={<Dashboard />} /><Route path="parcels" element={<Parcels />} /><Route path="slots" element={<Slots />} /><Route path="bookings" element={<Bookings />} /><Route path="delivery-partners" element={<DeliveryPartners />} /><Route path="intake" element={<Intake />} /><Route path="warehouse" element={<WarehousePage />} /><Route path="analytics" element={<Analytics />} /><Route path="phone-settings" element={<PhoneSettings />} /><Route path="service-areas" element={<ServiceAreas />} /><Route path="blackout-dates" element={<BlackoutDates />} /><Route path="audit-log" element={<AuditLog />} /><Route path="notification-queue" element={<NotificationQueue />} /><Route path="system-health" element={<SystemHealth />} /><Route path="support" element={<SupportInbox />} /><Route path="merchant-applications" element={<MerchantApplications />} />
      </> : role === "delivery_partner" ? <>
        <Route index element={<PartnerDashboard />} /><Route path="phone-settings" element={<PhoneSettings />} /><Route path="availability" element={<PartnerAvailability />} />
      </> : role === "merchant" ? <>
        <Route index element={<MerchantDashboard />} /><Route path="shipments" element={<MerchantShipments />} /><Route path="new-shipment" element={<NewParcel />} /><Route path="phone-settings" element={<PhoneSettings />} />
      </> : <>
        <Route index element={<CustomerDashboard />} /><Route path="my-parcels" element={<CustomerParcels />} /><Route path="new-parcel" element={<NewParcel />} /><Route path="schedule/:parcelId" element={<ScheduleParcel />} /><Route path="phone-settings" element={<PhoneSettings />} /><Route path="support" element={<SupportCenter />} />
      </>}</Route> : <Route path="/" element={<LandingPage />} />
    }
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></AuthContext.Provider>;
}
