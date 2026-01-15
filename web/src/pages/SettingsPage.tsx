import { useState, useEffect } from 'react';
import { Key, Check, X, Loader2, RefreshCw, Eye, EyeOff } from 'lucide-react';
import { useSettings, useUpdateSetting, useTestApiKey, useReloadSettings } from '../api/settings';
import type { Setting } from '../api/client';

interface ApiKeyConfig {
  key: string;
  label: string;
  placeholder: string;
  helpUrl: string;
}

const API_KEYS_CONFIG: ApiKeyConfig[] = [
  {
    key: 'DEEPGRAM_API_KEY',
    label: 'Deepgram API Key',
    placeholder: 'Sua chave do Deepgram',
    helpUrl: 'https://console.deepgram.com/',
  },
  {
    key: 'MURF_API_KEY',
    label: 'Murf AI API Key',
    placeholder: 'Sua chave do Murf AI',
    helpUrl: 'https://murf.ai/api',
  },
  {
    key: 'OPENAI_API_KEY',
    label: 'OpenAI API Key',
    placeholder: 'Sua chave da OpenAI',
    helpUrl: 'https://platform.openai.com/api-keys',
  },
];

export function SettingsPage() {
  const { data: settings, isLoading } = useSettings();
  const updateMutation = useUpdateSetting();
  const testMutation = useTestApiKey();
  const reloadMutation = useReloadSettings();

  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string } | null>>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize form values when settings load
  useEffect(() => {
    if (settings) {
      const values: Record<string, string> = {};
      settings.forEach((s) => {
        // Start with empty for new input, not the masked value
        values[s.key] = '';
      });
      setFormValues(values);
    }
  }, [settings]);

  const handleInputChange = (key: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
    // Clear test result when value changes
    setTestResults((prev) => ({ ...prev, [key]: null }));
  };

  const toggleShowValue = (key: string) => {
    setShowValues((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleTest = async (key: string) => {
    const value = formValues[key];
    if (!value) {
      setTestResults((prev) => ({
        ...prev,
        [key]: { success: false, message: 'Digite uma API key para testar' },
      }));
      return;
    }

    try {
      const result = await testMutation.mutateAsync({ key, value });
      setTestResults((prev) => ({ ...prev, [key]: result }));
    } catch {
      setTestResults((prev) => ({
        ...prev,
        [key]: { success: false, message: 'Erro ao testar conexao' },
      }));
    }
  };

  const handleSave = async (key: string) => {
    const value = formValues[key];
    if (!value) return;

    try {
      await updateMutation.mutateAsync({ key, value });
      setFormValues((prev) => ({ ...prev, [key]: '' }));
      setHasChanges(false);
    } catch {
      // Error handled by mutation
    }
  };

  const handleSaveAll = async () => {
    const keysToSave = Object.entries(formValues).filter(([, value]) => value);
    for (const [key, value] of keysToSave) {
      await updateMutation.mutateAsync({ key, value });
    }
    // Clear form after save
    setFormValues((prev) => {
      const cleared: Record<string, string> = {};
      Object.keys(prev).forEach((k) => (cleared[k] = ''));
      return cleared;
    });
    setHasChanges(false);
  };

  const handleReload = async () => {
    await reloadMutation.mutateAsync();
  };

  const getSettingByKey = (key: string): Setting | undefined => {
    return settings?.find((s) => s.key === key);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded w-1/4 animate-pulse"></div>
        <div className="bg-white rounded-xl shadow-sm border p-6 animate-pulse">
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Configuracoes</h1>
          <p className="text-gray-500">Configure as API keys dos servicos</p>
        </div>
        <button
          onClick={handleReload}
          disabled={reloadMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 text-gray-700 bg-white border rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${reloadMutation.isPending ? 'animate-spin' : ''}`} />
          Recarregar
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Key className="w-5 h-5 text-blue-600" />
            API Keys
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Configure as chaves de API para os servicos de IA
          </p>
        </div>

        <div className="divide-y">
          {API_KEYS_CONFIG.map((config) => {
            const setting = getSettingByKey(config.key);
            const testResult = testResults[config.key];
            const inputValue = formValues[config.key] || '';
            const isConfigured = setting?.is_configured;

            return (
              <div key={config.key} className="px-6 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {config.label}
                      {isConfigured && (
                        <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">
                          Configurado
                        </span>
                      )}
                    </label>
                    <p className="text-xs text-gray-500 mb-2">
                      {setting?.description}
                      {' '}
                      <a
                        href={config.helpUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        Obter chave
                      </a>
                    </p>

                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <input
                          type={showValues[config.key] ? 'text' : 'password'}
                          value={inputValue}
                          onChange={(e) => handleInputChange(config.key, e.target.value)}
                          placeholder={isConfigured ? setting?.value : config.placeholder}
                          className="w-full p-2 pr-10 border rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                        />
                        <button
                          type="button"
                          onClick={() => toggleShowValue(config.key)}
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          {showValues[config.key] ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      </div>

                      <button
                        onClick={() => handleTest(config.key)}
                        disabled={!inputValue || testMutation.isPending}
                        className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {testMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          'Testar'
                        )}
                      </button>

                      <button
                        onClick={() => handleSave(config.key)}
                        disabled={!inputValue || updateMutation.isPending}
                        className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {updateMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          'Salvar'
                        )}
                      </button>
                    </div>

                    {testResult && (
                      <div
                        className={`mt-2 flex items-center gap-2 text-sm ${
                          testResult.success ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {testResult.success ? (
                          <Check className="w-4 h-4" />
                        ) : (
                          <X className="w-4 h-4" />
                        )}
                        {testResult.message}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {hasChanges && (
          <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
            <button
              onClick={() => {
                setFormValues((prev) => {
                  const cleared: Record<string, string> = {};
                  Object.keys(prev).forEach((k) => (cleared[k] = ''));
                  return cleared;
                });
                setHasChanges(false);
              }}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleSaveAll}
              disabled={updateMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              Salvar Todas
            </button>
          </div>
        )}
      </div>

      {/* Info box */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <h3 className="font-medium text-blue-900 mb-2">Informacoes</h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• As API keys sao armazenadas de forma segura no banco de dados</li>
          <li>• Use o botao "Testar" para verificar se a chave esta correta antes de salvar</li>
          <li>• Apos salvar, as configuracoes sao aplicadas automaticamente</li>
          <li>• Se voce perder uma chave, pode gerar uma nova no site do provedor</li>
        </ul>
      </div>
    </div>
  );
}
