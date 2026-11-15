import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, ArrowRight, HeartPulse } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export const OnboardingScreen: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  return (
    <div className="flex-1 bg-brand-primary flex flex-col justify-between p-6 text-white relative overflow-hidden">
      {/* Background Graphic Curves */}
      <div className="absolute top-0 left-0 right-0 h-64 bg-gradient-to-b from-brand-darkPeriwinkle/40 to-transparent -z-10" />

      {/* Top illustration container */}
      <div className="flex-1 flex flex-col items-center justify-center pt-2">
        <div className="w-56 h-56 rounded-full bg-white/10 backdrop-blur-sm p-3 mb-4 flex items-center justify-center shadow-lg relative border border-white/20">
          <img
            src="/assets/onboarding_hero.png"
            alt="Anemia Awareness Illustration"
            className="w-full h-full object-contain rounded-full"
            onError={(e) => {
              // Fallback if image fails to render
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
          {/* Badge */}
          <div className="absolute bottom-2 right-4 bg-brand-accent text-white p-2.5 rounded-full shadow-md">
            <HeartPulse className="w-5 h-5" />
          </div>
        </div>

        {/* Headline matching reference screenshot */}
        <h2 className="text-2xl sm:text-3xl font-extrabold text-center mb-2 tracking-tight">
          Frequent Headaches?
        </h2>
        <p className="text-white/85 text-xs sm:text-sm text-center max-w-xs leading-relaxed font-medium">
          Headaches and fatigue could be early signs of anemia. Screen your estimated hemoglobin level
          non-invasively using your smartphone camera and AI.
        </p>

        {/* Disclaimer Note */}
        <div className="mt-4 bg-white/10 backdrop-blur-md rounded-xl p-2.5 max-w-xs flex items-center gap-2 border border-white/15 text-[11px] text-white/90">
          <ShieldAlert className="w-4 h-4 text-brand-accent shrink-0" />
          <span>AI screening provides early indicators; it is not a replacement for laboratory CBC tests.</span>
        </div>
      </div>

      {/* Action buttons matching reference InShot_20240621_080337187_frame_0.png */}
      <div className="w-full pb-2">
        <div className="grid grid-cols-2 gap-3 mb-3">
          <button
            onClick={() => navigate('/login')}
            className="w-full py-3.5 bg-white text-brand-primary font-bold rounded-2xl shadow-lg hover:bg-slate-50 active:scale-95 transition-all text-sm flex items-center justify-center gap-1.5"
          >
            Sign In
          </button>
          <button
            onClick={() => navigate('/register')}
            className="w-full py-3.5 bg-white text-brand-primary font-bold rounded-2xl shadow-lg hover:bg-slate-50 active:scale-95 transition-all text-sm flex items-center justify-center gap-1.5"
          >
            Register
          </button>
        </div>

        <button
          onClick={async () => {
            try {
              const res = await api.guestLogin();
              login(res.access_token, res.user);
            } catch {
              localStorage.setItem('anemiawatch_guest', 'true');
            }
            navigate('/home');
          }}
          className="w-full py-2.5 text-center text-xs text-white/80 hover:text-white font-medium flex items-center justify-center gap-1"
        >
          <span>Explore as Guest</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>

        {/* Bottom Logo */}
        <div className="flex items-center justify-center gap-1.5 mt-2 opacity-80">
          <div className="w-4 h-4 rounded-full bg-brand-accent flex items-center justify-center text-[10px] font-black text-white">
            a
          </div>
          <span className="text-xs font-semibold tracking-wider lowercase">anem.ai</span>
        </div>
      </div>
    </div>
  );
};
