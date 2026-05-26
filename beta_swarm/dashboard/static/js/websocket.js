// websocket.js - Premium, stable self-healing WebSocket connection client hub for Beta Swarm v3.2
// WS_URL is already defined in utils.js — reuse it; fallback if loaded standalone
if (typeof WS_URL === 'undefined') {
    var WS_URL = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host;
}

class SwarmWebSocket {
    constructor(endpoint) {
        this.endpoint = endpoint;
        this.url = endpoint.startsWith('ws://') || endpoint.startsWith('wss://') ? endpoint : `${WS_URL}${endpoint}`;
        this.ws = null;
        this.listeners = {};
        this.subscriptions = new Set();
        this.reconnectAttempts = 0;
        this.maxDelay = 30000;
        this.active = false;
        this.reconnectTimer = null;
    }

    connect() {
        this.active = true;
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        console.log(`[SwarmWS] Connecting to ${this.url}...`);
        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log(`[SwarmWS] Connected to ${this.url}`);
                this.reconnectAttempts = 0;
                this.trigger('open', null);
                
                // Resubscribe to all event types automatically
                this.subscriptions.forEach(eventType => {
                    this.send({ type: 'subscribe', event: eventType });
                });
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    // Standard message routing
                    if (data && data.type) {
                        this.trigger('message', data);
                        this.trigger(data.type, data);
                    } else {
                        this.trigger('message', data);
                    }
                } catch {
                    this.trigger('message', event.data);
                }
            };

            this.ws.onclose = (event) => {
                console.log(`[SwarmWS] Connection closed: ${this.url}`);
                this.trigger('close', event);
                
                if (this.active) {
                    this._scheduleReconnect();
                }
            };

            this.ws.onerror = (err) => {
                console.error(`[SwarmWS] Socket error on ${this.url}:`, err);
                this.trigger('error', err);
            };
        } catch (e) {
            console.error(`[SwarmWS] Exception during init on ${this.url}:`, e);
            if (this.active) {
                this._scheduleReconnect();
            }
        }
    }

    _scheduleReconnect() {
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        
        // Exponential backoff: 1s -> 2s -> 4s -> 8s -> max 30s
        const delay = Math.min(Math.pow(2, this.reconnectAttempts) * 1000, this.maxDelay);
        this.reconnectAttempts++;
        console.log(`[SwarmWS] Reconnecting to ${this.url} in ${(delay/1000).toFixed(1)}s (attempt ${this.reconnectAttempts})...`);
        
        this.reconnectTimer = setTimeout(() => {
            if (this.active) this.connect();
        }, delay);
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(typeof data === 'object' ? JSON.stringify(data) : data);
            return true;
        }
        return false;
    }

    on(eventType, handler) {
        // Strict single-listener pattern: exactly one callback per event type to prevent memory leaks!
        this.listeners[eventType] = handler;
        
        // Track the subscription type to sync on reconnect
        if (eventType !== 'open' && eventType !== 'message' && eventType !== 'close' && eventType !== 'error') {
            this.subscriptions.add(eventType);
            // Send subscription event immediately if open
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.send({ type: 'subscribe', event: eventType });
            }
        }
    }

    off(eventType) {
        if (this.listeners[eventType]) {
            delete this.listeners[eventType];
        }
        this.subscriptions.delete(eventType);
    }

    trigger(eventType, data) {
        const handler = this.listeners[eventType];
        if (handler) {
            try {
                handler(data);
            } catch (e) {
                console.error(`[SwarmWS] Error in listener callback for event '${eventType}':`, e);
            }
        }
    }

    disconnect() {
        this.active = false;
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            try {
                this.ws.close();
            } catch {}
            this.ws = null;
        }
        console.log(`[SwarmWS] Disconnected from ${this.url}`);
    }

    destroy() {
        this.disconnect();
        this.listeners = {};
        this.subscriptions.clear();
    }
}

// Backwards-compatible WebSocketHub wrapping SwarmWebSocket
class WebSocketHub {
    constructor() {
        this.sockets = {};
    }

    connect(name, endpoint) {
        if (this.sockets[name]) {
            this.sockets[name].destroy();
        }
        const ws = new SwarmWebSocket(endpoint);
        this.sockets[name] = ws;
        ws.connect();
    }

    send(name, data) {
        const ws = this.sockets[name];
        if (ws) {
            return ws.send(data);
        }
        return false;
    }

    on(name, event, callback) {
        const ws = this.sockets[name];
        if (ws) {
            ws.on(event, callback);
        }
    }

    off(name, event) {
        const ws = this.sockets[name];
        if (ws) {
            ws.off(event);
        }
    }

    disconnect(name) {
        if (this.sockets[name]) {
            this.sockets[name].destroy();
            delete this.sockets[name];
        }
    }

    destroy() {
        // Loop through and destroy all active connections (called on SPA view transitions)
        Object.keys(this.sockets).forEach(name => {
            this.sockets[name].destroy();
        });
        this.sockets = {};
        console.log("[WebSocketHub] All WebSocket instances destroyed and listeners purged.");
    }
}

// Global Hub Instance
const wsHub = new WebSocketHub();
window.wsHub = wsHub;
window.SwarmWebSocket = SwarmWebSocket;
