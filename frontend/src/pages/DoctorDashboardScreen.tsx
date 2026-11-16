import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Stethoscope, Users, Activity, AlertTriangle, Download, Search,
  ChevronRight, Smartphone, LogOut, ShieldAlert
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api, getImageUrl } from '../services/api';

export const DoctorDashboardScreen: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [summary, setSummary] = useState<any>(null);
  const [patients, setPatients] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<any>(null);
  const [selectedScreening, setSelectedScreening] = useState<any>(null);
  const [, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'patients' | 'reviews'>('overview');

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const dashData = await api.getDoctorDashboard();
      setSummary(dashData);

      const patData = await api.getDoctorPatients(search);
      setPatients(patData.patients || []);
    } catch (err: any) {
      console.error('Doctor dashboard load failed:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, [search]);

  const viewPatientDetail = async (patientId: number | string) => {
    try {
      const res = await api.getDoctorPatientDetail(patientId);
      setSelectedPatient(res);
      if (res.history && res.history.length > 0) {
        setSelectedScreening(res.history[res.history.length - 1]);
      } else {
        setSelectedScreening(null);
      }
      setActiveTab('reviews');
    } catch (err) {
      alert('Failed to retrieve patient data.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans">
      {/* Top Clinical Header Bar */}
      <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between sticky top-0 z-30 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-primary text-white flex items-center justify-center shadow-md">
            <Stethoscope className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-black text-slate-800 tracking-tight">AnemiaWatch Clinical Portal</h1>
              <span className="text-[10px] font-bold bg-brand-secondary text-brand-primary px-2.5 py-0.5 rounded-full uppercase">
                Doctor Mode
              </span>
            </div>
            <p className="text-xs text-slate-400">AI-Assisted Non-Invasive Hemoglobin Triage System</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/home')}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-all"
          >
            <Smartphone className="w-4 h-4 text-brand-primary" />
            <span>View Patient Portal</span>
          </button>

          <div className="h-6 w-px bg-slate-200" />

          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs">
              {user?.full_name?.charAt(0) || 'D'}
            </div>
            <div className="text-right hidden sm:block">
              <span className="text-xs font-bold text-slate-800 block">{user?.full_name || 'Dr. Sarah Smith'}</span>
              <span className="text-[10px] text-slate-400 block">{user?.email || 'sarah@hospital.org'}</span>
            </div>
          </div>

          <button
            onClick={logout}
            className="p-2 text-slate-400 hover:text-red-600 rounded-xl hover:bg-red-50 transition-colors"
            title="Sign Out"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 space-y-6">
        {/* Verification Status Banner */}
        {user?.doctor_info?.verification_status === 'pending' && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-center justify-between shadow-xs">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-amber-900">Medical License Verification In Progress</h4>
                <p className="text-xs text-amber-700 mt-0.5">
                  Your credentials ({user?.doctor_info?.medical_registration_number} - {user?.doctor_info?.hospital_or_clinic}) have been submitted to the health authority admin team. Full patient records become accessible once verified.
                </p>
              </div>
            </div>
            <span className="text-[11px] font-bold text-amber-800 bg-amber-200/60 px-3 py-1 rounded-full uppercase tracking-wider shrink-0">
              Pending Approval
            </span>
          </div>
        )}

        {user?.doctor_info?.verification_status === 'rejected' && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-center justify-between shadow-xs">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-red-100 text-red-700 flex items-center justify-center shrink-0">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-red-900">Verification Rejected</h4>
                <p className="text-xs text-red-700 mt-0.5">
                  Your medical credentials could not be verified by the administrator. Please update your registration details or contact hospital administration.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex gap-2 border-b border-slate-200 pb-3">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'overview'
                ? 'bg-brand-primary text-white shadow-sm'
                : 'text-slate-600 hover:bg-white'
            }`}
          >
            Clinical Overview
          </button>
          <button
            onClick={() => setActiveTab('patients')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'patients'
                ? 'bg-brand-primary text-white shadow-sm'
                : 'text-slate-600 hover:bg-white'
            }`}
          >
            Patient List ({patients.length})
          </button>
          <button
            onClick={() => setActiveTab('reviews')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'reviews'
                ? 'bg-brand-primary text-white shadow-sm'
                : 'text-slate-600 hover:bg-white'
            }`}
          >
            Image & Segmentation Review
          </button>
        </div>

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-6 animate-fade-in">
            {/* Metric KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-5 rounded-3xl shadow-xs border border-slate-200/80 flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                    Total Patients
                  </span>
                  <span className="text-3xl font-black text-slate-800 mt-1 block">
                    {summary?.metrics?.total_patients || 0}
                  </span>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-brand-secondary text-brand-primary flex items-center justify-center">
                  <Users className="w-6 h-6" />
                </div>
              </div>

              <div className="bg-white p-5 rounded-3xl shadow-xs border border-slate-200/80 flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                    Total Screenings
                  </span>
                  <span className="text-3xl font-black text-slate-800 mt-1 block">
                    {summary?.metrics?.total_screenings || 0}
                  </span>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <Activity className="w-6 h-6" />
                </div>
              </div>

              <div className="bg-white p-5 rounded-3xl shadow-xs border border-slate-200/80 flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-amber-600 uppercase tracking-wider block">
                    Anemia Cases Flagged
                  </span>
                  <span className="text-3xl font-black text-amber-600 mt-1 block">
                    {summary?.metrics?.anemic_count || 0}
                  </span>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6" />
                </div>
              </div>

              <div className="bg-white p-5 rounded-3xl shadow-xs border border-slate-200/80 flex items-center justify-between">
                <div>
                  <span className="text-[11px] font-bold text-red-600 uppercase tracking-wider block">
                    Severe Anemia Cases Flagged
                  </span>
                  <span className="text-3xl font-black text-red-600 mt-1 block">
                    {summary?.metrics?.severe_cases_flagged || 0}
                  </span>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center">
                  <ShieldAlert className="w-6 h-6" />
                </div>
              </div>
            </div>

            {/* Recent Screenings Table */}
            <div className="bg-white rounded-3xl shadow-xs border border-slate-200/80 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-black text-slate-800 uppercase tracking-wider">
                  Recent Inbound Screenings
                </h3>
                <span className="text-xs text-slate-400">Realtime Sync</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 text-slate-400 text-[11px] uppercase">
                      <th className="pb-3 font-bold">Patient</th>
                      <th className="pb-3 font-bold">Method</th>
                      <th className="pb-3 font-bold">Estimated Hb</th>
                      <th className="pb-3 font-bold">Category</th>
                      <th className="pb-3 font-bold">Confidence</th>
                      <th className="pb-3 font-bold">Time</th>
                      <th className="pb-3 font-bold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {summary?.recent_screenings?.map((s: any) => (
                      <tr key={s.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3.5 font-bold text-slate-800">{s.patient_name}</td>
                        <td className="py-3.5 text-slate-600 capitalize">
                          {s.screening_type === 'nail' ? 'Fingernail' : 'Conjunctiva'}
                        </td>
                        <td className="py-3.5 font-black text-brand-primary">
                          {typeof s.estimated_hb === 'number' ? s.estimated_hb.toFixed(1) : (s.estimated_hb || 'N/A')} {s.unit || 'g/dL'}
                        </td>
                        <td className="py-3.5">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-black ${
                              (s.category || '').includes('Severe')
                                ? 'bg-red-100 text-red-700'
                                : (s.category || '').includes('Anemia')
                                ? 'bg-amber-100 text-amber-700'
                                : 'bg-emerald-100 text-emerald-700'
                            }`}
                          >
                            {s.category || 'Normal'}
                          </span>
                        </td>
                        <td className="py-3.5 text-slate-600 font-semibold">{typeof s.confidence === 'number' ? s.confidence.toFixed(1) : (s.confidence || '0')}%</td>
                        <td className="py-3.5 text-slate-400">{new Date(s.created_at).toLocaleString('en-US')}</td>
                        <td className="py-3.5 text-right space-x-2">
                          <button
                            onClick={() => viewPatientDetail(s.patient_id)}
                            className="px-2.5 py-1 bg-brand-secondary text-brand-primary hover:bg-brand-primary hover:text-white rounded-lg font-bold transition-all"
                          >
                            Review
                          </button>
                          <a
                            href={api.getPdfUrl(s.id)}
                            target="_blank"
                            rel="noreferrer"
                            className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-bold transition-all inline-flex items-center gap-1"
                          >
                            <Download className="w-3 h-3" />
                            <span>PDF</span>
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* PATIENTS TAB */}
        {activeTab === 'patients' && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex items-center justify-between gap-4">
              <div className="relative flex-1 max-w-md">
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search patient by name or email..."
                  className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-2xl text-xs focus:outline-none focus:border-brand-primary shadow-xs"
                />
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {patients.map((p) => (
                <div
                  key={p.id}
                  onClick={() => viewPatientDetail(p.id)}
                  className="bg-white p-5 rounded-3xl shadow-xs hover:shadow-md border border-slate-200/80 transition-all cursor-pointer flex flex-col justify-between group"
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-10 h-10 rounded-2xl bg-brand-secondary text-brand-primary font-black flex items-center justify-center text-sm">
                          {p.full_name.charAt(0)}
                        </div>
                        <div>
                          <h4 className="text-xs font-black text-slate-800 group-hover:text-brand-primary transition-colors">
                            {p.full_name}
                          </h4>
                          <span className="text-[10px] text-slate-400">{p.email}</span>
                        </div>
                      </div>
                      <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-semibold">
                        {p.age} yrs • {p.sex === 'female' ? 'Female' : 'Male'}
                      </span>
                    </div>

                    <div className="bg-slate-50 p-3 rounded-2xl border border-slate-100 text-[11px] space-y-1">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Total Screenings:</span>
                        <span className="font-bold text-slate-700">{p.total_screenings} screenings</span>
                      </div>
                      {p.latest_screening ? (
                        <div className="flex justify-between">
                          <span className="text-slate-400">Latest Hb:</span>
                          <span className="font-black text-brand-primary">
                            {p.latest_screening.hb} g/dL ({p.latest_screening.category})
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">No screenings recorded</span>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-brand-primary">
                    <span>View History & Images</span>
                    <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* REVIEWS & DETAILED SCREENING INSPECTION */}
        {activeTab === 'reviews' && (
          <div className="space-y-6 animate-fade-in">
            {selectedPatient ? (
              <div className="bg-white rounded-3xl p-6 shadow-xs border border-slate-200">
                <div className="flex flex-wrap items-center justify-between pb-4 border-b border-slate-100 gap-3">
                  <div>
                    <h3 className="text-base font-extrabold text-slate-800">
                      Clinical Record: {selectedPatient.patient.full_name}
                    </h3>
                    <p className="text-xs text-slate-400">
                      {selectedPatient.patient.email} • {selectedPatient.patient.age} Years •{' '}
                      {selectedPatient.patient.sex === 'female' ? 'Female' : 'Male'}
                      {selectedPatient.patient.is_pregnant ? ' (Pregnant)' : ''}
                    </p>
                  </div>
                  <button
                    onClick={() => setActiveTab('patients')}
                    className="text-xs font-bold text-brand-primary bg-brand-secondary px-3.5 py-1.5 rounded-xl hover:bg-brand-primary hover:text-white transition-all"
                  >
                    &larr; Back to Patients
                  </button>
                </div>

                {/* Screening Select Tabs */}
                {selectedPatient.history?.length > 0 ? (
                  <div className="mt-4">
                    <div className="flex gap-2 overflow-x-auto pb-2">
                      {selectedPatient.history.map((h: any) => (
                        <button
                          key={h.id}
                          onClick={() => setSelectedScreening(h)}
                          className={`px-3 py-1.5 rounded-xl text-xs font-bold shrink-0 transition-all ${
                            selectedScreening?.id === h.id
                              ? 'bg-brand-primary text-white shadow-xs'
                              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                          }`}
                        >
                          Screening #{h.id} ({h.estimated_hb} g/dL) - {new Date(h.created_at).toLocaleDateString('en-US')}
                        </button>
                      ))}
                    </div>

                    {/* Detailed Side-by-Side Review */}
                    {selectedScreening && (
                      <div className="mt-5 grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Left: Images */}
                        <div className="space-y-4">
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">
                                Original Capture
                              </span>
                              <div className="aspect-[4/3] bg-slate-100 rounded-2xl overflow-hidden border border-slate-200">
                                <img
                                  src={getImageUrl(selectedScreening.original_image_url)}
                                  alt="Original"
                                  className="w-full h-full object-cover"
                                />
                              </div>
                            </div>
                            <div>
                              <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">
                                AI Segmentation & ROI
                              </span>
                              <div className="aspect-[4/3] bg-slate-100 rounded-2xl overflow-hidden border border-slate-200">
                                <img
                                  src={getImageUrl(selectedScreening.processed_image_url)}
                                  alt="Annotated"
                                  className="w-full h-full object-cover"
                                />
                              </div>
                            </div>
                          </div>

                          <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100 text-[11px] text-slate-600 flex items-center justify-between">
                            <span>Quality Status: <b>{selectedScreening.quality_status}</b></span>
                            <a
                              href={api.getPdfUrl(selectedScreening.id)}
                              target="_blank"
                              rel="noreferrer"
                              className="px-3 py-1 bg-brand-primary text-white rounded-xl font-bold flex items-center gap-1 shadow-xs hover:bg-brand-darkPeriwinkle"
                            >
                              <Download className="w-3.5 h-3.5" />
                              <span>Download Medical Report (PDF)</span>
                            </a>
                          </div>
                        </div>

                        {/* Right: Clinical Assessment */}
                        <div className="bg-slate-50 rounded-3xl p-5 border border-slate-200 flex flex-col justify-between">
                          <div>
                            <span className="text-[10px] font-extrabold uppercase tracking-widest text-slate-400 block mb-2">
                              AI Triage Parameters
                            </span>

                            <div className="grid grid-cols-2 gap-3 mb-4">
                              <div className="bg-white p-3 rounded-2xl border border-slate-200/60">
                                <span className="text-[10px] text-slate-400 block">Hemoglobin Level</span>
                                <span className="text-2xl font-black text-brand-primary">
                                  {selectedScreening.estimated_hb} {selectedScreening.unit}
                                </span>
                              </div>
                              <div className="bg-white p-3 rounded-2xl border border-slate-200/60">
                                <span className="text-[10px] text-slate-400 block">Classification Status</span>
                                <span
                                  className={`text-sm font-black mt-1 block ${
                                    selectedScreening.is_anemic ? 'text-red-600' : 'text-emerald-600'
                                  }`}
                                >
                                  {selectedScreening.category}
                                </span>
                              </div>
                            </div>

                            <div className="space-y-2 text-xs text-slate-600">
                              <p>
                                <b>Method:</b> {selectedScreening.screening_type === 'nail' ? 'Nail Bed (42-Percentile ElasticNet)' : 'Palpebral Conjunctiva (Erythema Index)'}
                              </p>
                              <p>
                                <b>Confidence Score:</b> {selectedScreening.confidence?.toFixed(1)}%
                              </p>
                              <p>
                                <b>Patient Medical Notes:</b> {selectedPatient.patient.medical_notes || 'No chronic medical history recorded.'}
                              </p>
                            </div>
                          </div>

                          <div className="mt-4 pt-3 border-t border-slate-200 text-[10px] text-slate-400 leading-tight">
                            * Non-invasive camera screening assessments should always be confirmed with official laboratory Complete Blood Count (CBC) venous testing before transfusions or high-dose therapy.
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 mt-4 italic">This patient has not completed any screenings yet.</p>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-3xl p-12 text-center text-slate-400 border border-slate-200">
                <Users className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <h4 className="text-sm font-bold text-slate-700">Select a Patient First</h4>
                <p className="text-xs mt-1">Open the "Patient List" tab and click on a patient name to review their images and segmentation.</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};
