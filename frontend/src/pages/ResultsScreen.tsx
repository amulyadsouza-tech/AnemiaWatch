import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { ArrowLeft, Download, RefreshCw, Clock, CheckCircle2, AlertTriangle, ShieldAlert, Sparkles, Home } from 'lucide-react';
import { api, getImageUrl } from '../services/api';
import { BottomNav } from '../components/BottomNav';
import type { ScreeningResult } from '../types';

export const ResultsScreen: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const location = useLocation();

  const [data, setData] = useState<ScreeningResult | null>(
    (location.state as any)?.result || null
  );
  const [loading, setLoading] = useState<boolean>(!data);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'processed' | 'original'>('processed');

  useEffect(() => {
    if (!data && id) {
      setLoading(true);
      api.getScreeningDetail(id)
        .then((res) => {
          setData(res);
        })
        .catch((err) => {
          setError(err.message || 'Failed to load screening details');
        })
        .finally(() => setLoading(false));
    }
  }, [id, data]);

  if (loading) {
    return (
      <div className="flex-1 bg-brand-primary flex flex-col items-center justify-center p-6 text-white">
        <div className="w-12 h-12 rounded-full border-4 border-white/30 border-t-white animate-spin mb-4" />
        <p className="text-xs font-semibold">Loading Screening Results...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex-1 bg-brand-background flex flex-col items-center justify-center p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mb-3" />
        <h2 className="text-base font-bold text-slate-800 mb-1">Record Not Found</h2>
        <p className="text-xs text-slate-500 mb-4">{error || 'Screening record is not available.'}</p>
        <button
          onClick={() => navigate('/home')}
          className="px-5 py-2.5 bg-brand-primary text-white rounded-xl text-xs font-bold"
        >
          Back to Home
        </button>
      </div>
    );
  }

  const isAnemic = data.is_anemic || data.classification?.is_anemic;
  const hbVal = data.estimated_hb;
  const category = data.category || data.classification?.category || 'Normal';
  const confidence = data.confidence || data.confidence_percentage || 95.0;
  const targetRange = data.normal_range_text || data.classification?.normal_range_text || '12.0 - 16.0 g/dL';

  const downloadPdf = () => {
    const screeningId = data.id || data.screening_id;
    if (screeningId) {
      window.open(api.getPdfUrl(screeningId), '_blank');
    }
  };

  return (
    <div className="flex-1 min-h-0 bg-brand-primary flex flex-col justify-between text-brand-text relative overflow-hidden">
      {/* Header matching InShot_20240621_075405573_frame_26.png */}
      <div className="px-5 pt-3 pb-3 flex items-center justify-between text-white shrink-0">
        <button
          onClick={() => navigate('/home')}
          className="p-2 bg-white/15 rounded-full hover:bg-white/25 active:scale-95 transition-all"
        >
          <ArrowLeft className="w-5 h-5 text-white" />
        </button>
        <span className="text-base font-bold tracking-wide">Detection Results</span>
        <div className="w-9" />
      </div>

      {/* Main Results Card matching reference */}
      <div className="flex-1 min-h-0 bg-[#F4F6FC] rounded-t-[36px] px-5 pt-5 pb-6 flex flex-col overflow-y-auto overscroll-contain shadow-2xl">
        {/* Detail Deteksi Box */}
        <div className="bg-white rounded-3xl p-5 shadow-card border border-slate-100 mb-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <span className="text-xs font-black text-slate-800 uppercase tracking-wider">
              Detection Details
            </span>
            <span className="text-[10px] text-slate-400 font-medium">
              {data.screening_type === 'nail' ? 'Hand Nails' : 'Eye Conjunctiva'}
            </span>
          </div>

          {/* Primary Result Banner */}
          <div className="my-4 text-center">
            <div className="text-[11px] text-slate-400 font-semibold mb-1">
              Estimated Hemoglobin Level
            </div>
            <div className="flex items-baseline justify-center gap-1.5">
              <span className="text-4xl font-black text-brand-primary tracking-tight">
                {hbVal.toFixed(1)}
              </span>
              <span className="text-sm font-bold text-slate-500">
                {data.unit || 'g/dL'}
              </span>
            </div>

            {/* Status Pill */}
            <div className="mt-2.5 inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full text-xs font-black shadow-xs">
              <div
                className={`w-2.5 h-2.5 rounded-full ${
                  isAnemic ? 'bg-red-500' : 'bg-emerald-500'
                }`}
              />
              <span className={isAnemic ? 'text-red-600 font-black' : 'text-emerald-700 font-black'}>
                Result: {isAnemic ? 'Anemia Indicated!' : 'Normal Level'} ({category})
              </span>
            </div>

            <div className="mt-2 text-[11px] text-slate-400">
              Reference Range: <span className="font-semibold text-slate-600">{targetRange}</span>
            </div>
          </div>

          {/* Meta metrics */}
          <div className="grid grid-cols-2 gap-2 pt-3 border-t border-slate-100 text-xs">
            <div className="bg-slate-50 p-2.5 rounded-2xl">
              <span className="text-[10px] text-slate-400 block font-medium">Accuracy / Confidence</span>
              <span className="font-extrabold text-slate-800">{confidence.toFixed(2)}%</span>
            </div>
            <div className="bg-slate-50 p-2.5 rounded-2xl">
              <span className="text-[10px] text-slate-400 block font-medium">Image Quality</span>
              <span className="font-extrabold text-slate-800">{data.quality_status || 'Optimal'}</span>
            </div>
          </div>

          <div className="mt-2 text-[10px] text-slate-400 text-right">
            Date: {new Date(data.created_at).toLocaleString('en-US', { dateStyle: 'full', timeStyle: 'medium' })}
          </div>
        </div>

        {/* Visual ROI Inspection with Toggle */}
        <div className="bg-white rounded-3xl p-4 shadow-card border border-slate-100 mb-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-brand-primary" />
              <span>Image Inspection & AI Segmentation</span>
            </span>

            {/* Toggle Switch */}
            <div className="flex bg-slate-100 p-0.5 rounded-xl text-[10px] font-bold">
              <button
                onClick={() => setViewMode('processed')}
                className={`px-2.5 py-1 rounded-lg transition-all ${
                  viewMode === 'processed' ? 'bg-brand-primary text-white shadow-xs' : 'text-slate-500'
                }`}
              >
                Segmentation
              </button>
              <button
                onClick={() => setViewMode('original')}
                className={`px-2.5 py-1 rounded-lg transition-all ${
                  viewMode === 'original' ? 'bg-brand-primary text-white shadow-xs' : 'text-slate-500'
                }`}
              >
                Original
              </button>
            </div>
          </div>

          <div className="w-full aspect-[4/3] bg-slate-100 rounded-2xl overflow-hidden relative border border-slate-200 flex items-center justify-center">
            <img
              src={viewMode === 'processed' ? getImageUrl(data.processed_image_url) : getImageUrl(data.original_image_url)}
              alt="Screening Inspection"
              className="w-full h-full object-contain"
            />
          </div>

          {/* Feature indicators */}
          <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-500 px-1">
            {data.erythema_index ? (
              <span>Erythema Index: <b className="text-slate-800">{data.erythema_index.toFixed(2)}</b></span>
            ) : (
              <span>Detected Nails: <b className="text-slate-800">{data.nail_count || 4} ROI</b></span>
            )}
            <span className="text-brand-primary font-semibold text-[10px]">
              {data.validation_status}
            </span>
          </div>
        </div>

        {/* Clinical Guidance Sections matching InShot_20240621_075405573_frame_26.png */}
        <div className="bg-white rounded-3xl p-5 shadow-card border border-slate-100 space-y-4 mb-4">
          {/* Pencegahan */}
          <div>
            <h4 className="text-xs font-black text-slate-800 uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Prevention</span>
            </h4>
            <p className="text-xs text-slate-600 leading-relaxed font-normal">
              {data.recommendations?.prevention ||
                'Prevent anemia by consuming iron-rich foods such as lean red meat, poultry, beans, spinach, and fortified cereals, paired with vitamin C.'}
            </p>
          </div>

          {/* Resiko */}
          <div>
            <h4 className="text-xs font-black text-slate-800 uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              <span>Risks</span>
            </h4>
            <p className="text-xs text-slate-600 leading-relaxed font-normal">
              {data.recommendations?.risks ||
                'Untreated anemia can cause chronic fatigue, decreased cognitive focus, dizziness, and strain on cardiovascular health.'}
            </p>
          </div>

          {/* Saran */}
          <div>
            <h4 className="text-xs font-black text-slate-800 uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-brand-primary" />
              <span>Clinical Advice</span>
            </h4>
            <p className="text-xs text-slate-600 leading-relaxed font-normal">
              {data.recommendations?.advice ||
                'Please consult a healthcare provider for a standard Complete Blood Count (CBC) test in a laboratory to confirm nutritional status.'}
            </p>
          </div>
        </div>

        {/* Medical Disclaimer Banner */}
        <div className="bg-red-50 border border-red-200 rounded-2xl p-3.5 mb-5 text-[11px] text-red-800 leading-relaxed font-medium flex items-start gap-2.5">
          <ShieldAlert className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <span>
            {data.disclaimer ||
              'This is an AI-assisted screening estimate and not a confirmed medical diagnosis. Please consult a healthcare professional and confirm your hemoglobin level through appropriate laboratory testing.'}
          </span>
        </div>

        {/* Action Buttons */}
        <div className="space-y-2.5">
          <button
            onClick={downloadPdf}
            className="w-full py-3.5 bg-brand-primary text-white rounded-2xl text-xs font-extrabold flex items-center justify-center gap-2 shadow-md hover:bg-brand-darkPeriwinkle active:scale-95 transition-all"
          >
            <Download className="w-4 h-4" />
            <span>Download Clinical Report (PDF)</span>
          </button>

          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => navigate('/home')}
              className="py-3 bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 rounded-2xl text-[11px] font-bold flex items-center justify-center gap-1 transition-all active:scale-95 shadow-xs"
            >
              <Home className="w-3.5 h-3.5 text-brand-primary" />
              <span>Home</span>
            </button>
            <button
              onClick={() => navigate('/history')}
              className="py-3 bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 rounded-2xl text-[11px] font-bold flex items-center justify-center gap-1 transition-all active:scale-95 shadow-xs"
            >
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span>History</span>
            </button>
            <button
              onClick={() => navigate('/screening-select')}
              className="py-3 bg-brand-secondary/80 text-brand-primary border border-brand-primary/20 hover:bg-brand-secondary rounded-2xl text-[11px] font-bold flex items-center justify-center gap-1 transition-all active:scale-95 shadow-xs"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retake</span>
            </button>
          </div>
        </div>
      </div>

      {/* Bottom Navigation */}
      <BottomNav />
    </div>
  );
};
