import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { HeartPulse } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const SplashScreen: React.FC = () => {
  const navigate = useNavigate();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading) {
      const timer = setTimeout(() => {
        if (user) {
          navigate(user.role === 'doctor' ? '/doctor' : '/home');
        } else {
          navigate('/onboarding');
        }
      }, 1800);
      return () => clearTimeout(timer);
    }
  }, [user, loading, navigate]);

  return (
    <div className="flex-1 bg-brand-primary flex flex-col items-center justify-center p-6 text-white relative">
      <div className="flex flex-col items-center animate-fade-in">
        {/* Pulsing Medical Icon */}
        <div className="w-24 h-24 rounded-3xl bg-white/15 backdrop-blur-md flex items-center justify-center mb-6 shadow-inner border border-white/20">
          <HeartPulse className="w-14 h-14 text-white animate-pulse" />
        </div>

        <h1 className="text-3xl font-extrabold tracking-tight mb-2">AnemiaWatch</h1>
        <p className="text-white/80 text-sm font-medium text-center tracking-wide">
          "Your health, one scan at a time."
        </p>
      </div>

      {/* Loading dots */}
      <div className="absolute bottom-16 flex items-center space-x-2">
        <div className="w-2.5 h-2.5 rounded-full bg-white/60 animate-bounce" style={{ animationDelay: '0ms' }} />
        <div className="w-2.5 h-2.5 rounded-full bg-white animate-bounce" style={{ animationDelay: '150ms' }} />
        <div className="w-2.5 h-2.5 rounded-full bg-white/60 animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>

      <div className="absolute bottom-6 text-[10px] text-white/50 tracking-wider">
        HF26-35 AI Healthcare Project
      </div>
    </div>
  );
};
