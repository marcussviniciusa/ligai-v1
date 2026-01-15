import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

type MessageHandler = (data: { type: string; data: unknown; timestamp: string }) => void;

export function useDashboardWebSocket(onMessage?: MessageHandler) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Dashboard WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        // Handle specific message types
        switch (message.type) {
          case 'call_started':
          case 'call_ended':
          case 'call_state_changed':
            queryClient.invalidateQueries({ queryKey: ['calls', 'active'] });
            break;
          case 'stats_updated':
            queryClient.invalidateQueries({ queryKey: ['stats'] });
            break;
          case 'ping':
            ws.send(JSON.stringify({ type: 'pong' }));
            break;
        }

        // Call custom handler if provided
        if (onMessage) {
          onMessage(message);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      console.log('Dashboard WebSocket disconnected, reconnecting in 3s...');
      reconnectTimeoutRef.current = window.setTimeout(connect, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }, [queryClient, onMessage]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return wsRef.current;
}
