import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Mail, Lock, User, ArrowLeft, AlertCircle, Heart,
  Award, Building, Phone, ChevronRight, Eye, EyeOff
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

// ── Reusable labelled input ──────────────────────────────────────────────────
interface InputFieldProps {
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  icon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  onRightIconClick?: () => void;
}

const InputField: React.FC<InputFieldProps> = ({
  label, type = 'text', value, onChange, placeholder, required,
  icon, rightIcon, onRightIconClick
}) => (
  <div className="space-y-1.5">
    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">
      {label}
    </label>
    <div className="relative">
      {icon && (
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
          {icon}
        </span>
      )}
      <input
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`w-full py-3 ${icon ? 'pl-10' : 'pl-4'} ${rightIcon ? 'pr-10' : 'pr-4'} bg-slate-50 border border-slate-200 rounded-2xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#7185D1]/30 focus:border-[#7185D1] transition-all`}
      />
      {rightIcon && (
        <button
          type="button"
          onClick={onRightIconClick}
          className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
        >
          {rightIcon}
        </button>
      )}
    </div>
  </div>
);

// ── Main component ───────────────────────────────────────────────────────────
export const RegisterScreen: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [role, setRole] = useState<'patient' | 'doctor'>('patient');
  const [step, setStep] = useState<1 | 2>(1); // step 1 = basics, step 2 = profile details

  // Shared
  const [fullName, setFullName]   = useState('');
  const [email, setEmail]         = useState('');
  const [password, setPassword]   = useState('');
  const [showPwd, setShowPwd]     = useState(false);

  // Patient
  const [age, setAge]             = useState('24');
  const [sex, setSex]             = useState<'female' | 'male'>('female');
  const [isPregnant, setIsPregnant] = useState(false);

  // Doctor
  const [medRegNo, setMedRegNo]       = useState('');
  const [qualification, setQual]      = useState('');
  const [specialization, setSpec]     = useState('General Medicine');
  const [hospital, setHospital]       = useState('');
  const [doctorPhone, setDoctorPhone] = useState('');

  const [error, setError]   = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // ── Step 1 → 2 validation ──
  const goToStep2 = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!fullName.trim() || !email.trim() || !password) {
      setError('Please fill in all fields to continue.'); return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.'); return;
    }
    setStep(2);
  };

  // ── Final submit ──
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    if (role === 'doctor') {
      if (!medRegNo.trim() || !qualification.trim() || !hospital.trim()) {
        setError('Medical registration number, qualification, and hospital are required.');
        setLoading(false); return;
      }
      try {
        const res = await api.registerDoctor({
          email: email.trim(), password,
          full_name: fullName.trim(),
          medical_registration_number: medRegNo.trim(),
          qualification: qualification.trim(),
          specialization: specialization.trim(),
          hospital_or_clinic: hospital.trim(),
          phone_number: doctorPhone.trim() || undefined,
        });
        login(res.access_token, res.user, res.refresh_token);
        navigate('/doctor');
      } catch (err: any) {
        setError(err.message || 'Doctor registration failed.');
      } finally { setLoading(false); }
      return;
    }

    try {
      const res = await api.register({
        email: email.trim(), password,
        full_name: fullName.trim(),
        role: 'patient',
        age: Number(age) || 24, sex,
        pregnancy_status: isPregnant,
        is_pregnant: isPregnant,
      });
      login(res.access_token, res.user, res.refresh_token);
      navigate('/home');
    } catch (err: any) {
      setError(err.message || 'Registration failed.');
    } finally { setLoading(false); }
  };

  // ── Progress dots ──
  const ProgressDots = () => (
    <div className="flex items-center gap-1.5 justify-center">
      {[1, 2].map((s) => (
        <div
          key={s}
          className={`rounded-full transition-all duration-300 ${
            step === s ? 'w-6 h-2 bg-[#7185D1]' : 'w-2 h-2 bg-slate-200'
          }`}
        />
      ))}
    </div>
  );

  return (
    <div className="flex-1 bg-[#F4F7FF] flex flex-col overflow-hidden">

      {/* ── Header ── */}
      <div className="bg-[#7185D1] px-5 pt-5 pb-10 relative overflow-hidden shrink-0">
        {/* Background blobs */}
        <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-white/10 blur-2xl" />
        <div className="absolute bottom-0 -left-6 w-32 h-32 rounded-full bg-white/8 blur-xl" />

        <div className="relative flex items-center gap-3 mb-5">
          <button
            onClick={() => step === 2 ? setStep(1) : navigate('/onboarding')}
            className="p-2 bg-white/20 rounded-full hover:bg-white/30 active:scale-95 transition-all"
          >
            <ArrowLeft className="w-5 h-5 text-white" />
          </button>
          <div>
            <h1 className="text-lg font-black text-white leading-none">
              {step === 1 ? 'Create Account' : role === 'doctor' ? 'Doctor Profile' : 'Your Health Profile'}
            </h1>
            <p className="text-white/70 text-xs mt-0.5">
              {step === 1
                ? 'Join AnemiaWatch – takes 60 seconds'
                : role === 'doctor'
                  ? 'Provide your medical credentials'
                  : 'Help us calibrate WHO anemia thresholds for you'}
            </p>
          </div>
        </div>

        <ProgressDots />
      </div>

      {/* ── Card sheet pulled up over header ── */}
      <div className="flex-1 -mt-6 bg-white rounded-t-[2rem] shadow-xl overflow-y-auto px-5 pt-6 pb-8">

        {/* Error banner */}
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-600 text-xs rounded-2xl p-3 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-500" />
            <span>{error}</span>
          </div>
        )}

        {/* ───────── STEP 1: Basics ───────── */}
        {step === 1 && (
          <form onSubmit={goToStep2} className="space-y-4">

            {/* Role toggle */}
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">I am a</p>
              <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 rounded-2xl">
                {(['patient', 'doctor'] as const).map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRole(r)}
                    className={`py-2.5 rounded-xl text-sm font-bold transition-all ${
                      role === r
                        ? 'bg-white text-[#7185D1] shadow-sm'
                        : 'text-slate-500'
                    }`}
                  >
                    {r === 'patient' ? '🧑‍⚕️ Patient' : '👨‍💼 Doctor'}
                  </button>
                ))}
              </div>
            </div>

            <InputField
              label="Full Name"
              value={fullName}
              onChange={setFullName}
              placeholder={role === 'doctor' ? 'e.g. Dr. Jane Smith' : 'e.g. Jane Doe'}
              required
              icon={<User className="w-4 h-4" />}
            />

            <InputField
              label="Email Address"
              type="email"
              value={email}
              onChange={setEmail}
              placeholder="name@email.com"
              required
              icon={<Mail className="w-4 h-4" />}
            />

            <InputField
              label="Password"
              type={showPwd ? 'text' : 'password'}
              value={password}
              onChange={setPassword}
              placeholder="Min 8 characters"
              required
              icon={<Lock className="w-4 h-4" />}
              rightIcon={showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              onRightIconClick={() => setShowPwd(!showPwd)}
            />

            {/* Strength hint */}
            {password.length > 0 && (
              <div className="flex gap-1">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className={`h-1 flex-1 rounded-full transition-all ${
                      password.length >= i * 4
                        ? i === 1 ? 'bg-red-400' : i === 2 ? 'bg-amber-400' : 'bg-emerald-400'
                        : 'bg-slate-200'
                    }`}
                  />
                ))}
              </div>
            )}

            <button
              type="submit"
              className="w-full py-4 bg-[#7185D1] text-white font-black rounded-2xl shadow-md active:scale-95 transition-all text-sm flex items-center justify-center gap-2 mt-2"
            >
              <span>Continue</span>
              <ChevronRight className="w-4 h-4" />
            </button>

            <p className="text-center text-xs text-slate-500 pt-1">
              Already have an account?{' '}
              <Link to="/login" className="text-[#7185D1] font-bold hover:underline">Sign In</Link>
            </p>
          </form>
        )}

        {/* ───────── STEP 2: Profile details ───────── */}
        {step === 2 && (
          <form onSubmit={handleRegister} className="space-y-4">

            {/* ── PATIENT profile ── */}
            {role === 'patient' && (
              <>
                <div className="bg-[#F4F7FF] rounded-2xl p-4 border border-[#E5E9FF]">
                  <p className="text-xs font-bold text-[#7185D1] mb-3 uppercase tracking-wider">
                    Health Profile
                  </p>

                  {/* Age */}
                  <div className="space-y-1.5 mb-3">
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Age</label>
                    <input
                      type="number" min="1" max="120"
                      value={age}
                      onChange={(e) => setAge(e.target.value)}
                      className="w-full py-3 px-4 bg-white border border-slate-200 rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-[#7185D1]/30 focus:border-[#7185D1] transition-all"
                    />
                  </div>

                  {/* Sex */}
                  <div className="space-y-1.5">
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Biological Sex</label>
                    <div className="grid grid-cols-2 gap-2">
                      {(['female', 'male'] as const).map((s) => (
                        <button
                          key={s} type="button" onClick={() => setSex(s)}
                          className={`py-2.5 rounded-xl text-sm font-semibold border transition-all ${
                            sex === s
                              ? 'bg-[#7185D1] text-white border-[#7185D1]'
                              : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                          }`}
                        >
                          {s === 'female' ? '♀ Female' : '♂ Male'}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Pregnancy toggle – only for female */}
                {sex === 'female' && (
                  <div className="bg-pink-50 border border-pink-100 rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Heart className="w-4 h-4 text-[#FF8D86]" />
                      <span className="text-sm font-medium text-slate-700">Currently Pregnant?</span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox" checked={isPregnant}
                        onChange={(e) => setIsPregnant(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-10 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#7185D1]" />
                    </label>
                  </div>
                )}

                {/* Info note */}
                <div className="bg-[#F4F7FF] border border-[#E5E9FF] rounded-2xl p-3 text-xs text-slate-500 leading-relaxed">
                  🔒 Your health data is encrypted and used only to calibrate WHO anemia thresholds for your screening results.
                </div>
              </>
            )}

            {/* ── DOCTOR profile ── */}
            {role === 'doctor' && (
              <div className="space-y-4">
                <div className="bg-[#F4F7FF] rounded-2xl p-4 border border-[#E5E9FF]">
                  <p className="text-xs font-bold text-[#7185D1] mb-3 uppercase tracking-wider">
                    Professional Credentials
                  </p>

                  <div className="space-y-3">
                    <InputField
                      label="Medical Registration / License No."
                      value={medRegNo} onChange={setMedRegNo}
                      placeholder="e.g. MED-88421-NY" required
                      icon={<Award className="w-4 h-4" />}
                    />

                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Qualification</label>
                        <input
                          type="text" required value={qualification}
                          onChange={(e) => setQual(e.target.value)}
                          placeholder="e.g. MBBS, MD"
                          className="w-full py-3 px-3 bg-white border border-slate-200 rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-[#7185D1]/30 focus:border-[#7185D1] transition-all"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Specialization</label>
                        <input
                          type="text" required value={specialization}
                          onChange={(e) => setSpec(e.target.value)}
                          placeholder="e.g. Hematology"
                          className="w-full py-3 px-3 bg-white border border-slate-200 rounded-2xl text-sm focus:outline-none focus:ring-2 focus:ring-[#7185D1]/30 focus:border-[#7185D1] transition-all"
                        />
                      </div>
                    </div>

                    <InputField
                      label="Hospital / Clinic Affiliation"
                      value={hospital} onChange={setHospital}
                      placeholder="e.g. St. Jude General Hospital" required
                      icon={<Building className="w-4 h-4" />}
                    />

                    <InputField
                      label="Contact Phone (Optional)"
                      type="tel"
                      value={doctorPhone} onChange={setDoctorPhone}
                      placeholder="+1 555 123 4567"
                      icon={<Phone className="w-4 h-4" />}
                    />
                  </div>
                </div>

                <div className="bg-amber-50 border border-amber-100 rounded-2xl p-3 text-xs text-amber-700 leading-relaxed">
                  ⚠️ Your medical credentials will be verified by an administrator before you gain access to patient records. You will receive access within 24 hours.
                </div>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-[#7185D1] text-white font-black rounded-2xl shadow-md active:scale-95 transition-all text-sm disabled:opacity-50"
            >
              {loading
                ? 'Creating account…'
                : role === 'doctor' ? 'Register as Doctor' : 'Create My Account'}
            </button>

            <p className="text-center text-xs text-slate-400">
              By registering you agree to our{' '}
              <span className="text-[#7185D1] font-semibold">Privacy Policy</span> and{' '}
              <span className="text-[#7185D1] font-semibold">Terms of Use</span>.
            </p>
          </form>
        )}
      </div>
    </div>
  );
};
