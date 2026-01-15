import { Phone, PhoneOff, Clock, MessageSquare } from 'lucide-react';
import { useActiveCalls, useHangupCall } from '../api/calls';
import { cn } from '../lib/utils';

const stateColors: Record<string, string> = {
  idle: 'bg-green-100 text-green-700',
  processing: 'bg-yellow-100 text-yellow-700',
  speaking: 'bg-blue-100 text-blue-700',
};

const stateLabels: Record<string, string> = {
  idle: 'Aguardando',
  processing: 'Processando',
  speaking: 'Falando',
};

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function ActiveCalls() {
  const { data: calls, isLoading } = useActiveCalls();
  const hangupMutation = useHangupCall();

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/4"></div>
          <div className="h-20 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  const activeCalls = calls || [];

  return (
    <div className="bg-white rounded-xl shadow-sm border">
      <div className="px-6 py-4 border-b">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Chamadas Ativas
          </h2>
          <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
            {activeCalls.length} ativas
          </span>
        </div>
      </div>

      {activeCalls.length === 0 ? (
        <div className="px-6 py-12 text-center text-gray-500">
          <Phone className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p>Nenhuma chamada ativa no momento</p>
        </div>
      ) : (
        <div className="divide-y">
          {activeCalls.map((call) => (
            <div key={call.call_id} className="px-6 py-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                    <Phone className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">
                      {call.called_number || 'Desconhecido'}
                    </p>
                    <p className="text-sm text-gray-500">
                      ID: {call.call_id.slice(0, 12)}...
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {/* State badge */}
                  <span
                    className={cn(
                      'px-2 py-1 rounded-full text-xs font-medium',
                      stateColors[call.state] || 'bg-gray-100 text-gray-700'
                    )}
                  >
                    {stateLabels[call.state] || call.state}
                  </span>

                  {/* Duration */}
                  <div className="flex items-center gap-1 text-gray-500">
                    <Clock className="w-4 h-4" />
                    <span className="text-sm">{formatDuration(call.duration)}</span>
                  </div>

                  {/* Messages */}
                  <div className="flex items-center gap-1 text-gray-500">
                    <MessageSquare className="w-4 h-4" />
                    <span className="text-sm">{call.message_count}</span>
                  </div>

                  {/* Hangup button */}
                  <button
                    onClick={() => hangupMutation.mutate(call.call_id)}
                    disabled={hangupMutation.isPending}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Desligar"
                  >
                    <PhoneOff className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
