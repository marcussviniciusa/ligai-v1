import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Phone, MessageSquare, History, LayoutDashboard, Settings, Webhook, Calendar, Users, Book } from 'lucide-react';
import { cn } from '../lib/utils';

interface LayoutProps {
  children: ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Prompts', href: '/prompts', icon: MessageSquare },
  { name: 'Agendamentos', href: '/schedules', icon: Calendar },
  { name: 'Campanhas', href: '/campaigns', icon: Users },
  { name: 'Historico', href: '/history', icon: History },
  { name: 'Webhooks', href: '/webhooks', icon: Webhook },
  { name: 'Configuracoes', href: '/settings', icon: Settings },
  { name: 'Documentacao', href: '/docs', icon: Book },
];

export function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-lg">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center gap-3 px-6 py-4 border-b">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <Phone className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">LigAI</span>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-4 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-blue-50 text-blue-600'
                      : 'text-gray-600 hover:bg-gray-100'
                  )}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <main className="p-8">{children}</main>
      </div>
    </div>
  );
}
