import { API_BASE_URL } from '../utils/constants';

class ApiClient {
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      console.log('Fazendo requisição:', url, config);
      console.log('Headers being sent:', config.headers);
      const response = await fetch(url, config);
      
      if (!response.ok) {
        let errorMessage = 'Erro na requisição';
        try {
          const error = await response.json();
          console.error('Erro detalhado:', error);
        
        // Tratamento específico para erros de validação do FastAPI
        if (error.detail && Array.isArray(error.detail)) {
          const validationErrors = error.detail.map(err => 
            `${err.loc?.join('.')} - ${err.msg}`
          ).join('; ');
          errorMessage = `Erro de validação: ${validationErrors}`;
        } else if (error.detail && typeof error.detail === 'string') {
          errorMessage = error.detail;
        } else if (error.message) {
          errorMessage = error.message;
        } else {
          errorMessage = JSON.stringify(error);
        }
        } catch (parseError) {
          const textError = await response.text();
          console.error('Erro como texto:', textError);
          errorMessage = textError || `HTTP ${response.status}`;
        }
        throw new Error(errorMessage);
      }

      return await response.json();
    } catch (error) {
      console.error('Erro na requisição:', error);
      throw new Error(error.message || 'Erro de conexão');
    }
  }

  async get(endpoint, token = null) {
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return this.request(endpoint, {
      method: 'GET',
      headers,
    });
  }

  async post(endpoint, data, token = null, useFormData = false) {
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Adicionar log para debug
    console.log('Dados sendo enviados:', data);
    console.log('Endpoint:', endpoint);

    let body;
    if (useFormData) {
      // Para endpoints que esperam form data (como OAuth)
      body = new URLSearchParams(data);
      headers['Content-Type'] = 'application/x-www-form-urlencoded';
    } else {
      // Para endpoints que esperam JSON
      body = JSON.stringify(data);
      headers['Content-Type'] = 'application/json';
    }

    return this.request(endpoint, {
      method: 'POST',
      headers,
      body,
    });
  }

  async uploadFile(endpoint, file, token = null) {
    const formData = new FormData();
    formData.append('file', file);

    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erro no upload');
    }

    return await response.json();
  }
}

export const apiClient = new ApiClient();