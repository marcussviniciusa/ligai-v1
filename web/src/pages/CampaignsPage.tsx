import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Plus, Trash2, Play, Pause, Eye, Loader2 } from 'lucide-react';
import {
  useCampaigns,
  useCreateCampaign,
  useDeleteCampaign,
  useStartCampaign,
  usePauseCampaign,
} from '../api/campaigns';
import type { Campaign } from '../api/campaigns';
import { usePrompts } from '../api/prompts';

function CampaignModal({ onClose }: { onClose: () => void }) {
  const { data: prompts } = usePrompts();
  const createCampaign = useCreateCampaign();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [promptId, setPromptId] = useState<number | undefined>();
  const [maxConcurrent, setMaxConcurrent] = useState(5);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    await createCampaign.mutateAsync({
      name,
      description: description || undefined,
      prompt_id: promptId,
      max_concurrent: maxConcurrent,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Nova Campanha</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nome da Campanha
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Ex: Campanha Janeiro 2025"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Descricao (opcional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              rows={2}
              placeholder="Descricao da campanha..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Prompt
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
              Chamadas Simultaneas (max)
            </label>
            <input
              type="number"
              value={maxConcurrent}
              onChange={(e) => setMaxConcurrent(Number(e.target.value))}
              min={1}
              max={50}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Maximo de chamadas simultaneas para esta campanha
            </p>
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
              disabled={createCampaign.isPending}
              className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Criar Campanha
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    pending: { bg: 'bg-yellow-100', text: 'text-yellow-700' },
    running: { bg: 'bg-blue-100', text: 'text-blue-700' },
    paused: { bg: 'bg-orange-100', text: 'text-orange-700' },
    completed: { bg: 'bg-green-100', text: 'text-green-700' },
  };

  const { bg, text } = config[status] || config.pending;

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${bg} ${text}`}>
      {status}
    </span>
  );
}

function ProgressBar({ completed, failed, total }: { completed: number; failed: number; total: number }) {
  const completedPercent = total > 0 ? (completed / total) * 100 : 0;
  const failedPercent = total > 0 ? (failed / total) * 100 : 0;

  return (
    <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
      <div className="h-full flex">
        <div
          className="bg-green-500 h-full"
          style={{ width: `${completedPercent}%` }}
        />
        <div
          className="bg-red-500 h-full"
          style={{ width: `${failedPercent}%` }}
        />
      </div>
    </div>
  );
}

function CampaignCard({ campaign }: { campaign: Campaign }) {
  const navigate = useNavigate();
  const deleteCampaign = useDeleteCampaign();
  const startCampaign = useStartCampaign();
  const pauseCampaign = usePauseCampaign();

  const handleDelete = async () => {
    if (confirm('Tem certeza que deseja excluir esta campanha?')) {
      await deleteCampaign.mutateAsync(campaign.id);
    }
  };

  const canStart = campaign.status === 'pending' || campaign.status === 'paused';
  const canPause = campaign.status === 'running';
  const canDelete = campaign.status === 'pending' || campaign.status === 'completed';

  const progress = campaign.total_contacts > 0
    ? Math.round(((campaign.completed_contacts + campaign.failed_contacts) / campaign.total_contacts) * 100)
    : 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-medium text-gray-900">{campaign.name}</h3>
            <StatusBadge status={campaign.status} />
          </div>

          {campaign.description && (
            <p className="mt-1 text-sm text-gray-500">{campaign.description}</p>
          )}

          <div className="mt-3">
            <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
              <span>
                {campaign.completed_contacts + campaign.failed_contacts} / {campaign.total_contacts} contatos
              </span>
              <span>{progress}%</span>
            </div>
            <ProgressBar
              completed={campaign.completed_contacts}
              failed={campaign.failed_contacts}
              total={campaign.total_contacts}
            />
          </div>

          <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
            <span>{campaign.completed_contacts} completados</span>
            <span>{campaign.failed_contacts} falhou</span>
            <span>Max {campaign.max_concurrent} simultaneas</span>
          </div>
        </div>

        <div className="flex items-center gap-1 ml-4">
          <button
            onClick={() => navigate(`/campaigns/${campaign.id}`)}
            className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
            title="Ver detalhes"
          >
            <Eye className="w-5 h-5" />
          </button>

          {canStart && (
            <button
              onClick={() => startCampaign.mutate(campaign.id)}
              disabled={startCampaign.isPending || campaign.total_contacts === 0}
              className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg disabled:opacity-50"
              title={campaign.total_contacts === 0 ? 'Adicione contatos primeiro' : 'Iniciar'}
            >
              {startCampaign.isPending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Play className="w-5 h-5" />
              )}
            </button>
          )}

          {canPause && (
            <button
              onClick={() => pauseCampaign.mutate(campaign.id)}
              disabled={pauseCampaign.isPending}
              className="p-2 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded-lg"
              title="Pausar"
            >
              {pauseCampaign.isPending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Pause className="w-5 h-5" />
              )}
            </button>
          )}

          {canDelete && (
            <button
              onClick={handleDelete}
              disabled={deleteCampaign.isPending}
              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
              title="Excluir"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function CampaignsPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const { data: campaigns, isLoading } = useCampaigns(statusFilter);
  const [isCreating, setIsCreating] = useState(false);

  const statusOptions = [
    { value: '', label: 'Todas' },
    { value: 'pending', label: 'Pendentes' },
    { value: 'running', label: 'Em execucao' },
    { value: 'paused', label: 'Pausadas' },
    { value: 'completed', label: 'Concluidas' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campanhas</h1>
          <p className="text-gray-500 mt-1">Gerencie campanhas de discagem em lote</p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-5 h-5" />
          Nova Campanha
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
              <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
              <div className="h-2 bg-gray-200 rounded w-full"></div>
            </div>
          ))}
        </div>
      ) : campaigns?.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
          <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhuma campanha</h3>
          <p className="text-gray-500 mb-4">
            Crie campanhas para realizar chamadas em lote
          </p>
          <button
            onClick={() => setIsCreating(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-5 h-5" />
            Nova Campanha
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {campaigns?.map((campaign) => (
            <CampaignCard key={campaign.id} campaign={campaign} />
          ))}
        </div>
      )}

      {isCreating && <CampaignModal onClose={() => setIsCreating(false)} />}
    </div>
  );
}
