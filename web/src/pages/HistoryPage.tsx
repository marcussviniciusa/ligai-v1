import { useState } from 'react';
import { History, Clock, MessageSquare, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { useCalls, useCall, useDeleteCall } from '../api/calls';
import { cn } from '../lib/utils';

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '-';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

const statusColors: Record<string, string> = {
  completed: 'bg-green-100 text-green-700',
  active: 'bg-blue-100 text-blue-700',
  failed: 'bg-red-100 text-red-700',
};

export function HistoryPage() {
  const [page, setPage] = useState(1);
  const [selectedCallId, setSelectedCallId] = useState<number | null>(null);
  const perPage = 15;

  const { data: callsData, isLoading } = useCalls(page, perPage);
  const { data: selectedCall } = useCall(selectedCallId || 0);
  const deleteMutation = useDeleteCall();

  const handleDelete = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Tem certeza que deseja excluir este registro?')) {
      deleteMutation.mutate(id);
      if (selectedCallId === id) {
        setSelectedCallId(null);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded w-1/4 animate-pulse"></div>
        <div className="bg-white rounded-xl shadow-sm border p-6 animate-pulse">
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const calls = callsData?.items || [];
  const totalPages = Math.ceil((callsData?.total || 0) / perPage);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Historico</h1>
        <p className="text-gray-500">Registro de chamadas anteriores</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calls list */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-sm border">
            {calls.length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-500">
                <History className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p>Nenhuma chamada registrada</p>
              </div>
            ) : (
              <>
                <div className="divide-y">
                  {calls.map((call) => (
                    <div
                      key={call.id}
                      onClick={() => setSelectedCallId(call.id)}
                      className={cn(
                        'px-6 py-4 hover:bg-gray-50 cursor-pointer',
                        selectedCallId === call.id && 'bg-blue-50'
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">
                              {call.called_number || 'Desconhecido'}
                            </span>
                            <span
                              className={cn(
                                'px-2 py-0.5 rounded-full text-xs font-medium',
                                statusColors[call.status] || 'bg-gray-100 text-gray-700'
                              )}
                            >
                              {call.status}
                            </span>
                          </div>
                          <div className="flex gap-4 mt-1 text-sm text-gray-500">
                            <span>{formatDate(call.start_time)}</span>
                            <span className="flex items-center gap-1">
                              <Clock className="w-4 h-4" />
                              {formatDuration(call.duration_seconds)}
                            </span>
                          </div>
                        </div>

                        <button
                          onClick={(e) => handleDelete(call.id, e)}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination */}
                <div className="px-6 py-4 border-t flex items-center justify-between">
                  <span className="text-sm text-gray-500">
                    {callsData?.total || 0} chamadas no total
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <span className="text-sm text-gray-600">
                      {page} / {totalPages || 1}
                    </span>
                    <button
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                      className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Call detail */}
        <div>
          <div className="bg-white rounded-xl shadow-sm border">
            {selectedCall ? (
              <>
                <div className="px-6 py-4 border-b">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Detalhes da Chamada
                  </h2>
                </div>
                <div className="p-6 space-y-4">
                  <div>
                    <span className="text-sm text-gray-500">Numero</span>
                    <p className="font-medium">{selectedCall.called_number || 'Desconhecido'}</p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-500">Inicio</span>
                    <p className="font-medium">{formatDate(selectedCall.start_time)}</p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-500">Duracao</span>
                    <p className="font-medium">{formatDuration(selectedCall.duration_seconds)}</p>
                  </div>
                  {selectedCall.summary && (
                    <div>
                      <span className="text-sm text-gray-500">Resumo</span>
                      <p className="text-sm mt-1">{selectedCall.summary}</p>
                    </div>
                  )}

                  {/* Transcript */}
                  {selectedCall.messages && selectedCall.messages.length > 0 && (
                    <div>
                      <span className="text-sm text-gray-500 flex items-center gap-1 mb-2">
                        <MessageSquare className="w-4 h-4" />
                        Transcricao
                      </span>
                      <div className="space-y-2 max-h-80 overflow-y-auto">
                        {selectedCall.messages.map((msg) => (
                          <div
                            key={msg.id}
                            className={cn(
                              'p-3 rounded-lg text-sm',
                              msg.role === 'user'
                                ? 'bg-gray-100 text-gray-800'
                                : 'bg-blue-100 text-blue-800'
                            )}
                          >
                            <p className="font-medium text-xs mb-1">
                              {msg.role === 'user' ? 'Cliente' : 'IA'}
                            </p>
                            <p>{msg.content}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="px-6 py-12 text-center text-gray-500">
                <MessageSquare className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                <p>Selecione uma chamada para ver detalhes</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
