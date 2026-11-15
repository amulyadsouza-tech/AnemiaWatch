import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Hand, Eye, Info } from 'lucide-react';
import { BottomNav } from '../components/BottomNav';

export const ScreeningSelectionScreen: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex-1 flex flex-col justify-between bg-brand-primary text-brand-text relative">
      {/* Top Header */}
      <div className="px-5 pt-3 pb-5 flex items-center justify-between text-white shrink-0">
        <button
          onClick={() => navigate('/home')}
          className="p-2 bg-white/15 rounded-full hover:bg-white/25 active:scale-95 transition-all"
        >
          <ArrowLeft className="w-5 h-5 text-white" />
        </button>
        <h1 className="text-base font-bold tracking-wide">Select Screening Method</h1>
        <div className="w-9" />
      </div>

      {/* Main Body Card */}
      <div className="flex-1 min-h-0 bg-[#F4F6FC] rounded-t-[36px] px-5 pt-6 pb-4 flex flex-col overflow-y-auto overscroll-contain shadow-2xl justify-between">
        <div>
          <div className="text-center mb-6">
            <span className="text-[11px] font-bold text-brand-primary tracking-widest uppercase bg-brand-secondary px-3 py-1 rounded-full">
              Non-Invasive AI Screening
            </span>
            <h2 className="text-xl font-black text-slate-800 tracking-tight mt-2.5">
              Hemoglobin Assessment
            </h2>
            <p className="text-xs text-slate-500 max-w-xs mx-auto mt-1 font-medium leading-relaxed">
              Select the anatomical region you wish to screen using your smartphone camera.
            </p>
          </div>

          <div className="space-y-4">
            {/* Card 1: Nail Bed Analysis */}
            <div
              onClick={() => navigate('/capture/nail')}
              className="bg-white rounded-3xl p-5 shadow-card hover:shadow-elevated transition-all cursor-pointer border border-slate-100 flex flex-col group relative overflow-hidden"
            >
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-2xl bg-brand-secondary flex items-center justify-center shrink-0 group-hover:bg-brand-primary group-hover:text-white transition-colors text-brand-primary shadow-sm">
                  <Hand className="w-7 h-7" />
                </div>
                <div className="flex-1">
                  <span className="text-[10px] font-extrabold text-brand-accent tracking-wider uppercase block">
                    Method A
                  </span>
                  <h3 className="text-base font-extrabold text-slate-800 leading-tight group-hover:text-brand-primary transition-colors">
                    Nail Bed Analysis
                  </h3>
                  <p className="text-xs text-slate-500 mt-1.5 leading-relaxed font-normal">
                    Capture your fingernails to analyse nail-bed colour and related visual features.
                  </p>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px]">
                <span className="text-slate-400 font-medium">42-Feature ElasticNet Pipeline</span>
                <span className="font-bold text-brand-primary group-hover:translate-x-1 transition-transform inline-flex items-center gap-1">
                  Start Scan &rarr;
                </span>
              </div>
            </div>

            {/* Card 2: Lower Eyelid Analysis */}
            <div
              onClick={() => navigate('/capture/conjunctiva')}
              className="bg-white rounded-3xl p-5 shadow-card hover:shadow-elevated transition-all cursor-pointer border border-slate-100 flex flex-col group relative overflow-hidden"
            >
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-2xl bg-brand-secondary flex items-center justify-center shrink-0 group-hover:bg-brand-primary group-hover:text-white transition-colors text-brand-primary shadow-sm">
                  <Eye className="w-7 h-7" />
                </div>
                <div className="flex-1">
                  <span className="text-[10px] font-extrabold text-brand-primary tracking-wider uppercase block">
                    Method B (Harvard Clinical Dataset)
                  </span>
                  <h3 className="text-base font-extrabold text-slate-800 leading-tight group-hover:text-brand-primary transition-colors">
                    Lower Eyelid Analysis
                  </h3>
                  <p className="text-xs text-slate-500 mt-1.5 leading-relaxed font-normal">
                    Capture your lower eyelid to analyse the palpebral conjunctiva.
                  </p>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px]">
                <span className="text-slate-400 font-medium">Erythema Index (EI)</span>
                <span className="font-bold text-brand-primary group-hover:translate-x-1 transition-transform inline-flex items-center gap-1">
                  Start Scan &rarr;
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Quality tips note */}
        <div className="bg-brand-secondary/40 p-3.5 rounded-2xl border border-brand-secondary/80 mt-4 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-brand-primary shrink-0 mt-0.5" />
          <p className="text-[11px] text-slate-600 leading-normal">
            Ensure adequate, uniform lighting and avoid direct glare or flash reflections for accurate color extraction.
          </p>
        </div>
      </div>

      <BottomNav />
    </div>
  );
};
