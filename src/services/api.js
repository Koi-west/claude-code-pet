// API 服务基础配置
class ApiService {
  constructor() {
    this.baseURL = process.env.NODE_ENV === 'development' 
      ? 'http://localhost:8000' 
      : 'http://localhost:8000'; // 生产环境地址
    this.timeout = 10000;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      timeout: this.timeout,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // 发送消息到后端
  async sendMessage(message) {
    return this.request('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  // 获取系统状态
  async getStatus() {
    return this.request('/api/status');
  }
}

export default new ApiService();