import { useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Upload,
  Plus,
  Play,
  Pause,
  Users,
  CheckCircle,
  XCircle,
  Phone,
  Loader2,
  Download,
} from 'lucide-react';
import {
  useCampaign,
  useCampaignStats,
  useCampaignContacts,
  useStartCampaign,
  usePauseCampaign,
  useImportContacts,
  useImportContactsCsv,
} from '../api/campaigns';

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; icon?: typeof CheckCircle }> = {
    pending: { bg: 'bg-yellow-100', text: 'text-yellow-700' },
    calling: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Phone },
    completed: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle },
    failed: { bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
  };

  const { bg, text, icon: Icon } = config[status] || config.pending;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${bg} ${text}`}>
      {Icon && <Icon className="w-3 h-3" />}
      {status}
    </span>
  );
}

function ImportModal({
  campaignId,
  onClose,
}: {
  campaignId: number;
  onClose: () => void;
}) {
  const importContacts = useImportContacts();
  const importCsv = useImportContactsCsv();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<'csv' | 'manual'>('csv');
  const [manualInput, setManualInput] = useState('');
  const [result, setResult] = useState<{ success: boolean; imported: number } | null>(null);

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const res = await importCsv.mutateAsync({ id: campaignId, file });
      setResult(res);
    } catch (error) {
      setResult({ success: false, imported: 0 });
    }
  };

  const handleManualImport = async () => {
    const lines = manualInput.split('\n').filter((l) => l.trim());
    const contacts = lines.map((line) => {
      const [phone, name] = line.split(',').map((s) => s.trim());
      return { phone_number: phone, name: name || undefined };
    });

    if (contacts.length === 0) return;

    try {
      const res = await importContacts.mutateAsync({
        id: campaignId,
        data: { contacts },
      });
      setResult(res);
      setManualInput('');
    } catch (error) {
      setResult({ success: false, imported: 0 });
    }
  };

  const downloadTemplate = () => {
    const csv = 'phone_number,name\n5511999887766,Joao Silva\n5511988776655,Maria Santos';
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'template_contatos.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Importar Contatos</h2>

        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setMode('csv')}
            className={`flex-1 py-2 rounded-lg text-sm font-medium ${
              mode === 'csv' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
            }`}
          >
            Upload CSV
          </button>
          <button
            onClick={() => setMode('manual')}
            className={`flex-1 py-2 rounded-lg text-sm font-medium ${
              mode === 'manual' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'
            }`}
          >
            Digitar Numeros
          </button>
        </div>

        {mode === 'csv' ? (
          <div className="space-y-4">
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors"
            >
              <Upload className="w-10 h-10 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-600">
                Clique para selecionar um arquivo CSV
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Colunas esperadas: phone_number, name (opcional)
              </p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleCsvUpload}
              className="hidden"
            />
            <button
              onClick={downloadTemplate}
              className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
            >
              <Download className="w-4 h-4" />
              Baixar template CSV
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Numeros (um por linha)
              </label>
              <textarea
                value={manualInput}
                onChange={(e) => setManualInput(e.target.value)}
                className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                rows={6}
                placeholder="5511999887766, Joao Silva&#10;5511988776655&#10;5511977665544, Maria"
              />
              <p className="text-xs text-gray-500 mt-1">
                Formato: numero, nome (nome opcional)
              </p>
            </div>
            <button
              onClick={handleManualImport}
              disabled={importContacts.isPending || !manualInput.trim()}
              className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              Importar
            </button>
          </div>
        )}

        {result && (
          <div
            className={`mt-4 p-3 rounded-lg ${
              result.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            }`}
          >
            {result.success
              ? `${result.imported} contatos importados com sucesso!`
              : 'Erro ao importar contatos'}
          </div>
        )}

        <div className="flex justify-end gap-3 pt-4 mt-4 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}

function ContactsTable({ campaignId }: { campaignId: number }) {
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [page, setPage] = useState(1);
  const { data: contacts, isLoading } = useCampaignContacts(
    campaignId,
    page,
    50,
    statusFilter
  );

  const statusOptions = [
    { value: '', label: 'Todos' },
    { value: 'pending', label: 'Pendentes' },
    { value: 'calling', label: 'Chamando' },
    { value: 'completed', label: 'Completados' },
    { value: 'failed', label: 'Falhou' },
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border">
      <div className="p-4 border-b flex items-center justify-between">
        <h3 className="font-medium text-gray-900">Contatos</h3>
        <div className="flex gap-1">
          {statusOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() => {
                setStatusFilter(opt.value || undefined);
                setPage(1);
              }}
              className={`px-2 py-1 rounded text-xs font-medium ${
                (statusFilter || '') === opt.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-gray-500">Carregando...</div>
      ) : contacts?.length === 0 ? (
        <div className="p-8 text-center text-gray-500">Nenhum contato encontrado</div>
      ) : (
        <>
          <div className="divide-y max-h-96 overflow-y-auto">
            {contacts?.map((contact) => (
              <div key={contact.id} className="p-3 flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{contact.phone_number}</span>
                    <StatusBadge status={contact.status} />
                  </div>
                  {contact.name && (
                    <p className="text-sm text-gray-500">{contact.name}</p>
                  )}
                </div>
                <div className="text-right text-xs text-gray-400">
                  {contact.attempts > 0 && <div>{contact.attempts} tentativa(s)</div>}
                  {contact.error_message && (
                    <div className="text-red-500">{contact.error_message}</div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="p-3 border-t flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="text-sm text-gray-500">Pagina {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={contacts && contacts.length < 50}
              className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
            >
              Proxima
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const campaignId = Number(id);

  const { data: campaign, isLoading } = useCampaign(campaignId);
  const { data: stats } = useCampaignStats(campaignId);
  const startCampaign = useStartCampaign();
  const pauseCampaign = usePauseCampaign();

  const [showImport, setShowImport] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-gray-400 animate-spin" />
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-medium text-gray-900">Campanha nao encontrada</h2>
        <button
          onClick={() => navigate('/campaigns')}
          className="mt-4 text-blue-600 hover:text-blue-700"
        >
          Voltar para campanhas
        </button>
      </div>
    );
  }

  const canStart = campaign.status === 'pending' || campaign.status === 'paused';
  const canPause = campaign.status === 'running';
  const canAddContacts = campaign.status === 'pending' || campaign.status === 'paused';

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/campaigns')}
          className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{campaign.name}</h1>
          {campaign.description && (
            <p className="text-gray-500 mt-1">{campaign.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {canAddContacts && (
            <button
              onClick={() => setShowImport(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              <Plus className="w-5 h-5" />
              Adicionar Contatos
            </button>
          )}
          {canStart && (
            <button
              onClick={() => startCampaign.mutate(campaignId)}
              disabled={startCampaign.isPending || campaign.total_contacts === 0}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {startCampaign.isPending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Play className="w-5 h-5" />
              )}
              {campaign.status === 'paused' ? 'Retomar' : 'Iniciar'}
            </button>
          )}
          {canPause && (
            <button
              onClick={() => pauseCampaign.mutate(campaignId)}
              disabled={pauseCampaign.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
            >
              {pauseCampaign.isPending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Pause className="w-5 h-5" />
              )}
              Pausar
            </button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
              <Users className="w-5 h-5 text-gray-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats?.total || 0}</div>
              <div className="text-xs text-gray-500">Total</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              <Users className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats?.pending || 0}</div>
              <div className="text-xs text-gray-500">Pendentes</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Phone className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats?.calling || 0}</div>
              <div className="text-xs text-gray-500">Chamando</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats?.completed || 0}</div>
              <div className="text-xs text-gray-500">Completados</div>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <XCircle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats?.failed || 0}</div>
              <div className="text-xs text-gray-500">Falhou</div>
            </div>
          </div>
        </div>
      </div>

      {/* Progress */}
      {stats && stats.total > 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Progresso</span>
            <span className="text-sm text-gray-500">{stats.success_rate}% taxa de sucesso</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div className="h-full flex">
              <div
                className="bg-green-500 h-full transition-all duration-500"
                style={{ width: `${(stats.completed / stats.total) * 100}%` }}
              />
              <div
                className="bg-red-500 h-full transition-all duration-500"
                style={{ width: `${(stats.failed / stats.total) * 100}%` }}
              />
              <div
                className="bg-blue-500 h-full transition-all duration-500"
                style={{ width: `${(stats.calling / stats.total) * 100}%` }}
              />
            </div>
          </div>
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-green-500 rounded-full" /> Completados
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-red-500 rounded-full" /> Falhou
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-blue-500 rounded-full" /> Chamando
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-gray-300 rounded-full" /> Pendentes
            </span>
          </div>
        </div>
      )}

      {/* Contacts Table */}
      <ContactsTable campaignId={campaignId} />

      {showImport && (
        <ImportModal campaignId={campaignId} onClose={() => setShowImport(false)} />
      )}
    </div>
  );
}
