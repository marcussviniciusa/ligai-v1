import { useState } from 'react';
import { Webhook, Plus, Trash2, Edit2, Play, CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import {
  useWebhooks,
  useWebhookEvents,
  useCreateWebhook,
  useUpdateWebhook,
  useDeleteWebhook,
  useTestWebhook,
  useWebhookLogs,
} from '../api/webhooks';
import type { WebhookConfig } from '../api/webhooks';

function WebhookModal({
  webhook,
  onClose,
}: {
  webhook?: WebhookConfig;
  onClose: () => void;
}) {
  const { data: eventsData } = useWebhookEvents();
  const createWebhook = useCreateWebhook();
  const updateWebhook = useUpdateWebhook();

  const [url, setUrl] = useState(webhook?.url || '');
  const [events, setEvents] = useState<string[]>(webhook?.events || []);
  const [secret, setSecret] = useState('');
  const [isActive, setIsActive] = useState(webhook?.is_active ?? true);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (webhook) {
      await updateWebhook.mutateAsync({
        id: webhook.id,
        data: { url, events, is_active: isActive, secret: secret || undefined },
      });
    } else {
      await createWebhook.mutateAsync({ url, events, secret: secret || undefined });
    }
    onClose();
  };

  const toggleEvent = (event: string) => {
    if (events.includes(event)) {
      setEvents(events.filter((e) => e !== event));
    } else {
      setEvents([...events, event]);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          {webhook ? 'Editar Webhook' : 'Novo Webhook'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              URL de Destino
            </label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="https://seu-servidor.com/webhook"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Eventos
            </label>
            <div className="space-y-2">
              {eventsData?.events.map((event) => (
                <label key={event} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={events.includes(event)}
                    onChange={() => toggleEvent(event)}
                    className="rounded text-blue-600"
                  />
                  <span className="text-sm text-gray-700">{event}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Secret (HMAC - opcional)
            </label>
            <input
              type="text"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="Deixe vazio para manter o atual"
            />
            <p className="text-xs text-gray-500 mt-1">
              Usado para assinar as requisicoes (header X-Webhook-Signature)
            </p>
          </div>

          {webhook && (
            <div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="rounded text-blue-600"
                />
                <span className="text-sm text-gray-700">Webhook ativo</span>
              </label>
            </div>
          )}

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
              disabled={createWebhook.isPending || updateWebhook.isPending || events.length === 0}
              className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {webhook ? 'Salvar' : 'Criar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function WebhookLogsPanel({ webhookId }: { webhookId: number }) {
  const { data: logs, isLoading } = useWebhookLogs(webhookId);

  if (isLoading) {
    return <div className="p-4 text-gray-500">Carregando logs...</div>;
  }

  if (!logs?.length) {
    return <div className="p-4 text-gray-500">Nenhum log encontrado</div>;
  }

  return (
    <div className="border-t bg-gray-50">
      <div className="p-3 text-sm font-medium text-gray-700">Ultimos Envios</div>
      <div className="max-h-48 overflow-y-auto divide-y">
        {logs.slice(0, 10).map((log) => (
          <div key={log.id} className="p-3 flex items-center gap-3">
            {log.success ? (
              <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
            ) : (
              <XCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900">{log.event_type}</div>
              <div className="text-xs text-gray-500">
                {log.status_code ? `HTTP ${log.status_code}` : log.error_message}
                {log.attempt > 1 && ` (tentativa ${log.attempt})`}
              </div>
            </div>
            <div className="text-xs text-gray-400">
              {new Date(log.created_at).toLocaleString('pt-BR')}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function WebhookCard({ webhook }: { webhook: WebhookConfig }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const deleteWebhook = useDeleteWebhook();
  const testWebhook = useTestWebhook();
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleTest = async () => {
    setTestResult(null);
    const result = await testWebhook.mutateAsync(webhook.id);
    setTestResult(result);
    setTimeout(() => setTestResult(null), 5000);
  };

  const handleDelete = async () => {
    if (confirm('Tem certeza que deseja excluir este webhook?')) {
      await deleteWebhook.mutateAsync(webhook.id);
    }
  };

  return (
    <>
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    webhook.is_active ? 'bg-green-500' : 'bg-gray-400'
                  }`}
                />
                <span className="text-sm font-medium text-gray-900 truncate">
                  {webhook.url}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {webhook.events.map((event) => (
                  <span
                    key={event}
                    className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded"
                  >
                    {event}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-1 ml-4">
              <button
                onClick={handleTest}
                disabled={testWebhook.isPending}
                className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                title="Testar webhook"
              >
                <Play className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsEditing(true)}
                className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                title="Editar"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteWebhook.isPending}
                className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                title="Excluir"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {testResult && (
            <div
              className={`mt-3 p-2 rounded text-sm ${
                testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}
            >
              {testResult.message}
            </div>
          )}

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-3 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            {isExpanded ? 'Ocultar logs' : 'Ver logs'}
          </button>
        </div>

        {isExpanded && <WebhookLogsPanel webhookId={webhook.id} />}
      </div>

      {isEditing && <WebhookModal webhook={webhook} onClose={() => setIsEditing(false)} />}
    </>
  );
}

export function WebhooksPage() {
  const { data: webhooks, isLoading } = useWebhooks();
  const [isCreating, setIsCreating] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Webhooks</h1>
          <p className="text-gray-500 mt-1">
            Configure endpoints para receber eventos de chamadas
          </p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-5 h-5" />
          Novo Webhook
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="bg-white rounded-xl shadow-sm border p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-1/3"></div>
            </div>
          ))}
        </div>
      ) : webhooks?.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
          <Webhook className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhum webhook configurado</h3>
          <p className="text-gray-500 mb-4">
            Configure webhooks para receber notificacoes quando chamadas acontecerem
          </p>
          <button
            onClick={() => setIsCreating(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-5 h-5" />
            Criar Webhook
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {webhooks?.map((webhook) => (
            <WebhookCard key={webhook.id} webhook={webhook} />
          ))}
        </div>
      )}

      {isCreating && <WebhookModal onClose={() => setIsCreating(false)} />}
    </div>
  );
}
