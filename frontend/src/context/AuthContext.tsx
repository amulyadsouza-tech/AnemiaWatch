import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (token: string, user: User, refreshToken?: string) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('anemiawatch_token'));
  const [loading, setLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const data = await api.getMe();
      setUser(data);
    } catch {
      // Try refresh token if available
      const storedRefresh = localStorage.getItem('anemiawatch_refresh_token');
      if (storedRefresh) {
        try {
          const res = await api.refreshToken(storedRefresh);
          if (res.access_token) {
            localStorage.setItem('anemiawatch_token', res.access_token);
            if (res.refresh_token) {
              localStorage.setItem('anemiawatch_refresh_token', res.refresh_token);
            }
            setToken(res.access_token);
            if (res.user) {
              setUser(res.user);
              setLoading(false);
              return;
            }
          }
        } catch {
          // Refresh failed
        }
      }
      logout();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, [token]);

  const login = (newToken: string, newUser: User, refreshToken?: string) => {
    localStorage.setItem('anemiawatch_token', newToken);
    if (refreshToken) {
      localStorage.setItem('anemiawatch_refresh_token', refreshToken);
    }
    setToken(newToken);
    setUser(newUser);
  };

  const logout = () => {
    const storedRefresh = localStorage.getItem('anemiawatch_refresh_token');
    api.logoutBackend(storedRefresh || undefined);
    localStorage.removeItem('anemiawatch_token');
    localStorage.removeItem('anemiawatch_refresh_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
