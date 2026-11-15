import React from 'react';
import { Wifi, Battery, Signal, Stethoscope, Smartphone } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface MobileFrameProps {
  children: React.ReactNode;
}

export const MobileFrame: React.FC<MobileFrameProps> = ({ children }) => {
  const { user } = useAuth();
  const location = useLocation();
  const isDoctorRoute = location.pathname.startsWith('/doctor');

  if (isDoctorRoute) {
    return <div className="min-h-screen bg-slate-50 text-brand-text">{children}</div>;
  }

  return (
    <div className="min-h-screen bg-[#EBEFF8] flex flex-col items-center justify-center p-0 sm:py-6 selection:bg-brand-primary selection:text-white">
      {/* Top Banner on Desktop with Mode Switcher */}
      <div className="w-full max-w-[430px] hidden sm:flex items-center justify-between px-3 py-1.5 mb-2 text-xs text-slate-500 font-medium">
        <div className="flex items-center gap-1.5">
          <Smartphone className="w-3.5 h-3.5 text-brand-primary" />
          <span>AnemiaWatch Android Preview</span>
        </div>
        {user?.role === 'doctor' ? (
          <Link
            to="/doctor"
            className="flex items-center gap-1 text-brand-primary hover:underline font-semibold bg-white px-2 py-0.5 rounded-full shadow-sm"
          >
            <Stethoscope className="w-3.5 h-3.5" />
            <span>Doctor Dashboard</span>
          </Link>
        ) : (
          <span className="text-slate-400">HF26-35 Mobile View</span>
        )}
      </div>

      {/* Mobile Device Frame */}
      <div className="w-full sm:max-w-[412px] h-screen sm:h-[844px] bg-[#7185D1] sm:rounded-[42px] sm:shadow-2xl sm:border-[8px] sm:border-slate-800 flex flex-col overflow-hidden relative">
        {/* Android Status Bar — always brand-primary colored */}
        <div className="h-7 w-full bg-[#7185D1] text-white flex items-center justify-between px-5 text-[11px] font-semibold tracking-wider select-none shrink-0 z-30">
          <span>09:41</span>
          <div className="flex items-center space-x-1.5 opacity-90">
            <Signal className="w-3 h-3" />
            <Wifi className="w-3 h-3" />
            <Battery className="w-3.5 h-3.5" />
          </div>
        </div>

        {/* Dynamic App Content Screen */}
        <div className="flex-1 w-full overflow-hidden flex flex-col relative bg-[#7185D1]">
          {children}
        </div>

        {/* Android Navigation Bar Pill */}
        <div className="h-3.5 w-full bg-white flex items-center justify-center shrink-0 z-30">
          <div className="w-28 h-1 bg-slate-300 rounded-full" />
        </div>
      </div>
    </div>
  );
};
