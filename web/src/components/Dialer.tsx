import { useState } from 'react';
import { Phone, Delete } from 'lucide-react';
import { useDialCall } from '../api/calls';
import { usePrompts } from '../api/prompts';
import { cn } from '../lib/utils';

export function Dialer() {
  const [number, setNumber] = useState('');
  const [selectedPromptId, setSelectedPromptId] = useState<number | undefined>();
  const dialMutation = useDialCall();
  const { data: prompts } = usePrompts();

  const handleDial = () => {
    if (number.length < 10) return;

    dialMutation.mutate(
      { number, prompt_id: selectedPromptId },
      {
        onSuccess: (response) => {
          if (response.success) {
            setNumber('');
          }
        },
      }
    );
  };

  const handleKeyPress = (digit: string) => {
    if (number.length < 15) {
      setNumber((prev) => prev + digit);
    }
  };

  const handleDelete = () => {
    setNumber((prev) => prev.slice(0, -1));
  };

  const dialPad = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['*', '0', '#'],
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Discar</h2>

      {/* Number display */}
      <div className="mb-4">
        <input
          type="text"
          value={number}
          onChange={(e) => setNumber(e.target.value.replace(/\D/g, ''))}
          placeholder="Digite o numero"
          className="w-full text-2xl text-center font-mono p-4 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Prompt selector */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Prompt (opcional)
        </label>
        <select
          value={selectedPromptId || ''}
          onChange={(e) => setSelectedPromptId(e.target.value ? Number(e.target.value) : undefined)}
          className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">Usar prompt ativo</option>
          {prompts?.map((prompt) => (
            <option key={prompt.id} value={prompt.id}>
              {prompt.name} {prompt.is_active && '(ativo)'}
            </option>
          ))}
        </select>
      </div>

      {/* Dial pad */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {dialPad.flat().map((digit) => (
          <button
            key={digit}
            onClick={() => handleKeyPress(digit)}
            className="p-4 text-xl font-medium bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            {digit}
          </button>
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleDelete}
          className="flex-1 p-4 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
        >
          <Delete className="w-6 h-6 mx-auto text-gray-600" />
        </button>
        <button
          onClick={handleDial}
          disabled={number.length < 10 || dialMutation.isPending}
          className={cn(
            'flex-1 p-4 rounded-lg transition-colors flex items-center justify-center gap-2',
            number.length >= 10 && !dialMutation.isPending
              ? 'bg-green-600 hover:bg-green-700 text-white'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          )}
        >
          <Phone className="w-6 h-6" />
          <span className="font-medium">
            {dialMutation.isPending ? 'Discando...' : 'Ligar'}
          </span>
        </button>
      </div>

      {/* Status message */}
      {dialMutation.isSuccess && (
        <div className="mt-4 p-3 bg-green-50 text-green-700 rounded-lg text-sm">
          {dialMutation.data.message}
        </div>
      )}
      {dialMutation.isError && (
        <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          Erro ao iniciar chamada: {(dialMutation.error as Error).message}
        </div>
      )}
    </div>
  );
}
