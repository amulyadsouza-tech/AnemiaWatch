import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, Clock, ChevronRight, AlertTriangle, Activity, Heart, BookOpen, Stethoscope, Shield, Salad } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { BottomNav } from '../components/BottomNav';
import type { ArticleItem, ScreeningResult } from '../types';

// Icon map for article categories
const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  'Symptoms & Awareness': <Heart className="w-5 h-5 text-brand-primary" />,
  'Causes & Diagnosis': <Stethoscope className="w-5 h-5 text-brand-primary" />,
  'Nutrition & Prevention': <Salad className="w-5 h-5 text-brand-primary" />,
  'Lab Tests & Monitoring': <Shield className="w-5 h-5 text-brand-primary" />,
};

// Category color accent
const CATEGORY_COLORS: Record<string, string> = {
  'Symptoms & Awareness':  'bg-pink-50 text-pink-600 border-pink-100',
  'Causes & Diagnosis':    'bg-sky-50 text-sky-600 border-sky-100',
  'Nutrition & Prevention':'bg-emerald-50 text-emerald-600 border-emerald-100',
  'Lab Tests & Monitoring':'bg-violet-50 text-violet-600 border-violet-100',
};

export const HomeScreen: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [articles, setArticles] = useState<ArticleItem[]>([]);
  const [recentScreening, setRecentScreening] = useState<ScreeningResult | null>(null);
  const [selectedArticle, setSelectedArticle] = useState<ArticleItem | null>(null);

  const displayName = user?.full_name?.split(' ')[0] || 'User';

  useEffect(() => {
    api.getArticles()
      .then(setArticles)
      .catch(() => {});

    api.getHistory()
      .then((res) => {
        if (res.screenings && res.screenings.length > 0) {
          setRecentScreening(res.screenings[0]);
        }
      })
      .catch(() => {});
  }, []);

  return (
    <div className="flex-1 min-h-0 flex flex-col bg-brand-primary relative overflow-hidden">

      {/* ── Top Header matching reference ── */}
      <div className="px-6 pt-5 pb-5 relative flex items-end justify-between min-h-[135px]">
        <div className="z-10 max-w-[210px] pb-1">
          <p className="text-white/80 text-xs font-semibold tracking-wide mb-0.5">Good day,</p>
          <h1 className="text-2xl font-extrabold text-white tracking-tight leading-snug">
            {displayName}!
          </h1>
          <p className="text-white/75 text-xs font-medium mt-1">
            Say goodbye to Anemia!
          </p>
        </div>

        {/* Clean Character illustration resting on the white card without overlapping icons */}
        <div className="absolute right-3 bottom-0 w-[110px] h-[140px] pointer-events-none select-none z-10">
          <img
            src="/assets/home_character.png"
            alt="AnemiaWatch Character"
            className="w-full h-full object-contain object-bottom"
            onError={(e) => { (e.target as HTMLElement).style.display = 'none'; }}
          />
        </div>
      </div>

      {/* ── Main Content Card (white rounded-top) ── */}
      <div className="flex-1 min-h-0 bg-[#F4F6FC] rounded-t-[32px] px-5 pt-6 pb-4 flex flex-col overflow-y-auto overscroll-contain shadow-2xl">

        {/* Anemia Section */}
        <div className="mb-5">
          <h2 className="text-base font-black text-slate-800 tracking-tight mb-3">Anemia</h2>
          <div className="grid grid-cols-2 gap-3">

            {/* Screening Card */}
            <button
              onClick={() => navigate('/screening-select')}
              className="bg-white hover:bg-brand-secondary/40 active:scale-[0.98] transition-all p-4 rounded-2xl text-left flex flex-col shadow-sm border border-brand-primary/10 group"
            >
              <div className="w-10 h-10 rounded-full bg-brand-primary/10 text-brand-primary flex items-center justify-center mb-3 group-hover:bg-brand-primary/20 transition-colors">
                <CheckCircle className="w-5 h-5" />
              </div>
              <h3 className="font-extrabold text-sm text-slate-800 leading-tight">Screening</h3>
              <p className="text-[11px] text-slate-400 mt-1 leading-snug">AI-Assisted Detection</p>
            </button>

            {/* History Card */}
            <button
              onClick={() => navigate('/history')}
              className="bg-white hover:bg-brand-secondary/40 active:scale-[0.98] transition-all p-4 rounded-2xl text-left flex flex-col shadow-sm border border-brand-primary/10 group"
            >
              <div className="w-10 h-10 rounded-full bg-brand-primary/10 text-brand-primary flex items-center justify-center mb-3 group-hover:bg-brand-primary/20 transition-colors">
                <Clock className="w-5 h-5" />
              </div>
              <h3 className="font-extrabold text-sm text-slate-800 leading-tight">History</h3>
              <p className="text-[11px] text-slate-400 mt-1 leading-snug">View screening records</p>
            </button>
          </div>
        </div>

        {/* Recent Screening Banner */}
        {recentScreening && (
          <div
            onClick={() => navigate(`/results/${recentScreening.id}`)}
            className="mb-5 bg-white rounded-2xl px-4 py-3 shadow-sm border border-slate-100 flex items-center justify-between gap-3 cursor-pointer hover:shadow-md transition-all group"
          >
            <div className="flex items-center gap-3 min-w-0">
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
                recentScreening.is_anemic ? 'bg-red-50 text-red-500' : 'bg-emerald-50 text-emerald-600'
              }`}>
                <Activity className="w-4.5 h-4.5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-bold text-slate-700">Recent Screening:</span>
                  <span className={`text-[11px] font-extrabold px-2 py-0.5 rounded-full whitespace-nowrap ${
                    recentScreening.is_anemic
                      ? 'bg-red-100 text-red-700'
                      : 'bg-emerald-100 text-emerald-700'
                  }`}>
                    {recentScreening.estimated_hb} g/dL · {recentScreening.category}
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 mt-0.5">
                  {recentScreening.screening_type === 'nail' ? 'Fingernail' : 'Lower Eyelid'}{' '}
                  · {new Date(recentScreening.created_at).toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' })}
                </p>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/results/${recentScreening.id}`);
              }}
              className="p-1.5 text-slate-400 group-hover:text-brand-primary shrink-0 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Health Articles Section */}
        <div className="flex-1 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-black text-slate-800 tracking-tight">Health Articles</h2>
            <button
              onClick={() => { if (articles.length > 0) setSelectedArticle(articles[0]); }}
              className="text-xs font-bold text-brand-primary hover:underline"
            >
              View All
            </button>
          </div>

          {/* Article Cards */}
          <div className="space-y-3 pb-3">
            {articles.map((art, idx) => {
              const icon = CATEGORY_ICONS[art.category] || <BookOpen className="w-5 h-5 text-brand-primary" />;
              return (
                <div
                  key={art.id || idx}
                  onClick={() => setSelectedArticle(art)}
                  className="bg-white rounded-2xl shadow-sm border border-slate-100 flex items-center gap-3.5 px-3.5 py-3.5 cursor-pointer hover:shadow-md hover:border-brand-primary/25 active:scale-[0.99] transition-all group"
                >
                  {/* Category icon rounded container matching reference */}
                  <div className="w-12 h-12 rounded-2xl bg-[#E8EDFB] flex items-center justify-center shrink-0 text-brand-primary group-hover:bg-brand-primary/20 transition-colors">
                    {icon}
                  </div>

                  {/* Text block matching reference layout */}
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-bold text-brand-primary uppercase tracking-wider mb-0.5">
                      {art.category}
                    </p>
                    <h4 className="text-xs font-extrabold text-slate-800 leading-snug line-clamp-2 group-hover:text-brand-primary transition-colors">
                      {art.title}
                    </h4>
                    <span className="text-[10px] text-slate-400 font-medium mt-1 block">
                      Read time: {art.read_time}
                    </span>
                  </div>

                  <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-brand-primary shrink-0 transition-colors" />
                </div>
              );
            })}

            {articles.length === 0 && (
              <div className="text-center py-8 text-slate-400 text-xs">Loading articles...</div>
            )}
          </div>
        </div>
      </div>

      {/* Article Detail Modal */}
      {selectedArticle && (
        <div
          className="absolute inset-0 bg-black/50 z-50 flex items-end justify-center backdrop-blur-sm"
          onClick={() => setSelectedArticle(null)}
        >
          <div
            className="bg-white rounded-t-[28px] w-full max-h-[82vh] overflow-y-auto shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal handle */}
            <div className="flex justify-center pt-3 pb-1">
              <div className="w-10 h-1 bg-slate-200 rounded-full" />
            </div>

            <div className="px-6 pb-8 pt-3">
              <div className="flex items-center justify-between mb-4">
                <span className={`text-[9px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full border ${
                  CATEGORY_COLORS[selectedArticle.category] || 'bg-brand-secondary/60 text-brand-primary border-brand-primary/10'
                }`}>
                  {selectedArticle.category}
                </span>
                <button
                  onClick={() => setSelectedArticle(null)}
                  className="text-slate-400 hover:text-slate-700 text-xs font-semibold bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-full transition-colors"
                >
                  Close
                </button>
              </div>

              <h3 className="text-base font-extrabold text-slate-800 mb-3 leading-snug">
                {selectedArticle.title}
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed mb-5">
                {selectedArticle.content}
              </p>

              <div className="bg-amber-50 p-3 rounded-xl border border-amber-100 text-[11px] text-amber-700 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                <span>Educational resource only. Always consult a qualified healthcare professional for medical advice.</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Bottom Navigation */}
      <BottomNav />
    </div>
  );
};
