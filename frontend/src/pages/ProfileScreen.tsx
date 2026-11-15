import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { BottomNav } from '../components/BottomNav';

export const ProfileScreen: React.FC = () => {
  const navigate = useNavigate();
  const { user, refreshUser, logout } = useAuth();

  const [fullName, setFullName] = useState(user?.full_name || '');
  const [age, setAge] = useState(user?.profile?.age || 24);
  const [sex, setSex] = useState<'female' | 'male'>(user?.profile?.sex || 'female');
  const [isPregnant, setIsPregnant] = useState(user?.profile?.is_pregnant || false);
  const [bloodType, setBloodType] = useState(user?.profile?.blood_type || 'O+');
  const [phone, setPhone] = useState(user?.profile?.phone || '');
  const [notes, setNotes] = useState(user?.profile?.medical_notes || '');

  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);
    try {
      await api.updateProfile({
        full_name: fullName,
        age: Number(age),
        sex,
        is_pregnant: isPregnant,
        blood_type: bloodType,
        phone,
        medical_notes: notes,
      });
      await refreshUser();
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      alert(`Failed to save: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 bg-brand-primary flex flex-col justify-between text-brand-text relative">
      <div className="px-5 pt-3 pb-3 flex items-center justify-between text-white shrink-0">
        <button
          onClick={() => navigate('/home')}
          className="p-2 bg-white/15 rounded-full hover:bg-white/25 active:scale-95 transition-all"
        >
          <ArrowLeft className="w-5 h-5 text-white" />
        </button>
        <span className="text-base font-bold tracking-wide">Patient Profile</span>
        <button
          onClick={logout}
          title="Sign Out"
          className="p-2 bg-white/15 rounded-full hover:bg-white/25 active:scale-95 transition-all text-white"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 min-h-0 bg-[#F4F6FC] rounded-t-[36px] px-5 pt-5 pb-4 flex flex-col overflow-y-auto overscroll-contain shadow-2xl">
        <div className="bg-white rounded-3xl p-5 shadow-card border border-slate-100 mb-4 text-center">
          <div className="w-20 h-20 rounded-full bg-brand-secondary text-brand-primary flex items-center justify-center font-black text-2xl mx-auto mb-3 shadow-inner">
            {fullName.charAt(0) || 'P'}
          </div>
          <h2 className="text-base font-extrabold text-slate-800">{fullName}</h2>
          <p className="text-xs text-slate-400 mt-0.5">{user?.email}</p>
          <span className="inline-block mt-2 text-[10px] font-bold text-brand-primary bg-brand-secondary px-3 py-1 rounded-full uppercase tracking-wider">
            Verified Patient Account
          </span>
        </div>

        {savedSuccess && (
          <div className="mb-4 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-2xl p-3 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Profile successfully updated. WHO threshold adjusted accordingly.</span>
          </div>
        )}

        <form onSubmit={handleSave} className="bg-white rounded-3xl p-5 shadow-card border border-slate-100 space-y-3.5 mb-4">
          <span className="text-xs font-black text-slate-700 uppercase tracking-wider block border-b border-slate-100 pb-2">
            Clinical Demographic Data
          </span>

          <div>
            <label className="text-[11px] font-semibold text-slate-500 block mb-1">Full Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:border-brand-primary"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-500 block mb-1">Age (Years)</label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(parseInt(e.target.value) || 20)}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:border-brand-primary"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-500 block mb-1">Sex</label>
              <select
                value={sex}
                onChange={(e) => setSex(e.target.value as any)}
                className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:border-brand-primary"
              >
                <option value="female">Female</option>
                <option value="male">Male</option>
              </select>
            </div>
          </div>

          {sex === 'female' && (
            <div className="bg-brand-secondary/40 p-3 rounded-xl border border-brand-secondary flex items-center justify-between">
              <span className="text-xs font-medium text-slate-700">Pregnancy Status</span>
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

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-semibold text-slate-500 block mb-1">Blood Type</label>
              <input
                type="text"
                value={bloodType}
                onChange={(e) => setBloodType(e.target.value)}
                placeholder="e.g. O+, B+"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:border-brand-primary"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-500 block mb-1">Phone Number</label>
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+1 234 567 890"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:border-brand-primary"
              />
            </div>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-500 block mb-1">Medical History Notes</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Iron supplement history, thalassemia, or blood transfusion history..."
              className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:border-brand-primary"
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full py-3 bg-brand-primary text-white rounded-2xl text-xs font-bold shadow-md hover:bg-brand-darkPeriwinkle active:scale-95 transition-all disabled:opacity-50 mt-2"
          >
            {saving ? 'Saving...' : 'Update Profile'}
          </button>
        </form>
      </div>

      <BottomNav />
    </div>
  );
};
