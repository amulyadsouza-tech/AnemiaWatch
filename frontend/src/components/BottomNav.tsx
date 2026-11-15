import React from 'react';
import { Home, Clock, User as UserIcon, Camera } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

export const BottomNav: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleNav = (path: string) => {
    if (location.pathname === path) {
      const scrollable = document.querySelector('.overflow-y-auto');
      if (scrollable) {
        scrollable.scrollTo({ top: 0, behavior: 'smooth' });
      }
    } else {
      navigate(path);
    }
  };

  const navItems = [
    { label: 'Home', path: '/home', icon: Home },
    { label: 'Screening', path: '/screening-select', icon: Camera, highlight: true },
    { label: 'History', path: '/history', icon: Clock },
    { label: 'Profile', path: '/profile', icon: UserIcon },
  ];

  return (
    <div className="w-full bg-white border-t border-slate-100/80 py-2.5 px-4 flex items-center justify-around shrink-0 shadow-lg relative z-30 select-none">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = location.pathname === item.path;

        if (item.highlight) {
          return (
            <button
              key={item.path}
              onClick={() => handleNav(item.path)}
              className="flex flex-col items-center -mt-5 focus:outline-none group cursor-pointer"
            >
              <div className="w-12 h-12 rounded-full bg-brand-primary text-white flex items-center justify-center shadow-md group-hover:bg-brand-darkPeriwinkle group-active:scale-95 transition-all">
                <Icon className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-semibold text-brand-primary mt-1">{item.label}</span>
            </button>
          );
        }

        return (
          <button
            key={item.path}
            onClick={() => handleNav(item.path)}
            className={`flex flex-col items-center py-1 px-3 rounded-lg transition-colors focus:outline-none cursor-pointer ${
              isActive ? 'text-brand-primary font-bold' : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <Icon className="w-5 h-5" />
            <span className="text-[10px] mt-0.5">{item.label}</span>
          </button>
        );
      })}
    </div>
  );
};
