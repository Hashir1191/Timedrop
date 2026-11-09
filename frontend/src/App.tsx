import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { getMe } from "./api";
import { AuthContext, type AuthState } from "./auth";
import Login from "./pages/Login";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Parcels from "./pages/Parcels";
import Slots from "./pages/Slots";
import Bookings from "./pages/Bookings";

export default function App() {
  const [auth, setAuth] = useState<AuthState>({ token: localStorage.getItem("timedrop_token"), user: null, loading: true });
  useEffect(() => {
    if (!auth.token) { setAuth({ token: null, user: null, loading: false }); return; }
    getMe(auth.token).then((user) => {
      if (user.role !== "admin") throw new Error("This dashboard is for operations administrators.");
      setAuth({ token: auth.token, user, loading: false });
    }).catch(() => {
      localStorage.removeItem("timedrop_token");
      setAuth({ token: null, user: null, loading: false });
    });
  }, []);
  const logout = () => {
    localStorage.removeItem("timedrop_token");
    setAuth({ token: null, user: null, loading: false });
  };
  if (auth.loading) return <div className="screen-center"><div className="loader" /></div>;
  return (
    <AuthContext.Provider value={{ ...auth, setAuth, logout }}>
      <Routes>
        <Route path="/login" element={auth.user ? <Navigate to="/" replace /> : <Login />} />
        <Route path="/" element={auth.user ? <Layout /> : <Navigate to="/login" replace />}>
          <Route index element={<Dashboard />} />
          <Route path="parcels" element={<Parcels />} />
          <Route path="slots" element={<Slots />} />
          <Route path="bookings" element={<Bookings />} />
        </Route>
        <Route path="*" element={<Navigate to={auth.user ? "/" : "/login"} replace />} />
      </Routes>
    </AuthContext.Provider>
  );
}