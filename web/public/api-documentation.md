# LigAI API Documentation

**Base URL:** `http://localhost:8000`
**Version:** 1.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Calls](#calls)
4. [Prompts](#prompts)
5. [Webhooks](#webhooks)
6. [Schedules](#schedules)
7. [Campaigns](#campaigns)
8. [Settings](#settings)
9. [WebSocket](#websocket)
10. [System](#system)

---

## Overview

LigAI is an AI-powered phone call system that uses:
- **FreeSWITCH** for VoIP
- **Deepgram** for Speech-to-Text (STT)
- **Murf** for Text-to-Speech (TTS)
- **OpenAI GPT** for conversation AI

All API responses are in JSON format.

---

## Authentication

Currently, the API does not require authentication. This may change in future versions.

---

## Calls

### List Call History

```
GET /api/v1/calls
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| skip | integer | No | Number of records to skip (default: 0) |
| limit | integer | No | Maximum records to return (default: 50) |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/calls?skip=0&limit=10"
```

**Response:**
```json
[
  {
    "id": 1,
    "call_id": "call-123456-abc",
    "called_number": "5511999887766",
    "status": "completed",
    "duration": 120,
    "start_time": "2026-01-15T10:30:00Z",
    "end_time": "2026-01-15T10:32:00Z",
    "created_at": "2026-01-15T10:30:00Z"
  }
]
```

---

### Get Active Calls

```
GET /api/v1/calls/active
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/calls/active"
```

**Response:**
```json
[
  {
    "call_id": "call-123456-abc",
    "freeswitch_uuid": "call-123456-abc",
    "caller_number": "unknown",
    "called_number": "5511999887766",
    "state": "speaking",
    "duration": 45.5,
    "message_count": 5
  }
]
```

---

### Get Active Call Details

```
GET /api/v1/calls/active/{call_id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| call_id | string | Yes | The call ID |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/calls/active/call-123456-abc"
```

---

### Get Call with Transcript

```
GET /api/v1/calls/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The database ID of the call |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/calls/1"
```

**Response:**
```json
{
  "id": 1,
  "call_id": "call-123456-abc",
  "called_number": "5511999887766",
  "status": "completed",
  "duration": 120,
  "transcript": [
    {"role": "assistant", "content": "Hello, how can I help you?"},
    {"role": "user", "content": "I have a question about..."}
  ],
  "start_time": "2026-01-15T10:30:00Z",
  "end_time": "2026-01-15T10:32:00Z"
}
```

---

### Initiate a Call

```
POST /api/v1/calls/dial
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| number | string | Yes | Phone number to call (E.164 format recommended) |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/calls/dial" \
  -H "Content-Type: application/json" \
  -d '{"number": "5511999887766"}'
```

**Response:**
```json
{
  "success": true,
  "call_id": "call-123456-abc",
  "message": "Call initiated to 5511999887766"
}
```

---

### Hangup a Call

```
POST /api/v1/calls/{call_id}/hangup
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| call_id | string | Yes | The call ID to hang up |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/calls/call-123456-abc/hangup"
```

**Response:**
```json
{
  "success": true,
  "message": "Call hangup initiated"
}
```

---

### Delete Call Record

```
DELETE /api/v1/calls/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The database ID of the call |

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/calls/1"
```

---

## Prompts

### List All Prompts

```
GET /api/v1/prompts
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/prompts"
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Sales Assistant",
    "content": "You are a helpful sales assistant...",
    "is_active": true,
    "created_at": "2026-01-15T10:00:00Z",
    "updated_at": "2026-01-15T10:00:00Z"
  }
]
```

---

### Get Active Prompt

```
GET /api/v1/prompts/active
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/prompts/active"
```

---

### Get Prompt by ID

```
GET /api/v1/prompts/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The prompt ID |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/prompts/1"
```

---

### Create Prompt

```
POST /api/v1/prompts
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Name of the prompt |
| content | string | Yes | The prompt content/instructions |
| is_active | boolean | No | Whether to set as active (default: false) |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/prompts" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Customer Support",
    "content": "You are a helpful customer support agent...",
    "is_active": true
  }'
```

---

### Update Prompt

```
PUT /api/v1/prompts/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The prompt ID |

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | No | Name of the prompt |
| content | string | No | The prompt content |
| is_active | boolean | No | Whether prompt is active |

**Example:**
```bash
curl -X PUT "http://localhost:8000/api/v1/prompts/1" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'
```

---

### Activate Prompt

```
POST /api/v1/prompts/{id}/activate
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The prompt ID to activate |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/prompts/1/activate"
```

---

### Delete Prompt

```
DELETE /api/v1/prompts/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The prompt ID |

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/prompts/1"
```

---

## Webhooks

### Supported Events

| Event | Description |
|-------|-------------|
| `call.started` | Call was answered |
| `call.ended` | Call was terminated |
| `call.failed` | Call failed to connect |
| `call.state_changed` | Call state changed (ringing, speaking, etc.) |

---

### List Webhook Events

```
GET /api/v1/webhooks/events
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/webhooks/events"
```

**Response:**
```json
{
  "events": [
    {"event": "call.started", "description": "Fired when a call is answered"},
    {"event": "call.ended", "description": "Fired when a call ends"},
    {"event": "call.failed", "description": "Fired when a call fails"},
    {"event": "call.state_changed", "description": "Fired when call state changes"}
  ]
}
```

---

### List Webhooks

```
GET /api/v1/webhooks
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/webhooks"
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "CRM Integration",
    "url": "https://example.com/webhook",
    "events": ["call.started", "call.ended"],
    "is_active": true,
    "created_at": "2026-01-15T10:00:00Z"
  }
]
```

---

### Get Webhook by ID

```
GET /api/v1/webhooks/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The webhook ID |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/webhooks/1"
```

---

### Get Webhook Logs

```
GET /api/v1/webhooks/{id}/logs
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The webhook ID |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | integer | No | Maximum records (default: 50) |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/webhooks/1/logs?limit=10"
```

**Response:**
```json
[
  {
    "id": 1,
    "webhook_id": 1,
    "event": "call.started",
    "payload": {"call_id": "call-123"},
    "status_code": 200,
    "response_body": "OK",
    "success": true,
    "created_at": "2026-01-15T10:30:00Z"
  }
]
```

---

### Create Webhook

```
POST /api/v1/webhooks
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Name of the webhook |
| url | string | Yes | URL to send events to |
| events | array | Yes | List of events to subscribe |
| secret | string | No | Secret for HMAC signature |
| is_active | boolean | No | Whether webhook is active (default: true) |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/webhooks" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My CRM",
    "url": "https://example.com/webhook",
    "events": ["call.started", "call.ended"],
    "secret": "my-secret-key"
  }'
```

---

### Test Webhook

```
POST /api/v1/webhooks/{id}/test
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The webhook ID to test |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/webhooks/1/test"
```

**Response:**
```json
{
  "success": true,
  "status_code": 200,
  "response_time_ms": 150,
  "message": "Webhook test successful"
}
```

---

### Update Webhook

```
PUT /api/v1/webhooks/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The webhook ID |

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | No | Name of the webhook |
| url | string | No | URL to send events to |
| events | array | No | List of events |
| secret | string | No | Secret for HMAC |
| is_active | boolean | No | Whether active |

**Example:**
```bash
curl -X PUT "http://localhost:8000/api/v1/webhooks/1" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

---

### Delete Webhook

```
DELETE /api/v1/webhooks/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The webhook ID |

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/webhooks/1"
```

---

### Webhook Payload Format

When an event occurs, LigAI sends a POST request to your webhook URL with:

**Headers:**
```
Content-Type: application/json
X-Webhook-Signature: sha256=<hmac-signature>
X-Webhook-Event: <event-name>
```

**Body:**
```json
{
  "event": "call.started",
  "timestamp": "2026-01-15T10:30:00Z",
  "data": {
    "call_id": "call-123456-abc",
    "called_number": "5511999887766",
    "start_time": "2026-01-15T10:30:00Z"
  }
}
```

**HMAC Signature Verification (Python):**
```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

**Retry Policy:**
- 3 attempts with exponential backoff: 1s, 5s, 15s
- Retries on 5xx errors or network failures

---

## Schedules

### List Scheduled Calls

```
GET /api/v1/schedules
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| status | string | No | Filter by status (pending, completed, failed, cancelled) |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/schedules?status=pending"
```

**Response:**
```json
[
  {
    "id": 1,
    "phone_number": "5511999887766",
    "scheduled_time": "2026-01-15T14:00:00Z",
    "status": "pending",
    "created_at": "2026-01-15T10:00:00Z"
  }
]
```

---

### Get Schedule by ID

```
GET /api/v1/schedules/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The schedule ID |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/schedules/1"
```

---

### Create Scheduled Call

```
POST /api/v1/schedules
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| phone_number | string | Yes | Phone number to call |
| scheduled_time | string | Yes | ISO 8601 datetime for the call |
| notes | string | No | Optional notes |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/schedules" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "5511999887766",
    "scheduled_time": "2026-01-15T14:00:00Z",
    "notes": "Follow-up call"
  }'
```

**Response:**
```json
{
  "id": 1,
  "phone_number": "5511999887766",
  "scheduled_time": "2026-01-15T14:00:00Z",
  "status": "pending",
  "notes": "Follow-up call",
  "created_at": "2026-01-15T10:00:00Z"
}
```

---

### Cancel Scheduled Call

```
DELETE /api/v1/schedules/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The schedule ID |

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/schedules/1"
```

---

## Campaigns

### List Campaigns

```
GET /api/v1/campaigns
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/campaigns"
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "January Promotion",
    "status": "running",
    "total_contacts": 100,
    "completed_contacts": 45,
    "successful_contacts": 40,
    "failed_contacts": 5,
    "created_at": "2026-01-15T10:00:00Z"
  }
]
```

---

### Get Campaign by ID

```
GET /api/v1/campaigns/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The campaign ID |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/campaigns/1"
```

---

### Get Campaign Statistics

```
GET /api/v1/campaigns/{id}/stats
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The campaign ID |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/campaigns/1/stats"
```

**Response:**
```json
{
  "total_contacts": 100,
  "pending": 50,
  "completed": 45,
  "failed": 5,
  "success_rate": 88.9,
  "avg_duration": 95.5
}
```

---

### Get Campaign Contacts

```
GET /api/v1/campaigns/{id}/contacts
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The campaign ID |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| status | string | No | Filter by status |
| skip | integer | No | Records to skip |
| limit | integer | No | Max records (default: 100) |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/campaigns/1/contacts?status=pending"
```

---

### Create Campaign

```
POST /api/v1/campaigns
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Campaign name |
| description | string | No | Campaign description |
| max_concurrent | integer | No | Max simultaneous calls (default: 5) |
| prompt_id | integer | No | Specific prompt to use |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/campaigns" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "January Promotion",
    "description": "New year special offers",
    "max_concurrent": 3
  }'
```

---

### Import Contacts (JSON)

```
POST /api/v1/campaigns/{id}/contacts
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The campaign ID |

**Request Body:**
```json
{
  "contacts": [
    {"phone_number": "5511999887766", "name": "John Doe", "metadata": {"company": "ACME"}},
    {"phone_number": "5511999887767", "name": "Jane Doe"}
  ]
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/1/contacts" \
  -H "Content-Type: application/json" \
  -d '{
    "contacts": [
      {"phone_number": "5511999887766", "name": "John Doe"},
      {"phone_number": "5511999887767", "name": "Jane Doe"}
    ]
  }'
```

**Response:**
```json
{
  "imported": 2,
  "duplicates": 0,
  "errors": 0
}
```

---

### Import Contacts (CSV)

```
POST /api/v1/campaigns/{id}/contacts/csv
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The campaign ID |

**Request:** multipart/form-data with CSV file

**CSV Format:**
```csv
phone_number,name,company
5511999887766,John Doe,ACME
5511999887767,Jane Doe,XYZ Corp
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/1/contacts/csv" \
  -F "file=@contacts.csv"
```

---

### Start Campaign

```
POST /api/v1/campaigns/{id}/start
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The campaign ID |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/1/start"
```

**Response:**
```json
{
  "success": true,
  "message": "Campaign started"
}
```

---

### Pause Campaign

```
POST /api/v1/campaigns/{id}/pause
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The campaign ID |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/1/pause"
```

---

### Update Campaign

```
PUT /api/v1/campaigns/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The campaign ID |

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | No | Campaign name |
| description | string | No | Description |
| max_concurrent | integer | No | Max concurrent calls |

**Example:**
```bash
curl -X PUT "http://localhost:8000/api/v1/campaigns/1" \
  -H "Content-Type: application/json" \
  -d '{"max_concurrent": 10}'
```

---

### Delete Campaign

```
DELETE /api/v1/campaigns/{id}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | integer | Yes | The campaign ID |

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/v1/campaigns/1"
```

---

## Settings

### List All Settings

```
GET /api/v1/settings
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/settings"
```

**Response:**
```json
{
  "deepgram_api_key": "****",
  "murf_api_key": "****",
  "openai_api_key": "****",
  "max_concurrent_calls": "15"
}
```

---

### Get Setting

```
GET /api/v1/settings/{key}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| key | string | Yes | The setting key |

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/settings/max_concurrent_calls"
```

---

### Update Setting

```
PUT /api/v1/settings/{key}
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| key | string | Yes | The setting key |

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| value | string | Yes | The new value |

**Example:**
```bash
curl -X PUT "http://localhost:8000/api/v1/settings/max_concurrent_calls" \
  -H "Content-Type: application/json" \
  -d '{"value": "20"}'
```

---

### Test API Key

```
POST /api/v1/settings/test
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| service | string | Yes | Service name (deepgram, murf, openai) |
| api_key | string | Yes | API key to test |

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/settings/test" \
  -H "Content-Type: application/json" \
  -d '{"service": "openai", "api_key": "sk-..."}'
```

**Response:**
```json
{
  "valid": true,
  "message": "API key is valid"
}
```

---

### Reload Settings

```
POST /api/v1/settings/reload
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/settings/reload"
```

---

## WebSocket

### Dashboard Real-time Updates

```
WS /ws/dashboard
```

Connect to receive real-time updates about active calls and system statistics.

**Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/dashboard');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

**Message Format:**
```json
{
  "type": "stats_update",
  "data": {
    "active_calls": 5,
    "total_calls_today": 150,
    "avg_duration": 95.5
  }
}
```

---

### FreeSWITCH Audio Stream

```
WS /ws/{uuid}
```

Internal WebSocket for FreeSWITCH audio streaming. Used by the system for real-time audio processing.

---

## System

### Health Check

```
GET /health
```

**Example:**
```bash
curl -X GET "http://localhost:8000/health"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-15T10:30:00Z"
}
```

---

### System Statistics

```
GET /api/v1/stats
```

**Example:**
```bash
curl -X GET "http://localhost:8000/api/v1/stats"
```

**Response:**
```json
{
  "active_calls": 5,
  "total_calls_today": 150,
  "total_calls_all_time": 5000,
  "avg_duration": 95.5,
  "success_rate": 92.5
}
```

---

## Error Responses

All API errors follow this format:

```json
{
  "detail": "Error message here"
}
```

**Common HTTP Status Codes:**
| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

## Rate Limiting

Currently, there are no rate limits. This may change in future versions.

---

*Generated by LigAI*
