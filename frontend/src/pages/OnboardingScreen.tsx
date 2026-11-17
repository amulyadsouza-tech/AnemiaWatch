import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, HeartPulse, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export const OnboardingScreen: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  return (
    <div className="flex-1 flex flex-col bg-[#7185D1] relative overflow-hidden select-none">

      {/* ── Soft decorative background blobs ── */}
      <div className="absolute -top-20 -left-20 w-72 h-72 rounded-full bg-white/10 blur-3xl pointer-events-none" />
      <div className="absolute top-40 -right-16 w-56 h-56 rounded-full bg-white/8 blur-2xl pointer-events-none" />

      {/* ── Hero section (takes all available space above buttons) ── */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 pt-10 pb-4">

        {/* Phone mockup card with the uploaded reference image */}
        <div className="relative mb-8">
          {/* Outer glow ring */}
          <div className="absolute inset-0 rounded-[2.5rem] bg-white/20 blur-xl scale-110 pointer-events-none" />

          {/* Phone-frame card */}
          <div
            className="relative w-52 h-72 rounded-[2.5rem] overflow-hidden shadow-2xl border border-white/30"
            style={{ background: 'linear-gradient(145deg, #8A9EE0 0%, #6273C3 100%)' }}
          >
            <img
              src="/assets/onboarding_hero_new.png"
              alt="AnemiaWatch – detect anemia with your camera"
              className="w-full h-full object-cover"
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
            />
            {/* Subtle inner shadow */}
            <div className="absolute inset-0 rounded-[2.5rem] shadow-inner pointer-events-none" />
          </div>

          {/* Heart badge floating bottom-right of card */}
          <div className="absolute -bottom-3 -right-3 w-11 h-11 bg-[#FF8D86] rounded-2xl shadow-lg flex items-center justify-center border-2 border-white">
            <HeartPulse className="w-5 h-5 text-white" />
          </div>
        </div>

        {/* Headline */}
        <h1 className="text-[26px] sm:text-3xl font-black text-white text-center tracking-tight leading-tight mb-3">
          Frequent Headaches?
        </h1>

        {/* Body copy */}
        <p className="text-white/85 text-sm text-center max-w-xs leading-relaxed font-medium mb-5">
          Headaches and fatigue could be early signs of anemia. Screen your estimated hemoglobin
          level non-invasively using your smartphone camera and AI.
        </p>

        {/* Disclaimer pill */}
        <div className="bg-white/15 backdrop-blur-sm rounded-2xl px-4 py-2.5 max-w-xs flex items-start gap-2.5 border border-white/20">
          <ShieldCheck className="w-4 h-4 text-white/80 mt-0.5 shrink-0" />
          <p className="text-[11px] text-white/90 leading-snug font-medium">
            AI screening provides early indicators; it is not a replacement for laboratory CBC tests.
          </p>
        </div>
      </div>

      {/* ── Action buttons ── */}
      <div className="px-6 pb-6 space-y-3 shrink-0">
        {/* Primary row: Sign In + Register */}
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => navigate('/login')}
            className="py-4 bg-white text-[#7185D1] font-black rounded-2xl shadow-lg active:scale-95 transition-all text-sm tracking-wide"
          >
            Sign In
          </button>
          <button
            onClick={() => navigate('/register')}
            className="py-4 bg-white text-[#7185D1] font-black rounded-2xl shadow-lg active:scale-95 transition-all text-sm tracking-wide"
          >
            Register
          </button>
        </div>

        {/* Guest explore link */}
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
          className="w-full py-2.5 flex items-center justify-center gap-1.5 text-white/80 hover:text-white text-xs font-semibold transition-colors"
        >
          <span>Explore as Guest</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>

        {/* Branding wordmark */}
        <div className="flex items-center justify-center gap-1.5 pt-1 opacity-75">
          <div className="w-5 h-5 rounded-full bg-[#FF8D86] flex items-center justify-center">
            <span className="text-[9px] font-black text-white">a</span>
          </div>
          <span className="text-xs font-bold text-white/90 tracking-widest lowercase">anem.ai</span>
        </div>
      </div>
    </div>
  );
};
