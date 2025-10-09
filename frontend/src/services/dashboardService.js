import { apiClient } from './apiClient';

class DashboardService {
  constructor() {
    this.apiClient = apiClient; // Garantir que apiClient está definido
  }

  getToken() {
    return localStorage.getItem('access_token');
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
    
    return this.apiClient.post('/api/financial-profile', data, token);
  }

  async getFinancialProfile() {
    const token = this.getToken();
    return this.apiClient.get('/api/financial-profile', token);
  }

  async uploadExtract(file) {
    const token = this.getToken();
    return this.apiClient.uploadFile('/api/upload-extract', file, token);
  }

  async getProcessingStatus(profileId) {
    const token = this.getToken();
    return this.apiClient.get(`/api/processing-status/${profileId}`, token);
  }

  async runFinancialAnalysis(analysisConfig = {}) {
    // Primeiro, obter dados do perfil para construir user_data
    const profile = await this.getFinancialProfile();
    
    if (!profile) {
      throw new Error('Perfil financeiro não encontrado. Complete seu perfil primeiro.');
    }
    
    const requestBody = {
      user_data: {
        age: profile.questionnaire_data.age || 25,
        monthly_income: profile.questionnaire_data.monthly_income || 3000,
        dependents: profile.questionnaire_data.dependents || [],
        risk_profile: profile.questionnaire_data.risk_profile || "moderado",
        financial_goal: profile.objective_data?.financial_goal || "Reserva de emergência",
        target_amount: profile.objective_data?.financial_goal_details?.target_amount || 1000,
        time_frame: profile.objective_data?.financial_goal_details?.time_frame || "12 meses",
        debt_to_income_ratio: profile.questionnaire_data.debt_to_income_ratio || 0.3,
        liquid_assets: profile.questionnaire_data.liquid_assets || 0,
        transportation_methods: profile.questionnaire_data.transportation_methods || "Transporte público"
      },
      categorization_method: analysisConfig.method || "ollama"
    };
    
    const token = this.getToken();
    return this.apiClient.post('/api/financial/analyze-with-crewai', requestBody, token);
  }

  async getFinancialAnalysis() {
    const token = this.getToken();
    return this.apiClient.get('/api/dashboard/financial-analysis', token);
  }

  async getAnalysisStatus(userId) {
    const token = this.getToken();
    return this.apiClient.get(`/api/financial/analysis-status/${userId}`, token);
  }

  // Métodos legados para compatibilidade com simpleDashboard.jsx
  async getFinancialReports(token) {
    // Usar o método novo que já existe
    return this.getFinancialAnalysis();
  }

  async generateFinancialAdvice(token) {
    // Usar o método de análise financeira
    return this.runFinancialAnalysis();
  }
}

// Criar e exportar instância
export const dashboardService = new DashboardService();