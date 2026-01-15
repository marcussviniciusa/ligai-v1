import { useState } from 'react';
import { Calendar, Plus, Trash2, Clock, Phone, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import {
  useScheduledCalls,
  useCreateScheduledCall,
  useCancelScheduledCall,
} from '../api/schedules';
import type { ScheduledCall } from '../api/schedules';
import { usePrompts } from '../api/prompts';

function formatDateTime(isoString: string): string {
  return new Date(isoString).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function ScheduleModal({ onClose }: { onClose: () => void }) {
  const { data: prompts } = usePrompts();
  const createSchedule = useCreateScheduledCall();

  const [phoneNumber, setPhoneNumber] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');
  const [promptId, setPromptId] = useState<number | undefined>();
  const [notes, setNotes] = useState('');

  // Get min datetime (now + 1 minute)
  const now = new Date();
  now.setMinutes(now.getMinutes() + 1);
  const minDateTime = now.toISOString().slice(0, 16);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    await createSchedule.mutateAsync({
      phone_number: phoneNumber,
      scheduled_time: new Date(scheduledTime).toISOString(),
      prompt_id: promptId,
      notes: notes || undefined,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Agendar Chamada</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Numero de Telefone
            </label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="11999887766"
              minLength={10}
              maxLength={15}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Data e Hora
            </label>
            <input
              type="datetime-local"
              value={scheduledTime}
              onChange={(e) => setScheduledTime(e.target.value)}
              min={minDateTime}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Prompt (opcional)
            </label>
            <select
              value={promptId || ''}
              onChange={(e) => setPromptId(e.target.value ? Number(e.target.value) : undefined)}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Usar prompt ativo</option>
              {prompts?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} {p.is_active && '(ativo)'}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Observacoes (opcional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              rows={2}
              placeholder="Anotacoes sobre esta chamada..."
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={createSchedule.isPending}
              className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Agendar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; icon: typeof Clock }> = {
    pending: { bg: 'bg-yellow-100', text: 'text-yellow-700', icon: Clock },
    executing: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Loader2 },
    completed: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle },
    cancelled: { bg: 'bg-gray-100', text: 'text-gray-700', icon: XCircle },
    failed: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
  };

  const { bg, text, icon: Icon } = config[status] || config.pending;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${bg} ${text}`}>
      <Icon className={`w-3 h-3 ${status === 'executing' ? 'animate-spin' : ''}`} />
      {status}
    </span>
  );
}

function ScheduleCard({ schedule }: { schedule: ScheduledCall }) {
  const cancelSchedule = useCancelScheduledCall();

  const handleCancel = async () => {
    if (confirm('Tem certeza que deseja cancelar este agendamento?')) {
      await cancelSchedule.mutateAsync(schedule.id);
    }
  };

  const isPast = new Date(schedule.scheduled_time) < new Date();
  const canCancel = schedule.status === 'pending';

  return (
    <div className="bg-white rounded-xl shadow-sm border p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <Phone className="w-5 h-5 text-gray-400" />
            <span className="text-lg font-medium text-gray-900">{schedule.phone_number}</span>
            <StatusBadge status={schedule.status} />
          </div>

          <div className="mt-2 flex items-center gap-2 text-sm text-gray-500">
            <Calendar className="w-4 h-4" />
            <span className={isPast && schedule.status === 'pending' ? 'text-red-600' : ''}>
              {formatDateTime(schedule.scheduled_time)}
            </span>
          </div>

          {schedule.notes && (
            <p className="mt-2 text-sm text-gray-600">{schedule.notes}</p>
          )}

          {schedule.call_id && (
            <p className="mt-2 text-xs text-gray-400">Call ID: {schedule.call_id}</p>
          )}
        </div>

        {canCancel && (
          <button
            onClick={handleCancel}
            disabled={cancelSchedule.isPending}
            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
            title="Cancelar agendamento"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
}

export function SchedulesPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const { data: schedules, isLoading } = useScheduledCalls(statusFilter);
  const [isCreating, setIsCreating] = useState(false);

  const statusOptions = [
    { value: '', label: 'Todos' },
    { value: 'pending', label: 'Pendentes' },
    { value: 'completed', label: 'Concluidos' },
    { value: 'cancelled', label: 'Cancelados' },
    { value: 'failed', label: 'Falhou' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agendamentos</h1>
          <p className="text-gray-500 mt-1">Agende chamadas para horarios especificos</p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-5 h-5" />
          Agendar Chamada
        </button>
      </div>

      <div className="flex gap-2">
        {statusOptions.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setStatusFilter(opt.value || undefined)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              (statusFilter || '') === opt.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-xl shadow-sm border p-6 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-1/3 mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            </div>
          ))}
        </div>
      ) : schedules?.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
          <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhum agendamento</h3>
          <p className="text-gray-500 mb-4">
            Agende chamadas para serem realizadas automaticamente
          </p>
          <button
            onClick={() => setIsCreating(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-5 h-5" />
            Agendar Chamada
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {schedules?.map((schedule) => (
            <ScheduleCard key={schedule.id} schedule={schedule} />
          ))}
        </div>
      )}

      {isCreating && <ScheduleModal onClose={() => setIsCreating(false)} />}
    </div>
  );
}
