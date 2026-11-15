import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, Activity, ChevronRight, Download, Calendar } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, CartesianGrid } from 'recharts';
import { api } from '../services/api';
import { BottomNav } from '../components/BottomNav';
import type { ScreeningResult } from '../types';

export const HistoryScreen: React.FC = () => {
  const navigate = useNavigate();
  const [screenings, setScreenings] = useState<ScreeningResult[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    api.getHistory()
      .then((res) => setScreenings(res.screenings || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Format chart data chronologically
  const chartData = [...screenings]
    .reverse()
    .map((s, idx) => ({
      index: idx + 1,
      date: new Date(s.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      hb: s.estimated_hb,
      method: s.screening_type === 'nail' ? 'Nail' : 'Eyelid',
      category: s.category,
    }));

  return (
    <div className="flex-1 bg-brand-primary flex flex-col justify-between text-brand-text relative">
      {/* Top Header */}
      <div className="px-5 pt-3 pb-3 flex items-center justify-between text-white shrink-0">
        <button
          onClick={() => navigate('/home')}
          className="p-2 bg-white/15 rounded-full hover:bg-white/25 active:scale-95 transition-all"
        >
          <ArrowLeft className="w-5 h-5 text-white" />
        </button>
        <span className="text-base font-bold tracking-wide">Screening History</span>
        <div className="w-9" />
      </div>

      {/* Main Body */}
      <div className="flex-1 min-h-0 bg-[#F4F6FC] rounded-t-[36px] px-5 pt-5 pb-4 flex flex-col overflow-y-auto overscroll-contain shadow-2xl">
        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center p-6 text-slate-400">
            <div className="w-8 h-8 rounded-full border-4 border-brand-primary border-t-transparent animate-spin mb-3" />
            <p className="text-xs">Loading history...</p>
          </div>
        ) : screenings.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
            <Clock className="w-16 h-16 text-slate-300 mb-3" />
            <h3 className="text-sm font-bold text-slate-700 mb-1">No Screening History Yet</h3>
            <p className="text-xs max-w-xs mb-5">
              You haven't performed any hemoglobin screenings yet. Start a scan now to monitor your blood health.
            </p>
            <button
              onClick={() => navigate('/screening-select')}
              className="py-3 px-6 bg-brand-primary text-white rounded-2xl text-xs font-bold shadow-md hover:bg-brand-darkPeriwinkle"
            >
              Start First Screening
            </button>
          </div>
        ) : (
          <>
            {/* Trend Graph Card */}
            <div className="bg-white rounded-3xl p-4 shadow-card border border-slate-100 mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-extrabold text-slate-800 flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-brand-primary" />
                  <span>Hemoglobin Trend (g/dL)</span>
                </span>
                <span className="text-[10px] font-semibold text-slate-400">
                  WHO Threshold: 12.0 g/dL
                </span>
              </div>

              <div className="w-full h-44 pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94A3B8' }} />
                    <YAxis domain={[5, 18]} tick={{ fontSize: 10, fill: '#94A3B8' }} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const p = payload[0].payload;
                          return (
                            <div className="bg-slate-900 text-white p-2 rounded-xl text-[10px] shadow-lg">
                              <p className="font-bold">{p.date}</p>
                              <p className="text-brand-secondary font-black">
                                {p.hb} g/dL ({p.method})
                              </p>
                              <p className="text-slate-300">{p.category}</p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    {/* Normal threshold reference line */}
                    <ReferenceLine y={12.0} stroke="#FF8D86" strokeDasharray="3 3" />
                    <Line
                      type="monotone"
                      dataKey="hb"
                      stroke="#7185D1"
                      strokeWidth={3}
                      dot={{ r: 4, fill: '#7185D1', strokeWidth: 2, stroke: '#FFFFFF' }}
                      activeDot={{ r: 6, fill: '#FF8D86' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Historical Screenings List */}
            <div className="flex-1 space-y-3 pb-2">
              <span className="text-xs font-black text-slate-700 uppercase tracking-wider block px-1">
                Screening List ({screenings.length})
              </span>

              {screenings.map((s) => (
                <div
                  key={s.id}
                  onClick={() => navigate(`/results/${s.id}`)}
                  className="bg-white rounded-2xl p-3.5 shadow-card hover:shadow-md transition-all cursor-pointer border border-slate-100 flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-11 h-11 rounded-2xl flex items-center justify-center font-black text-xs ${
                        s.is_anemic ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'
                      }`}
                    >
                      {s.estimated_hb.toFixed(1)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-800">
                          {s.screening_type === 'nail' ? 'Fingernail' : 'Lower Eyelid'}
                        </span>
                        <span
                          className={`text-[9px] font-extrabold px-2 py-0.5 rounded-full ${
                            s.is_anemic ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'
                          }`}
                        >
                          {s.category}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-1">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {new Date(s.created_at).toLocaleDateString('en-US', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </span>
                        <span>•</span>
                        <span>Confidence: {s.confidence.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        window.open(api.getPdfUrl(s.id!), '_blank');
                      }}
                      title="Download PDF"
                      className="p-2 text-slate-400 hover:text-brand-primary hover:bg-slate-50 rounded-xl transition-all"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                    <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-brand-primary group-hover:translate-x-0.5 transition-all" />
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <BottomNav />
    </div>
  );
};
