import { StatsCards } from '../components/StatsCards';
import { ActiveCalls } from '../components/ActiveCalls';
import { Dialer } from '../components/Dialer';
import { useDashboardWebSocket } from '../api/websocket';

export function DashboardPage() {
  // Connect to WebSocket for real-time updates
  useDashboardWebSocket();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Visao geral do sistema de chamadas</p>
      </div>

      {/* Stats */}
      <StatsCards />

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active calls - takes 2 columns */}
        <div className="lg:col-span-2">
          <ActiveCalls />
        </div>

        {/* Dialer */}
        <div>
          <Dialer />
        </div>
      </div>
    </div>
  );
}
