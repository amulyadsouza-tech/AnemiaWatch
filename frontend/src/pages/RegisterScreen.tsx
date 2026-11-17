import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, User, ArrowLeft, AlertCircle, Heart, Award, Building, Phone } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

export const RegisterScreen: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'patient' | 'doctor'>('patient');

  // Patient-specific state
  const [age, setAge] = useState(24);
  const [sex, setSex] = useState<'female' | 'male'>('female');
  const [isPregnant, setIsPregnant] = useState(false);

  // Doctor-specific state
  const [medRegNo, setMedRegNo] = useState('');
  const [qualification, setQualification] = useState('');
  const [specialization, setSpecialization] = useState('General Medicine');
  const [hospital, setHospital] = useState('');
  const [doctorPhone, setDoctorPhone] = useState('');

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const cleanName = fullName.trim();
    const cleanEmail = email.trim();
    if (!cleanName || !cleanEmail || !password) {
      setError('Please complete all required fields.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long and contain both letters and digits.');
      return;
    }

    setLoading(true);

    if (role === 'doctor') {
      if (!medRegNo.trim() || !qualification.trim() || !hospital.trim()) {
        setError('Please provide medical registration number, qualification, and hospital affiliation.');
        setLoading(false);
        return;
      }
      try {
        const res = await api.registerDoctor({
          email: cleanEmail,
          password,
          full_name: cleanName,
          medical_registration_number: medRegNo.trim(),
          qualification: qualification.trim(),
          specialization: specialization.trim(),
          hospital_or_clinic: hospital.trim(),
          phone_number: doctorPhone.trim() || undefined,
        });
        login(res.access_token, res.user, res.refresh_token);
        navigate('/doctor');
      } catch (err: any) {
        setError(err.message || 'Doctor registration failed');
      } finally {
        setLoading(false);
      }
      return;
    }

    try {
      const res = await api.register({
        email: cleanEmail,
        password,
        full_name: cleanName,
        role: 'patient',
        age: Number(age) || 24,
        sex,
        pregnancy_status: isPregnant,
        is_pregnant: isPregnant,
      });
      login(res.access_token, res.user, res.refresh_token);
      navigate('/home');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 bg-brand-primary flex flex-col justify-end text-brand-text relative">
      <div className="p-4 flex items-center justify-between text-white shrink-0">
        <button
          onClick={() => navigate('/onboarding')}
          className="p-2 bg-white/15 rounded-full hover:bg-white/25 active:scale-95 transition-all"
        >
          <ArrowLeft className="w-5 h-5 text-white" />
        </button>
        <span className="text-sm font-bold tracking-wide">
          {role === 'doctor' ? 'Clinician Registration' : 'Patient Registration'}
        </span>
        <div className="w-9" />
      </div>

      {/* Hero illustration + headline */}
      <div className="flex flex-col items-center px-4 pb-3 gap-3">
        <div className="w-28 h-24 rounded-2xl bg-white/15 border border-white/20 overflow-hidden flex items-center justify-center shadow-md">
          <img
            src="/assets/doctor_patient_hero.png"
            alt="Doctor and patient illustration"
            className="w-full h-full object-contain p-1"
          />
        </div>
        <div className="text-white text-center">
          <h2 className="text-xl font-bold tracking-tight">Create AnemiaWatch Account</h2>
          <p className="text-xs text-white/80 mt-0.5">
            {role === 'doctor'
              ? 'Join the certified clinician network for clinical review'
              : 'Complete your details for WHO anemia threshold calibration'}
          </p>
        </div>
      </div>

      <div className="bg-white rounded-t-[32px] p-6 shadow-2xl max-h-[85vh] overflow-y-auto">
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-600 text-xs rounded-xl p-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-3.5">
          {/* Account Role Selector */}
          <div>
            <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
              Account Type
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setRole('patient')}
                className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                  role === 'patient'
                    ? 'bg-brand-primary text-white border-brand-primary'
                    : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                }`}
              >
                Patient
              </button>
              <button
                type="button"
                onClick={() => setRole('doctor')}
                className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${
                  role === 'doctor'
                    ? 'bg-brand-primary text-white border-brand-primary'
                    : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                }`}
              >
                Doctor / Clinician
              </button>
            </div>
          </div>

          {/* Full Name */}
          <div>
            <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
              {role === 'doctor' ? 'Full Name & Title' : 'Full Name'}
            </label>
            <div className="relative">
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder={role === 'doctor' ? 'e.g. Dr. Jane Smith' : 'e.g. Jane Doe'}
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-brand-primary pl-10"
              />
              <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            </div>
          </div>

          {/* Email */}
          <div>
            <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
              Email
            </label>
            <div className="relative">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@email.com"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-brand-primary pl-10"
              />
              <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            </div>
          </div>

          {/* Password */}
          <div>
            <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
              Password
            </label>
            <div className="relative">
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 8 chars, 1 letter & 1 digit"
                className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-brand-primary pl-10"
              />
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
            </div>
          </div>

          {/* PATIENT FIELDS */}
          {role === 'patient' && (
            <>
              {/* Age & Sex Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
                    Age (Years)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="120"
                    value={age}
                    onChange={(e) => setAge(parseInt(e.target.value) || 20)}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-brand-primary"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
                    Sex
                  </label>
                  <select
                    value={sex}
                    onChange={(e) => setSex(e.target.value as any)}
                    className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-brand-primary"
                  >
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                  </select>
                </div>
              </div>

              {/* Pregnancy condition (for women) */}
              {sex === 'female' && (
                <div className="bg-brand-secondary/40 p-3 rounded-xl border border-brand-secondary flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Heart className="w-4 h-4 text-brand-accent" />
                    <span className="text-xs font-medium text-slate-700">Currently Pregnant?</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isPregnant}
                      onChange={(e) => setIsPregnant(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-brand-primary"></div>
                  </label>
                </div>
              )}
            </>
          )}

          {/* DOCTOR FIELDS */}
          {role === 'doctor' && (
            <div className="space-y-3 pt-1 border-t border-slate-100">
              <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider block">
                Professional Credentials
              </span>

              {/* Medical Reg Number */}
              <div>
                <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
                  Medical Registration / License No.
                </label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    value={medRegNo}
                    onChange={(e) => setMedRegNo(e.target.value)}
                    placeholder="e.g. MED-88421-NY"
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-brand-primary pl-10"
                  />
                  <Award className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                </div>
              </div>

              {/* Qualification & Specialization */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
                    Qualification
                  </label>
                  <input
                    type="text"
                    required
                    value={qualification}
                    onChange={(e) => setQualification(e.target.value)}
                    placeholder="e.g. MBBS, MD"
                    className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-brand-primary"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
                    Specialization
                  </label>
                  <input
                    type="text"
                    required
                    value={specialization}
                    onChange={(e) => setSpecialization(e.target.value)}
                    placeholder="e.g. Hematology"
                    className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-brand-primary"
                  />
                </div>
              </div>

              {/* Hospital Affiliation */}
              <div>
                <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
                  Hospital / Clinic Affiliation
                </label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    value={hospital}
                    onChange={(e) => setHospital(e.target.value)}
                    placeholder="e.g. St. Jude General Hospital"
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-brand-primary pl-10"
                  />
                  <Building className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                </div>
              </div>

              {/* Phone */}
              <div>
                <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">
                  Contact Phone (Optional)
                </label>
                <div className="relative">
                  <input
                    type="tel"
                    value={doctorPhone}
                    onChange={(e) => setDoctorPhone(e.target.value)}
                    placeholder="+1 555 123 4567"
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-brand-primary pl-10"
                  />
                  <Phone className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                </div>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 bg-brand-primary text-white font-bold rounded-2xl shadow-md hover:bg-brand-darkPeriwinkle active:scale-95 transition-all text-sm disabled:opacity-50 mt-4"
          >
            {loading ? 'Registering...' : role === 'doctor' ? 'Register as Doctor' : 'Register Now'}
          </button>
        </form>

        <p className="text-center text-xs text-slate-500 mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-brand-primary font-bold hover:underline">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
};
