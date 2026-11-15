import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff, AlertCircle, ArrowLeft, Stethoscope, User } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export const LoginScreen: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!email || !password) {
      setError('Please enter your email and password.');
      return;
    }
    setLoading(true);
    try {
      const res = await api.login({ email, password });
      login(res.access_token, res.user);
      navigate(res.user.role === 'doctor' ? '/doctor' : '/home');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your email and password.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async (role: 'patient' | 'doctor') => {
    setError(null);
    setLoading(true);
    const demoEmail = role === 'doctor' ? 'doctor@test.com' : 'test@gmail.com';
    const demoPass  = role === 'doctor' ? 'doctor1234'      : 'test1234';
    try {
      try {
        const res = await api.login({ email: demoEmail, password: demoPass });
        login(res.access_token, res.user);
        navigate(role === 'doctor' ? '/doctor' : '/home');
      } catch {
        // If demo user doesn't exist yet, auto-register
        const regRes = await api.register({
          email: demoEmail,
          password: demoPass,
          full_name: role === 'doctor' ? 'Dr. Test Doctor' : 'Test Patient',
          role: role,
          age: role === 'doctor' ? 35 : 24,
          sex: role === 'doctor' ? 'male' : 'female',
          is_pregnant: false
        });
        login(regRes.access_token, regRes.user);
        navigate(role === 'doctor' ? '/doctor' : '/home');
      }
    } catch (err: any) {
      setError(err.message || 'Demo login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 bg-brand-primary flex flex-col justify-end text-brand-text relative">
      {/* Top Header */}
      <div className="p-5 flex items-center justify-between text-white shrink-0">
        <button
          onClick={() => navigate('/onboarding')}
          className="p-2 bg-white/15 rounded-full hover:bg-white/25 active:scale-95 transition-all"
        >
          <ArrowLeft className="w-5 h-5 text-white" />
        </button>
        <span className="text-sm font-bold tracking-wide">Sign in to AnemiaWatch</span>
        <div className="w-9" />
      </div>

      {/* Top Graphic Area */}
      <div className="flex-1 flex flex-col items-center justify-center p-4 text-white">
        <h2 className="text-2xl font-bold tracking-tight mb-1 text-center">Welcome Back</h2>
        <p className="text-xs text-white/80 text-center">Monitor your blood health regularly</p>
      </div>

      {/* Bottom Sheet Card matching InShot_20240621_080337187_frame_189.png */}
      <div className="bg-white rounded-t-[32px] p-6 shadow-2xl flex flex-col animate-slide-up">
        <h3 className="text-xl font-bold text-slate-800 text-center mb-5">Sign In</h3>

        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-600 text-xs rounded-xl p-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email field */}
          <div className="relative">
            <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
              Email
            </label>
            <div className="relative">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@email.com"
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:outline-none focus:border-brand-primary focus:bg-white transition-all pl-11"
              />
              <Mail className="w-4 h-4 text-slate-400 absolute left-4 top-3.5" />
            </div>
          </div>

          {/* Password field */}
          <div className="relative">
            <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:outline-none focus:border-brand-primary focus:bg-white transition-all pl-11 pr-11"
              />
              <Lock className="w-4 h-4 text-slate-400 absolute left-4 top-3.5" />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-3.5 text-slate-400 hover:text-slate-600"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 bg-brand-primary text-white font-bold rounded-2xl shadow-md hover:bg-brand-darkPeriwinkle active:scale-95 transition-all text-sm disabled:opacity-50 mt-2"
          >
            {loading ? 'Processing...' : 'Sign In'}
          </button>
        </form>

        {/* Demo Fast Login Pills */}
        <div className="mt-5 pt-4 border-t border-slate-100">
          <p className="text-[11px] text-slate-400 text-center mb-2.5 font-medium">Or try a demo account:</p>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleDemoLogin('patient')}
              className="py-2.5 px-3 bg-brand-secondary/60 hover:bg-brand-secondary text-brand-primary rounded-xl text-xs font-semibold flex flex-col items-center gap-0.5 transition-all"
            >
              <User className="w-3.5 h-3.5" />
              <span>Patient</span>
              <span className="text-[9px] opacity-70 font-normal">test@gmail.com</span>
            </button>
            <button
              onClick={() => handleDemoLogin('doctor')}
              className="py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold flex flex-col items-center gap-0.5 transition-all"
            >
              <Stethoscope className="w-3.5 h-3.5" />
              <span>Doctor</span>
              <span className="text-[9px] opacity-60 font-normal">doctor@test.com</span>
            </button>
          </div>
        </div>

        {/* Register link */}
        <p className="text-center text-xs text-slate-500 mt-5">
          Don't have an account?{' '}
          <Link to="/register" className="text-brand-primary font-bold hover:underline">
            Register Now
          </Link>
        </p>
      </div>
    </div>
  );
};
