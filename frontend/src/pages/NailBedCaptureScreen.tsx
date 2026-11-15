import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Camera, RefreshCw, Upload, AlertCircle, Check, Loader2, Sparkles } from 'lucide-react';
import { api } from '../services/api';

export const NailBedCaptureScreen: React.FC = () => {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [stream, setStream] = useState<MediaStream | null>(null);
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState<string>('');

  // Start Camera
  const startCamera = async () => {
    setCameraError(null);
    try {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err: any) {
      console.warn('Camera stream error:', err);
      setCameraError('Camera inaccessible or blocked. You can upload a photo from your gallery.');
    }
  };

  useEffect(() => {
    startCamera();
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Take Snapshot
  const capturePhoto = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current || document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (blob) {
          setCapturedBlob(blob);
          setPreviewUrl(URL.createObjectURL(blob));
        }
      },
      'image/jpeg',
      0.95
    );
  };

  // Retake
  const retakePhoto = () => {
    setCapturedBlob(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    startCamera();
  };

  // File Upload Fallback
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setCapturedBlob(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  // Submit for analysis
  const analyzeImage = async () => {
    if (!capturedBlob) return;
    setProcessing(true);
    setProcessingStep('Detecting fingernail contours...');

    try {
      if (!localStorage.getItem('anemiawatch_token')) {
        try {
          const guestRes = await api.guestLogin();
          localStorage.setItem('anemiawatch_token', guestRes.access_token);
        } catch (e) {
          console.warn('Guest login auto-fallback:', e);
        }
      }

      setTimeout(() => setProcessingStep('Filtering specular glare & leukonychia...'), 500);
      setTimeout(() => setProcessingStep('Extracting 42-percentile intensity vector...'), 1100);
      setTimeout(() => setProcessingStep('Estimating hemoglobin with ElasticNet model...'), 1700);

      const file = new File([capturedBlob], 'fingernail_capture.jpg', { type: 'image/jpeg' });
      const result = await api.screenNail(file);

      // Stop camera stream
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }

      navigate(`/results/${result.screening_id}`, { state: { result } });
    } catch (err: any) {
      alert(`Analysis failed: ${err.message || 'Please check backend connection'}`);
      setProcessing(false);
    }
  };

  return (
    <div className="flex-1 bg-brand-primary flex flex-col justify-between text-white relative">
      {/* Header */}
      <div className="px-5 pt-3 pb-3 flex items-center justify-between shrink-0">
        <button
          onClick={() => {
            if (stream) stream.getTracks().forEach((track) => track.stop());
            navigate('/screening-select');
          }}
          className="p-2 bg-white/15 rounded-full hover:bg-white/25 active:scale-95 transition-all"
        >
          <ArrowLeft className="w-5 h-5 text-white" />
        </button>
        <div className="text-center">
          <h1 className="text-sm font-bold tracking-wide">Scan Fingernails</h1>
          <span className="text-[10px] text-white/75 font-medium">Nail Bed Color Analysis</span>
        </div>
        <div className="w-9" />
      </div>

      {/* Main Viewport Container */}
      <div className="flex-1 px-4 flex flex-col items-center justify-center relative">
        <div className="w-full aspect-[3/4] max-h-[460px] bg-slate-900 rounded-[28px] overflow-hidden relative shadow-2xl border-2 border-white/20 flex items-center justify-center">
          {!previewUrl ? (
            <>
              {/* Real Live Video */}
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />

              {/* Hand & 4 Fingernails Alignment Overlay */}
              <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center p-6">
                {/* 4 Nail Target Boxes matching research paper images.jpg */}
                <div className="w-full max-w-[280px] grid grid-cols-4 gap-2 mb-2">
                  {[1, 2, 3, 4].map((n) => (
                    <div
                      key={n}
                      className="aspect-[4/5] rounded-xl border-2 border-dashed border-white/80 bg-white/10 flex flex-col items-center justify-between p-1.5 shadow-sm"
                    >
                      <span className="text-[9px] font-bold text-white bg-brand-primary/80 px-1 rounded">
                        Nail {n}
                      </span>
                      <div className="w-4 h-4 border border-brand-accent/90 rounded-xs" />
                    </div>
                  ))}
                </div>

                {/* Hand outline guide */}
                <div className="w-56 h-36 border border-white/40 rounded-b-3xl bg-white/5 flex items-center justify-center text-center p-3">
                  <span className="text-[11px] text-white/80 font-medium leading-snug">
                    Align your 4 fingers facing the camera inside the alignment box
                  </span>
                </div>
              </div>
            </>
          ) : (
            /* Image Preview */
            <img
              src={previewUrl}
              alt="Fingernail Capture"
              className="w-full h-full object-cover"
            />
          )}

          {/* Camera Error / Fallback Banner */}
          {cameraError && !previewUrl && (
            <div className="absolute inset-0 bg-slate-900/90 flex flex-col items-center justify-center p-6 text-center">
              <AlertCircle className="w-10 h-10 text-amber-400 mb-2" />
              <p className="text-xs text-white/90 mb-4">{cameraError}</p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="py-2.5 px-4 bg-brand-primary text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-md"
              >
                <Upload className="w-4 h-4" />
                <span>Choose Nail Photo from Gallery</span>
              </button>
            </div>
          )}

          {/* Hidden Canvas and File Input */}
          <canvas ref={canvasRef} className="hidden" />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
          />
        </div>

        {/* Quality Checklist Instructions */}
        <div className="w-full max-w-[320px] bg-white/10 backdrop-blur-sm rounded-2xl p-2.5 mt-3 text-[11px] text-white/90 border border-white/10 space-y-1">
          <div className="flex items-center gap-1.5 font-medium">
            <Check className="w-3.5 h-3.5 text-emerald-300" />
            <span>Ensure nails are free of polish and lighting is uniform.</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium">
            <Check className="w-3.5 h-3.5 text-emerald-300" />
            <span>Avoid direct flashlight reflection (glare).</span>
          </div>
        </div>
      </div>

      {/* Control Buttons matching Android standard */}
      <div className="p-5 pb-6 shrink-0 flex items-center justify-around">
        {!previewUrl ? (
          <>
            {/* Gallery Upload Button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              title="Upload Photo"
              className="w-12 h-12 rounded-full bg-white/20 hover:bg-white/30 text-white flex items-center justify-center active:scale-95 transition-all shadow-md"
            >
              <Upload className="w-5 h-5" />
            </button>

            {/* Shutter Button */}
            <button
              onClick={capturePhoto}
              title="Capture Photo"
              className="w-20 h-20 rounded-full bg-white text-brand-primary flex items-center justify-center p-1.5 shadow-2xl active:scale-90 transition-all group"
            >
              <div className="w-full h-full rounded-full border-4 border-brand-primary/40 flex items-center justify-center group-hover:bg-slate-50">
                <Camera className="w-8 h-8 text-brand-primary" />
              </div>
            </button>

            {/* Flip / Reset Camera */}
            <button
              onClick={startCamera}
              title="Reload Camera"
              className="w-12 h-12 rounded-full bg-white/20 hover:bg-white/30 text-white flex items-center justify-center active:scale-95 transition-all shadow-md"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </>
        ) : (
          /* Captured Actions */
          <div className="w-full grid grid-cols-2 gap-3 px-2">
            <button
              onClick={retakePhoto}
              disabled={processing}
              className="py-3.5 px-4 bg-white/20 hover:bg-white/30 text-white rounded-2xl text-xs font-bold flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Retake</span>
            </button>

            <button
              onClick={analyzeImage}
              disabled={processing}
              className="py-3.5 px-4 bg-white text-brand-primary hover:bg-slate-50 rounded-2xl text-xs font-extrabold flex items-center justify-center gap-2 shadow-xl transition-all active:scale-95 disabled:opacity-50"
            >
              {processing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-brand-primary" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-brand-accent" />
                  <span>Analyze Image</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Processing Overlay Dialog */}
      {processing && (
        <div className="absolute inset-0 bg-brand-primary/95 z-50 flex flex-col items-center justify-center p-6 text-center animate-fade-in">
          <div className="w-20 h-20 rounded-3xl bg-white/15 backdrop-blur-md flex items-center justify-center mb-5 border border-white/20">
            <Loader2 className="w-10 h-10 text-white animate-spin" />
          </div>
          <h3 className="text-lg font-extrabold tracking-tight mb-2">Processing Fingernail Image</h3>
          <p className="text-xs text-white/85 font-medium max-w-xs">{processingStep}</p>
        </div>
      )}
    </div>
  );
};
