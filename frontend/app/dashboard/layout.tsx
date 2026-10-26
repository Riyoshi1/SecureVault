"use client"

import { useAuth } from '../lib/auth';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, token, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !token) {
      router.push('/login');
    }
  }, [token, isLoading, router]);

  if (isLoading || !token) {
    return <div className="min-h-screen bg-background flex items-center justify-center">Loading...</div>;
  }

  const navItems = [
    { name: 'My Files', path: '/dashboard', icon: '📁' },
    { name: 'Upload', path: '/dashboard/upload', icon: '⬆️' },
    { name: 'Personal Profile', path: '/dashboard/profile', icon: '👤' },
    { name: 'Benchmark', path: '/dashboard/benchmark', icon: '⚡' },
  ];

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex flex-col w-64 bg-dark-800 border-r border-slate-700">
        <div className="p-4 border-b border-slate-700">
          <h2 className="text-xl font-bold flex items-center gap-2">🛡️ SecureVault</h2>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => (
            <Link 
              key={item.path} 
              href={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                pathname === item.path 
                  ? 'bg-primary-600/20 text-primary-400 border border-primary-500/30' 
                  : 'text-slate-400 hover:bg-dark-900 hover:text-foreground'
              }`}
            >
              <span>{item.icon}</span>
              {item.name}
            </Link>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-16 flex items-center justify-between px-6 bg-dark-800 border-b border-slate-700">
          <div className="flex items-center md:hidden">
            {/* Mobile menu button could go here */}
            <span className="font-bold">🛡️ SecureVault</span>
          </div>
          
          <div className="flex items-center gap-4 ml-auto">
            <span className="text-sm text-slate-400">
              Welcome, <strong className="text-foreground">{user?.username}</strong>
            </span>
            <button 
              onClick={logout}
              className="px-3 py-1.5 text-sm rounded-md bg-dark-900 border border-slate-700 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30 transition-colors"
            >
              Logout
            </button>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-6xl mx-auto">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
