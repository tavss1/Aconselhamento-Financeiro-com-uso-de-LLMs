import { apiClient } from './apiClient';

class AuthService {
  async login(email, password) {
    return await apiClient.post('/auth/login', { 
      email: email, 
      password: password 
    });
  }

  async register(name, email, password) {
    return await apiClient.post('/auth/register', { name, email, password });
  }

  async getUserProfile(token) {
    return await apiClient.get('/user/profile', token);
  }
}

export const authService = new AuthService();