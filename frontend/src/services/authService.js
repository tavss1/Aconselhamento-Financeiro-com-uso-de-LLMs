import { apiClient } from './apiClient';

class AuthService {
  async login(email, password) {
    return await apiClient.post('/api/auth/login', { 
      email: email, 
      password: password 
    });
  }

  async register(name, email, password) {
    return await apiClient.post('/api/auth/register', { 
      name, 
      email, 
      password 
    });
  }

  async validateToken() {
    const token = localStorage.getItem('access_token');
    
    if (!token) return false;
    
    try {
      const response = await apiClient.post('/api/auth/validate-token', {}, token);
      return response && response.status !== false;
    } catch (error) {
      console.error('Erro ao validar token:', error);
      return false;
    }
  }

  async getUserProfile(token) {
    return await apiClient.get('/api/user/profile', token);
  }
}

export const authService = new AuthService();