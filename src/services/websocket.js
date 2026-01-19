// WebSocket 服务 - 最简实现
class WebSocketService {
  constructor() {
    this.ws = null;
    this.url = 'ws://localhost:8000/ws/chat';
    this.onMessage = null;
    this.onStatusChange = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('WebSocket 连接成功');
        this.reconnectAttempts = 0;
        this.notifyStatus('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (this.onMessage) {
            this.onMessage(data);
          }
        } catch (error) {
          console.error('解析消息失败:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket 连接关闭');
        this.notifyStatus('disconnected');
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
        this.notifyStatus('error');
      };

    } catch (error) {
      console.error('WebSocket 连接失败:', error);
      this.notifyStatus('error');
    }
  }

  sendMessage(content) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'message',
        content: content
      };
      this.ws.send(JSON.stringify(message));
      return true;
    } else {
      console.error('WebSocket 未连接');
      return false;
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      setTimeout(() => {
        this.connect();
      }, 3000);
    }
  }

  notifyStatus(status) {
    if (this.onStatusChange) {
      this.onStatusChange(status);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export default new WebSocketService();