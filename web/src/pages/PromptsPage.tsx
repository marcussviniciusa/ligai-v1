import { useState } from 'react';
import { Plus, Edit, Trash2, Check, MessageSquare } from 'lucide-react';
import {
  usePrompts,
  useCreatePrompt,
  useUpdatePrompt,
  useDeletePrompt,
  useActivatePrompt,
} from '../api/prompts';
import type { Prompt } from '../api/client';

interface PromptFormData {
  name: string;
  description: string;
  system_prompt: string;
  voice_id: string;
  llm_model: string;
  temperature: number;
}

const defaultFormData: PromptFormData = {
  name: '',
  description: '',
  system_prompt: '',
  voice_id: 'pt-BR-isadora',
  llm_model: 'gpt-4.1-nano',
  temperature: 0.7,
};

export function PromptsPage() {
  const { data: prompts, isLoading } = usePrompts();
  const createMutation = useCreatePrompt();
  const updateMutation = useUpdatePrompt();
  const deleteMutation = useDeletePrompt();
  const activateMutation = useActivatePrompt();

  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState<PromptFormData>(defaultFormData);

  const handleCreate = () => {
    setIsEditing(true);
    setEditingId(null);
    setFormData(defaultFormData);
  };

  const handleEdit = (prompt: Prompt) => {
    setIsEditing(true);
    setEditingId(prompt.id);
    setFormData({
      name: prompt.name,
      description: prompt.description || '',
      system_prompt: prompt.system_prompt,
      voice_id: prompt.voice_id,
      llm_model: prompt.llm_model,
      temperature: prompt.temperature,
    });
  };

  const handleSave = () => {
    if (editingId) {
      updateMutation.mutate(
        { id: editingId, data: formData },
        {
          onSuccess: () => {
            setIsEditing(false);
            setEditingId(null);
          },
        }
      );
    } else {
      createMutation.mutate(formData, {
        onSuccess: () => {
          setIsEditing(false);
        },
      });
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditingId(null);
    setFormData(defaultFormData);
  };

  const handleDelete = (id: number) => {
    if (confirm('Tem certeza que deseja excluir este prompt?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleActivate = (id: number) => {
    activateMutation.mutate(id);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-gray-200 rounded w-1/4 animate-pulse"></div>
        <div className="bg-white rounded-xl shadow-sm border p-6 animate-pulse">
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-gray-100 rounded"></div>
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
          <h1 className="text-2xl font-bold text-gray-900">Prompts</h1>
          <p className="text-gray-500">Configure os prompts da IA</p>
        </div>
        <button
          onClick={handleCreate}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Novo Prompt
        </button>
      </div>

      {/* Form modal */}
      {isEditing && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-semibold">
                {editingId ? 'Editar Prompt' : 'Novo Prompt'}
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Ex: Atendimento Vendas"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descricao
                </label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Descricao opcional"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  System Prompt
                </label>
                <textarea
                  value={formData.system_prompt}
                  onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                  rows={8}
                  className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  placeholder="Voce e um assistente..."
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Voz
                  </label>
                  <select
                    value={formData.voice_id}
                    onChange={(e) => setFormData({ ...formData, voice_id: e.target.value })}
                    className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="pt-BR-isadora">Isadora (PT-BR)</option>
                    <option value="pt-BR-arthur">Arthur (PT-BR)</option>
                    <option value="pt-BR-ana">Ana (PT-BR)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Modelo LLM
                  </label>
                  <select
                    value={formData.llm_model}
                    onChange={(e) => setFormData({ ...formData, llm_model: e.target.value })}
                    className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="gpt-4.1-nano">GPT-4.1 Nano (Mais Rápido)</option>
                    <option value="gpt-4.1-mini">GPT-4.1 Mini</option>
                    <option value="gpt-4.1">GPT-4.1</option>
                    <option value="gpt-5.2-instant">GPT-5.2 Instant</option>
                    <option value="gpt-5.2">GPT-5.2</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Temperatura
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="2"
                    step="0.1"
                    value={formData.temperature}
                    onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                    className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-3">
              <button
                onClick={handleCancel}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                disabled={!formData.name || !formData.system_prompt}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Prompts list */}
      <div className="bg-white rounded-xl shadow-sm border">
        {prompts?.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-500">
            <MessageSquare className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>Nenhum prompt configurado</p>
            <button
              onClick={handleCreate}
              className="mt-4 text-blue-600 hover:text-blue-700 font-medium"
            >
              Criar primeiro prompt
            </button>
          </div>
        ) : (
          <div className="divide-y">
            {prompts?.map((prompt) => (
              <div key={prompt.id} className="px-6 py-4 hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-gray-900">{prompt.name}</h3>
                      {prompt.is_active && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                          Ativo
                        </span>
                      )}
                    </div>
                    {prompt.description && (
                      <p className="text-sm text-gray-500 mt-1">{prompt.description}</p>
                    )}
                    <p className="text-sm text-gray-400 mt-2 line-clamp-2 font-mono">
                      {prompt.system_prompt.slice(0, 150)}...
                    </p>
                    <div className="flex gap-4 mt-2 text-xs text-gray-400">
                      <span>Voz: {prompt.voice_id}</span>
                      <span>Modelo: {prompt.llm_model}</span>
                      <span>Temp: {prompt.temperature}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {!prompt.is_active && (
                      <button
                        onClick={() => handleActivate(prompt.id)}
                        className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                        title="Ativar"
                      >
                        <Check className="w-5 h-5" />
                      </button>
                    )}
                    <button
                      onClick={() => handleEdit(prompt)}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="Editar"
                    >
                      <Edit className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(prompt.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Excluir"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
