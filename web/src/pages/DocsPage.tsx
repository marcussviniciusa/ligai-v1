import { useState } from 'react';
import { ChevronDown, ChevronRight, Copy, Check, Download } from 'lucide-react';

// Method badge component
function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: 'bg-green-100 text-green-700',
    POST: 'bg-blue-100 text-blue-700',
    PUT: 'bg-yellow-100 text-yellow-700',
    DELETE: 'bg-red-100 text-red-700',
    WS: 'bg-purple-100 text-purple-700',
  };

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold ${colors[method] || 'bg-gray-100 text-gray-700'}`}>
      {method}
    </span>
  );
}

// Code block with copy button
function CodeBlock({ code, language: _language = 'json' }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-sm overflow-x-auto">
        <code>{code}</code>
      </pre>
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 p-1.5 bg-gray-700 rounded opacity-0 group-hover:opacity-100 transition-opacity"
      >
        {copied ? (
          <Check className="w-4 h-4 text-green-400" />
        ) : (
          <Copy className="w-4 h-4 text-gray-400" />
        )}
      </button>
    </div>
  );
}

// Endpoint documentation component
function Endpoint({
  method,
  path,
  description,
  params,
  body,
  response,
  curl,
}: {
  method: string;
  path: string;
  description: string;
  params?: Array<{ name: string; type: string; required: boolean; description: string }>;
  body?: string;
  response?: string;
  curl?: string;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border rounded-lg overflow-hidden mb-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 p-4 hover:bg-gray-50 text-left"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
        <MethodBadge method={method} />
        <code className="text-sm font-mono text-gray-700">{path}</code>
        <span className="text-sm text-gray-500 flex-1">{description}</span>
      </button>

      {expanded && (
        <div className="border-t p-4 bg-gray-50 space-y-4">
          {params && params.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Parametros</h4>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500">
                    <th className="pb-2">Nome</th>
                    <th className="pb-2">Tipo</th>
                    <th className="pb-2">Obrigatorio</th>
                    <th className="pb-2">Descricao</th>
                  </tr>
                </thead>
                <tbody>
                  {params.map((p) => (
                    <tr key={p.name} className="border-t">
                      <td className="py-2 font-mono text-blue-600">{p.name}</td>
                      <td className="py-2 text-gray-600">{p.type}</td>
                      <td className="py-2">
                        {p.required ? (
                          <span className="text-red-600">Sim</span>
                        ) : (
                          <span className="text-gray-400">Nao</span>
                        )}
                      </td>
                      <td className="py-2 text-gray-600">{p.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {body && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Request Body</h4>
              <CodeBlock code={body} />
            </div>
          )}

          {response && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Response</h4>
              <CodeBlock code={response} />
            </div>
          )}

          {curl && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Exemplo cURL</h4>
              <CodeBlock code={curl} language="bash" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Section component
function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="mb-12 scroll-mt-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6 pb-2 border-b">{title}</h2>
      {children}
    </section>
  );
}

// Navigation items
const navItems = [
  { id: 'overview', label: 'Visao Geral' },
  { id: 'calls', label: 'Chamadas' },
  { id: 'prompts', label: 'Prompts' },
  { id: 'webhooks', label: 'Webhooks' },
  { id: 'schedules', label: 'Agendamentos' },
  { id: 'campaigns', label: 'Campanhas' },
  { id: 'settings', label: 'Configuracoes' },
  { id: 'websocket', label: 'WebSocket' },
];

export function DocsPage() {
  const [activeSection, setActiveSection] = useState('overview');

  return (
    <div className="flex gap-8">
      {/* Sidebar Navigation */}
      <nav className="w-48 flex-shrink-0 sticky top-4 h-fit">
        <h3 className="text-sm font-medium text-gray-500 mb-3">NAVEGACAO</h3>
        <ul className="space-y-1">
          {navItems.map((item) => (
            <li key={item.id}>
              <a
                href={`#${item.id}`}
                onClick={() => setActiveSection(item.id)}
                className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeSection === item.id
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {item.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {/* Main Content */}
      <main className="flex-1 min-w-0">
        {/* Overview */}
        <Section id="overview" title="Visao Geral">
          <div className="prose max-w-none">
            {/* Download Button */}
            <div className="mb-6 flex justify-end">
              <a
                href="/api-documentation.md"
                download="LigAI-API-Documentation.md"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                <Download className="w-4 h-4" />
                Baixar Documentacao (Markdown)
              </a>
            </div>

            <p className="text-gray-600 mb-4">
              A API do LigAI permite integrar o sistema de chamadas com IA em suas aplicacoes.
              Todos os endpoints estao disponíveis sob o prefixo <code>/api/v1/</code>.
            </p>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h4 className="font-medium text-blue-900 mb-2">URL Base</h4>
              <code className="text-blue-700">http://seu-servidor:8000/api/v1/</code>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h4 className="font-medium text-yellow-900 mb-2">Autenticacao</h4>
              <p className="text-yellow-800 text-sm">
                Atualmente a API nao requer autenticacao. Todos os endpoints sao publicos.
              </p>
            </div>
          </div>
        </Section>

        {/* Calls */}
        <Section id="calls" title="Chamadas">
          <p className="text-gray-600 mb-6">
            Endpoints para gerenciar chamadas telefonicas.
          </p>

          <Endpoint
            method="GET"
            path="/api/v1/calls"
            description="Lista historico de chamadas"
            params={[
              { name: 'page', type: 'int', required: false, description: 'Pagina (padrao: 1)' },
              { name: 'per_page', type: 'int', required: false, description: 'Itens por pagina (padrao: 20, max: 100)' },
              { name: 'status', type: 'string', required: false, description: 'Filtrar por status' },
            ]}
            response={`{
  "items": [
    {
      "id": 1,
      "call_id": "call-123",
      "called_number": "5511999887766",
      "status": "completed",
      "duration_seconds": 120.5,
      "created_at": "2026-01-15T10:30:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20
}`}
            curl="curl http://localhost:8000/api/v1/calls?page=1&per_page=10"
          />

          <Endpoint
            method="GET"
            path="/api/v1/calls/active"
            description="Lista chamadas em andamento"
            response={`[
  {
    "call_id": "call-123",
    "called_number": "5511999887766",
    "state": "processing",
    "duration": 45.5,
    "message_count": 3
  }
]`}
            curl="curl http://localhost:8000/api/v1/calls/active"
          />

          <Endpoint
            method="POST"
            path="/api/v1/calls/dial"
            description="Inicia uma nova chamada"
            body={`{
  "number": "5511999887766",
  "prompt_id": 1
}`}
            response={`{
  "success": true,
  "call_id": "call-123",
  "message": "Chamada iniciada"
}`}
            curl={`curl -X POST http://localhost:8000/api/v1/calls/dial \\
  -H "Content-Type: application/json" \\
  -d '{"number": "5511999887766"}'`}
          />

          <Endpoint
            method="POST"
            path="/api/v1/calls/{call_id}/hangup"
            description="Encerra uma chamada"
            params={[
              { name: 'call_id', type: 'string', required: true, description: 'ID da chamada' },
            ]}
            response={`{
  "success": true,
  "message": "Chamada encerrada"
}`}
            curl="curl -X POST http://localhost:8000/api/v1/calls/call-123/hangup"
          />

          <Endpoint
            method="GET"
            path="/api/v1/calls/{id}"
            description="Detalhes da chamada com transcricao"
            params={[
              { name: 'id', type: 'int', required: true, description: 'ID numerico da chamada' },
            ]}
            response={`{
  "id": 1,
  "call_id": "call-123",
  "status": "completed",
  "messages": [
    {"role": "assistant", "content": "Ola, como posso ajudar?"},
    {"role": "user", "content": "Gostaria de informacoes"}
  ]
}`}
          />

          <Endpoint
            method="DELETE"
            path="/api/v1/calls/{id}"
            description="Remove registro de chamada"
            params={[
              { name: 'id', type: 'int', required: true, description: 'ID numerico da chamada' },
            ]}
            curl="curl -X DELETE http://localhost:8000/api/v1/calls/1"
          />
        </Section>

        {/* Prompts */}
        <Section id="prompts" title="Prompts">
          <p className="text-gray-600 mb-6">
            Gerenciamento de prompts de IA para as chamadas.
          </p>

          <Endpoint
            method="GET"
            path="/api/v1/prompts"
            description="Lista todos os prompts"
            response={`[
  {
    "id": 1,
    "name": "Atendimento",
    "description": "Prompt para atendimento",
    "system_prompt": "Voce e um assistente...",
    "voice_id": "pt-BR-isadora",
    "llm_model": "gpt-4.1-nano",
    "temperature": 0.7,
    "is_active": true
  }
]`}
          />

          <Endpoint
            method="POST"
            path="/api/v1/prompts"
            description="Cria um novo prompt"
            body={`{
  "name": "Vendas",
  "description": "Prompt para vendas",
  "system_prompt": "Voce e um vendedor...",
  "voice_id": "pt-BR-isadora",
  "llm_model": "gpt-4.1-nano",
  "temperature": 0.7
}`}
          />

          <Endpoint
            method="POST"
            path="/api/v1/prompts/{id}/activate"
            description="Define prompt como ativo"
            params={[
              { name: 'id', type: 'int', required: true, description: 'ID do prompt' },
            ]}
          />
        </Section>

        {/* Webhooks */}
        <Section id="webhooks" title="Webhooks">
          <p className="text-gray-600 mb-6">
            Configure webhooks para receber notificacoes de eventos em tempo real.
          </p>

          <div className="bg-gray-50 border rounded-lg p-6 mb-6">
            <h3 className="font-medium text-gray-900 mb-4">Eventos Suportados</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b">
                  <th className="pb-2">Evento</th>
                  <th className="pb-2">Descricao</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b">
                  <td className="py-2 font-mono text-blue-600">call.started</td>
                  <td className="py-2 text-gray-600">Chamada foi atendida</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2 font-mono text-blue-600">call.ended</td>
                  <td className="py-2 text-gray-600">Chamada foi encerrada (inclui transcricao)</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2 font-mono text-blue-600">call.failed</td>
                  <td className="py-2 text-gray-600">Chamada falhou</td>
                </tr>
                <tr>
                  <td className="py-2 font-mono text-blue-600">call.state_changed</td>
                  <td className="py-2 text-gray-600">Estado da chamada mudou</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="bg-gray-50 border rounded-lg p-6 mb-6">
            <h3 className="font-medium text-gray-900 mb-4">Formato do Payload</h3>
            <CodeBlock code={`{
  "event": "call.ended",
  "timestamp": "2026-01-15T10:35:00Z",
  "data": {
    "call_id": "call-123",
    "duration": 120.5,
    "transcript": [
      {"role": "assistant", "content": "Ola!"},
      {"role": "user", "content": "Oi, tudo bem?"}
    ]
  }
}`} />
          </div>

          <div className="bg-gray-50 border rounded-lg p-6 mb-6">
            <h3 className="font-medium text-gray-900 mb-4">Assinatura HMAC</h3>
            <p className="text-gray-600 text-sm mb-3">
              Se configurar um secret, o LigAI enviara uma assinatura HMAC-SHA256 no header:
            </p>
            <CodeBlock code="X-Webhook-Signature: sha256=abc123..." />
            <p className="text-gray-500 text-xs mt-2">
              Verifique a assinatura comparando com HMAC-SHA256 do body usando seu secret.
            </p>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <h4 className="font-medium text-yellow-900 mb-2">Politica de Retry</h4>
            <p className="text-yellow-800 text-sm">
              Em caso de falha (status != 2xx), o sistema tenta novamente 3 vezes com backoff: 1s, 5s, 15s.
            </p>
          </div>

          <Endpoint
            method="GET"
            path="/api/v1/webhooks/events"
            description="Lista eventos suportados"
            response={`{
  "events": ["call.started", "call.ended", "call.failed", "call.state_changed"]
}`}
          />

          <Endpoint
            method="POST"
            path="/api/v1/webhooks"
            description="Cria configuracao de webhook"
            body={`{
  "url": "https://seu-servidor.com/webhook",
  "events": ["call.started", "call.ended"],
  "secret": "sua-chave-secreta"
}`}
          />

          <Endpoint
            method="POST"
            path="/api/v1/webhooks/{id}/test"
            description="Envia evento de teste"
            params={[
              { name: 'id', type: 'int', required: true, description: 'ID do webhook' },
            ]}
          />

          <Endpoint
            method="GET"
            path="/api/v1/webhooks/{id}/logs"
            description="Historico de entregas"
            params={[
              { name: 'id', type: 'int', required: true, description: 'ID do webhook' },
              { name: 'limit', type: 'int', required: false, description: 'Limite (padrao: 50)' },
            ]}
          />
        </Section>

        {/* Schedules */}
        <Section id="schedules" title="Agendamentos">
          <p className="text-gray-600 mb-6">
            Agende chamadas para serem realizadas em horarios especificos.
          </p>

          <Endpoint
            method="POST"
            path="/api/v1/schedules"
            description="Agenda uma chamada"
            body={`{
  "phone_number": "5511999887766",
  "scheduled_time": "2026-01-20T14:30:00Z",
  "prompt_id": 1,
  "notes": "Ligacao de retorno"
}`}
            response={`{
  "id": 1,
  "phone_number": "5511999887766",
  "scheduled_time": "2026-01-20T14:30:00Z",
  "status": "pending"
}`}
          />

          <Endpoint
            method="GET"
            path="/api/v1/schedules"
            description="Lista agendamentos"
            params={[
              { name: 'status', type: 'string', required: false, description: 'Filtrar: pending, completed, cancelled, failed' },
            ]}
          />

          <Endpoint
            method="DELETE"
            path="/api/v1/schedules/{id}"
            description="Cancela agendamento (apenas se pending)"
            params={[
              { name: 'id', type: 'int', required: true, description: 'ID do agendamento' },
            ]}
          />
        </Section>

        {/* Campaigns */}
        <Section id="campaigns" title="Campanhas">
          <p className="text-gray-600 mb-6">
            Gerencie campanhas de discagem em lote.
          </p>

          <Endpoint
            method="POST"
            path="/api/v1/campaigns"
            description="Cria uma campanha"
            body={`{
  "name": "Campanha Janeiro",
  "description": "Campanha de vendas",
  "prompt_id": 1,
  "max_concurrent": 5
}`}
          />

          <Endpoint
            method="POST"
            path="/api/v1/campaigns/{id}/contacts"
            description="Importa contatos via JSON"
            params={[
              { name: 'id', type: 'int', required: true, description: 'ID da campanha' },
            ]}
            body={`{
  "contacts": [
    {"phone_number": "5511999887766", "name": "Joao"},
    {"phone_number": "5511988776655", "name": "Maria"}
  ]
}`}
            response={`{
  "success": true,
  "imported": 2
}`}
          />

          <Endpoint
            method="POST"
            path="/api/v1/campaigns/{id}/contacts/csv"
            description="Importa contatos via CSV"
            params={[
              { name: 'id', type: 'int', required: true, description: 'ID da campanha' },
              { name: 'file', type: 'file', required: true, description: 'Arquivo CSV' },
            ]}
            curl={`curl -X POST http://localhost:8000/api/v1/campaigns/1/contacts/csv \\
  -F "file=@contatos.csv"`}
          />

          <div className="bg-gray-50 border rounded-lg p-4 mb-4">
            <h4 className="font-medium text-gray-900 mb-2">Formato CSV</h4>
            <CodeBlock code={`phone_number,name
5511999887766,Joao Silva
5511988776655,Maria Santos
5511977665544,Pedro`} />
          </div>

          <Endpoint
            method="POST"
            path="/api/v1/campaigns/{id}/start"
            description="Inicia ou retoma campanha"
            params={[
              { name: 'id', type: 'int', required: true, description: 'ID da campanha' },
            ]}
          />

          <Endpoint
            method="POST"
            path="/api/v1/campaigns/{id}/pause"
            description="Pausa campanha"
            params={[
              { name: 'id', type: 'int', required: true, description: 'ID da campanha' },
            ]}
          />

          <Endpoint
            method="GET"
            path="/api/v1/campaigns/{id}/stats"
            description="Estatisticas da campanha"
            params={[
              { name: 'id', type: 'int', required: true, description: 'ID da campanha' },
            ]}
            response={`{
  "total": 100,
  "pending": 50,
  "calling": 5,
  "completed": 40,
  "failed": 5,
  "success_rate": 88.9
}`}
          />
        </Section>

        {/* Settings */}
        <Section id="settings" title="Configuracoes">
          <p className="text-gray-600 mb-6">
            Gerenciamento de chaves de API e configuracoes do sistema.
          </p>

          <Endpoint
            method="GET"
            path="/api/v1/settings"
            description="Lista todas as configuracoes"
            response={`[
  {
    "id": 1,
    "key": "DEEPGRAM_API_KEY",
    "value": "****",
    "is_configured": true,
    "is_secret": true
  }
]`}
          />

          <Endpoint
            method="PUT"
            path="/api/v1/settings/{key}"
            description="Atualiza uma configuracao"
            params={[
              { name: 'key', type: 'string', required: true, description: 'Chave da configuracao' },
            ]}
            body={`{
  "value": "nova-chave-api"
}`}
          />

          <Endpoint
            method="POST"
            path="/api/v1/settings/test"
            description="Testa uma chave de API"
            body={`{
  "key": "OPENAI_API_KEY",
  "value": "sk-..."
}`}
            response={`{
  "success": true,
  "message": "Conexao bem-sucedida"
}`}
          />
        </Section>

        {/* WebSocket */}
        <Section id="websocket" title="WebSocket">
          <p className="text-gray-600 mb-6">
            Conexoes WebSocket para atualizacoes em tempo real.
          </p>

          <div className="bg-gray-50 border rounded-lg p-6 mb-6">
            <h3 className="font-medium text-gray-900 mb-4">Dashboard em Tempo Real</h3>
            <div className="flex items-center gap-2 mb-4">
              <MethodBadge method="WS" />
              <code className="text-sm font-mono text-gray-700">/ws/dashboard</code>
            </div>
            <p className="text-gray-600 text-sm mb-4">
              Conecte-se para receber eventos de chamadas em tempo real.
            </p>

            <h4 className="font-medium text-gray-900 mb-2">Eventos Recebidos</h4>
            <CodeBlock code={`// call_started
{
  "type": "call_started",
  "data": {"call_id": "call-123", "called_number": "5511..."},
  "timestamp": "2026-01-15T10:30:00Z"
}

// call_ended
{
  "type": "call_ended",
  "data": {"call_id": "call-123", "duration": 120.5},
  "timestamp": "2026-01-15T10:32:00Z"
}

// stats_updated
{
  "type": "stats_updated",
  "data": {"active_calls": 3, "total_calls": 100},
  "timestamp": "2026-01-15T10:30:00Z"
}`} />

            <h4 className="font-medium text-gray-900 mt-4 mb-2">Mensagens do Cliente</h4>
            <CodeBlock code={`// Ping para manter conexao
{"type": "ping"}

// Solicitar estatisticas
{"type": "get_stats"}`} />
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">Exemplo JavaScript</h4>
            <CodeBlock code={`const ws = new WebSocket('ws://localhost:8000/ws/dashboard');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Evento:', data.type, data.data);
};

ws.onopen = () => {
  // Enviar ping periodicamente
  setInterval(() => {
    ws.send(JSON.stringify({type: 'ping'}));
  }, 25000);
};`} />
          </div>
        </Section>
      </main>
    </div>
  );
}
