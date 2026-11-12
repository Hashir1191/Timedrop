import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { getMe } from "./api";
import { AuthContext, type AuthState } from "./auth";
import Login from "./pages/Login";
import Layout from "./components/Layout";
import CustomerLayout from "./components/CustomerLayout";
import PartnerLayout from "./components/PartnerLayout";
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
import PhoneSettings from "./pages/PhoneSettings";
export default function App(){
 const [auth,setAuth]=useState<AuthState>({token:localStorage.getItem("timedrop_token"),user:null,loading:true});
 useEffect(()=>{const token=auth.token;if(!token){setAuth({token:null,user:null,loading:false});return;}getMe(token).then(user=>setAuth({token,user,loading:false})).catch(()=>{localStorage.removeItem("timedrop_token");setAuth({token:null,user:null,loading:false});});},[]);
 const logout=()=>{localStorage.removeItem("timedrop_token");setAuth({token:null,user:null,loading:false});};
 if(auth.loading)return <div className="screen-center"><div className="loader"/></div>;
 const role=auth.user?.role;
 return <AuthContext.Provider value={{...auth,setAuth,logout}}><Routes>
  <Route path="/login" element={auth.user?<Navigate to="/" replace/>:<Login/>}/>
  <Route path="/" element={auth.user?(role==="admin"?<Layout/>:role==="delivery_partner"?<PartnerLayout/>:<CustomerLayout/>):<Navigate to="/login" replace/>}>
   {role==="admin"?<>
    <Route index element={<Dashboard/>}/><Route path="parcels" element={<Parcels/>}/><Route path="slots" element={<Slots/>}/><Route path="bookings" element={<Bookings/>}/><Route path="delivery-partners" element={<DeliveryPartners/>}/><Route path="phone-settings" element={<PhoneSettings/>}/>
   </>:role==="delivery_partner"?<><Route index element={<PartnerDashboard/>}/><Route path="phone-settings" element={<PhoneSettings/>}/></>:<>
    <Route index element={<CustomerDashboard/>}/><Route path="my-parcels" element={<CustomerParcels/>}/><Route path="new-parcel" element={<NewParcel/>}/><Route path="schedule/:parcelId" element={<ScheduleParcel/>}/><Route path="phone-settings" element={<PhoneSettings/>}/>
   </>}
  </Route><Route path="*" element={<Navigate to={auth.user?"/":"/login"} replace/>}/>
 </Routes></AuthContext.Provider>;
}
