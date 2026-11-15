import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { MobileFrame } from './components/MobileFrame';

import { SplashScreen } from './pages/SplashScreen';
import { OnboardingScreen } from './pages/OnboardingScreen';
import { LoginScreen } from './pages/LoginScreen';
import { RegisterScreen } from './pages/RegisterScreen';
import { HomeScreen } from './pages/HomeScreen';
import { ScreeningSelectionScreen } from './pages/ScreeningSelectionScreen';
import { NailBedCaptureScreen } from './pages/NailBedCaptureScreen';
import { ConjunctivaCaptureScreen } from './pages/ConjunctivaCaptureScreen';
import { ResultsScreen } from './pages/ResultsScreen';
import { HistoryScreen } from './pages/HistoryScreen';
import { ProfileScreen } from './pages/ProfileScreen';
import { DoctorDashboardScreen } from './pages/DoctorDashboardScreen';

// Protected Route wrapper
const ProtectedRoute: React.FC<{ children: React.ReactNode; doctorOnly?: boolean }> = ({
  children,
  doctorOnly = false,
}) => {
  const { user, loading } = useAuth();
  const isGuest = localStorage.getItem('anemiawatch_guest') === 'true';

  if (loading) {
    return (
      <div className="flex-1 bg-brand-primary flex items-center justify-center text-white text-xs">
        Loading session...
      </div>
    );
  }

  if (doctorOnly && user?.role !== 'doctor') {
    return <Navigate to="/login" replace />;
  }

  if (!user && !isGuest) {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
};

export function App() {
  return (
    <AuthProvider>
      <Router>
        <MobileFrame>
          <Routes>
            <Route path="/" element={<SplashScreen />} />
            <Route path="/onboarding" element={<OnboardingScreen />} />
            <Route path="/login" element={<LoginScreen />} />
            <Route path="/register" element={<RegisterScreen />} />

            {/* Patient routes */}
            <Route
              path="/home"
              element={
                <ProtectedRoute>
                  <HomeScreen />
                </ProtectedRoute>
              }
            />
            <Route
              path="/screening-select"
              element={
                <ProtectedRoute>
                  <ScreeningSelectionScreen />
                </ProtectedRoute>
              }
            />
            <Route
              path="/capture/nail"
              element={
                <ProtectedRoute>
                  <NailBedCaptureScreen />
                </ProtectedRoute>
              }
            />
            <Route
              path="/capture/conjunctiva"
              element={
                <ProtectedRoute>
                  <ConjunctivaCaptureScreen />
                </ProtectedRoute>
              }
            />
            <Route
              path="/results/:id"
              element={
                <ProtectedRoute>
                  <ResultsScreen />
                </ProtectedRoute>
              }
            />
            <Route
              path="/history"
              element={
                <ProtectedRoute>
                  <HistoryScreen />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <ProfileScreen />
                </ProtectedRoute>
              }
            />

            {/* Doctor portal */}
            <Route
              path="/doctor"
              element={
                <ProtectedRoute doctorOnly>
                  <DoctorDashboardScreen />
                </ProtectedRoute>
              }
            />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </MobileFrame>
      </Router>
    </AuthProvider>
  );
}

export default App;
