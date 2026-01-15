import { Phone, PhoneCall, Clock, Activity } from 'lucide-react';
import { useStats } from '../api/calls';

function formatDuration(seconds: number): string {
  if (!seconds) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function StatsCards() {
  const { data: stats, isLoading } = useStats();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-xl shadow-sm border p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          </div>
        ))}
      </div>
    );
  }

  const cards = [
    {
      title: 'Chamadas Ativas',
      value: stats?.active_calls || 0,
      max: stats?.max_concurrent_calls,
      icon: PhoneCall,
      color: 'text-green-600',
      bg: 'bg-green-100',
    },
    {
      title: 'Total de Chamadas',
      value: stats?.total_calls || 0,
      icon: Phone,
      color: 'text-blue-600',
      bg: 'bg-blue-100',
    },
    {
      title: 'Chamadas Completadas',
      value: stats?.completed_calls || 0,
      icon: Activity,
      color: 'text-purple-600',
      bg: 'bg-purple-100',
    },
    {
      title: 'Duracao Media',
      value: formatDuration(stats?.avg_duration_seconds || 0),
      icon: Clock,
      color: 'text-orange-600',
      bg: 'bg-orange-100',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
      {cards.map((card) => (
        <div key={card.title} className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">{card.title}</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {card.value}
                {card.max && (
                  <span className="text-sm font-normal text-gray-400">
                    /{card.max}
                  </span>
                )}
              </p>
            </div>
            <div className={`w-12 h-12 ${card.bg} rounded-lg flex items-center justify-center`}>
              <card.icon className={`w-6 h-6 ${card.color}`} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
