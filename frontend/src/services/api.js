import axios from 'axios';

// Configuração base do axios
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 segundos para operações de LLM
  headers: {
    'Content-Type': 'application/json',
  },
});

// Configurações de ambiente
export const apiConfig = {
  baseURL: API_BASE_URL,
  timeout: 30000,
  maxFileSize: 10 * 1024 * 1024, // 10MB
  allowedFileTypes: ['.csv', '.xlsx', '.xls'],
  supportedImageTypes: ['image/jpeg', 'image/png', 'image/gif'],
};

// Interceptor para adicionar token automaticamente
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para tratar respostas e erros
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Tratar erro 401 (não autorizado)
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    
    // Log de erros para debug
    console.error('API Error:', error.response?.data || error.message);
    
    return Promise.reject(error);
  }
);