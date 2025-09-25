import { apiClient } from './apiClient';

class DashboardService {
  constructor() {
    this.apiClient = apiClient; // Garantir que apiClient está definido
  }

  getToken() {
    return localStorage.getItem('token');
  }

  async saveFinancialProfile(data) {
    console.log('=== DashboardService.saveFinancialProfile ===');
    console.log('apiClient disponível:', !!this.apiClient);
    console.log('Dados recebidos:', data);
    
    // Verificar se apiClient está disponível
    if (!this.apiClient) {
      throw new Error('ApiClient não está inicializado');
    }

    // Verificar se os dados estão na estrutura correta
    if (!data.questionnaire_data || !data.objective_data) {
      throw new Error('Estrutura de dados inválida: questionnaire_data e objective_data são obrigatórios');
    }
    
    const token = this.getToken();
    console.log('Token disponível:', !!token);
    
    return this.apiClient.post('/financial-profile', data, token);
  }

  async uploadExtract(file) {
    const token = this.getToken();
    return this.apiClient.uploadFile('/upload-extract', file, token);
  }
}

// Criar e exportar instância
export const dashboardService = new DashboardService();