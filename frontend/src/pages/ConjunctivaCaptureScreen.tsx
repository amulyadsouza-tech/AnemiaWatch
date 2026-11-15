import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Camera, RefreshCw, Upload, AlertCircle, Loader2, Sparkles } from 'lucide-react';
import { api } from '../services/api';

export const ConjunctivaCaptureScreen: React.FC = () => {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [stream, setStream] = useState<MediaStream | null>(null);
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('user'); // default front camera for selfie eyelid capture
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState<string>('');

  const startCamera = async (mode = facingMode) => {
    setCameraError(null);
    try {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: mode, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err: any) {
      console.warn('Camera error:', err);
      setCameraError('Camera inaccessible or blocked. You can upload a photo from your gallery.');
    }
  };

  useEffect(() => {
    startCamera(facingMode);
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [facingMode]);

  const toggleFacingMode = () => {
    setFacingMode((prev) => (prev === 'user' ? 'environment' : 'user'));
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current || document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (facingMode === 'user') {
      // Mirror front camera
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }
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

  const retakePhoto = () => {
    setCapturedBlob(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    startCamera(facingMode);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setCapturedBlob(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const analyzeImage = async () => {
    if (!capturedBlob) return;
    setProcessing(true);
    setProcessingStep('Detecting eye socket and palpebral conjunctiva...');

    try {
      if (!localStorage.getItem('anemiawatch_token')) {
        try {
          const guestRes = await api.guestLogin();
          localStorage.setItem('anemiawatch_token', guestRes.access_token);
        } catch (e) {
          console.warn('Guest login auto-fallback:', e);
        }
      }

      setTimeout(() => setProcessingStep('Segmenting mucosal zone & filtering sclera...'), 500);
      setTimeout(() => setProcessingStep('Computing Erythema Index: EI = 100 * log10(R/G)...'), 1100);
      setTimeout(() => setProcessingStep('Evaluating Harvard clinical regression model...'), 1700);

      const file = new File([capturedBlob], 'conjunctiva_capture.jpg', { type: 'image/jpeg' });
      const result = await api.screenConjunctiva(file);

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
      {/* Title bar matching InShot_20240621_074931528_frame_21.png */}
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
        <span className="text-base font-bold tracking-wide">Anemia Screening</span>
        <div className="w-9" />
      </div>

      {/* Main Viewport Container */}
      <div className="flex-1 px-4 flex flex-col items-center justify-center relative">
        <div className="w-full aspect-[9/15] max-h-[480px] bg-slate-900 rounded-[32px] overflow-hidden relative shadow-2xl border-2 border-white/20 flex items-center justify-center">
          {!previewUrl ? (
            <>
              {/* Live Camera Stream */}
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={`w-full h-full object-cover ${facingMode === 'user' ? 'scale-x-[-1]' : ''}`}
              />

              {/* Exact Eye Alignment Overlay matching InShot_20240621_074931528_frame_21.png */}
              <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center">
                {/* Big Eye Shape Outer */}
                <div className="w-64 h-40 relative flex items-center justify-center">
                  {/* Stylized eye contour overlay */}
                  <div className="w-full h-full eye-overlay-shape border-4 border-white/70 shadow-lg flex items-center justify-center">
                    {/* Pupil Circle */}
                    <div className="w-20 h-20 rounded-full border-4 border-white/60 bg-white/5 flex items-center justify-center" />
                  </div>

                  {/* Lower Palpebral Conjunctiva Arc Highlight */}
                  <div className="absolute -bottom-1 w-48 h-10 palpebral-guide-arc flex items-end justify-center pb-1">
                    <span className="text-[10px] font-extrabold text-brand-accent bg-black/60 px-2 py-0.5 rounded-full">
                      Pull Lower Eyelid Here
                    </span>
                  </div>
                </div>

                <div className="mt-8 bg-black/50 backdrop-blur-md px-3.5 py-1.5 rounded-full text-[11px] font-medium text-white/90">
                  Gently pull down lower eyelid & look upward
                </div>
              </div>
            </>
          ) : (
            <img
              src={previewUrl}
              alt="Conjunctiva Capture"
              className="w-full h-full object-cover"
            />
          )}

          {cameraError && !previewUrl && (
            <div className="absolute inset-0 bg-slate-900/90 flex flex-col items-center justify-center p-6 text-center">
              <AlertCircle className="w-10 h-10 text-amber-400 mb-2" />
              <p className="text-xs text-white/90 mb-4">{cameraError}</p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="py-2.5 px-4 bg-brand-primary text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-md"
              >
                <Upload className="w-4 h-4" />
                <span>Choose Photo from Gallery</span>
              </button>
            </div>
          )}

          <canvas ref={canvasRef} className="hidden" />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
          />
        </div>
      </div>

      {/* Camera Controls matching InShot_20240621_074931528_frame_21.png */}
      <div className="p-5 pb-6 shrink-0 flex items-center justify-around">
        {!previewUrl ? (
          <>
            {/* Gallery Upload */}
            <button
              onClick={() => fileInputRef.current?.click()}
              title="Upload Photo"
              className="w-12 h-12 rounded-full bg-white/20 hover:bg-white/30 text-white flex items-center justify-center active:scale-95 transition-all shadow-md"
            >
              <Upload className="w-5 h-5" />
            </button>

            {/* Shutter Button (White circle with camera icon) */}
            <button
              onClick={capturePhoto}
              title="Capture Photo"
              className="w-20 h-20 rounded-full bg-white text-brand-primary flex items-center justify-center shadow-2xl active:scale-90 transition-all group"
            >
              <Camera className="w-8 h-8 text-brand-primary group-hover:scale-110 transition-transform" />
            </button>

            {/* Flip Camera Button (Periwinkle circle with rotate-camera icon) */}
            <button
              onClick={toggleFacingMode}
              title="Flip Camera"
              className="w-14 h-14 rounded-full bg-brand-darkPeriwinkle/90 hover:bg-brand-darkPeriwinkle text-white flex items-center justify-center active:scale-95 transition-all shadow-lg border border-white/20"
            >
              <RefreshCw className="w-6 h-6" />
            </button>
          </>
        ) : (
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

      {processing && (
        <div className="absolute inset-0 bg-brand-primary/95 z-50 flex flex-col items-center justify-center p-6 text-center animate-fade-in">
          <div className="w-20 h-20 rounded-3xl bg-white/15 backdrop-blur-md flex items-center justify-center mb-5 border border-white/20">
            <Loader2 className="w-10 h-10 text-white animate-spin" />
          </div>
          <h3 className="text-lg font-extrabold tracking-tight mb-2">Processing Eyelid Image</h3>
          <p className="text-xs text-white/85 font-medium max-w-xs">{processingStep}</p>
        </div>
      )}
    </div>
  );
};
