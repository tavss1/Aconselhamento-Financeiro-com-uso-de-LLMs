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
        age: profile.questionnaire_data.age,
        monthly_income: profile.questionnaire_data.monthly_income,
        dependents: profile.questionnaire_data.dependents,
        risk_profile: profile.questionnaire_data.risk_profile,
        financial_goal: profile.objective_data?.financial_goal,
        target_amount: profile.objective_data?.financial_goal_details?.target_amount,
        time_frame: profile.objective_data?.financial_goal_details?.time_frame,
        debt_to_income_ratio: profile.questionnaire_data.debt_to_income_ratio,
        liquid_assets: profile.questionnaire_data.liquid_assets,
        transportation_methods: profile.questionnaire_data.transportation_methods
      },
      categorization_method: analysisConfig.method || "ollama"
    };
    
    const token = this.getToken();
    const result = await this.apiClient.post('/api/financial/analyze-with-crewai', requestBody, token);
    
    // Adicionar flag indicando que a análise foi concluída com sucesso
    return {
      ...result,
      _analysisCompleted: true,
      _shouldRedirectToDashboard: true
    };
  }

  async getFinancialAnalysis() {
    const token = this.getToken();
    return this.apiClient.get('/api/dashboard/financial-analysis', token);
  }

  async getAnalysisStatus(userId) {
    const token = this.getToken();
    return this.apiClient.get(`/api/financial/analysis-status/${userId}`, token);
  }

  async checkAnalysisStatus() {
    const token = this.getToken();
    try {
      // Primeiro verificar se o endpoint específico existe
      return await this.apiClient.get('/api/auth/check-analysis-status', token);
    } catch (error) {
      console.log('Endpoint check-analysis-status não disponível, verificando manualmente...');
      
      // Fallback: verificar manualmente o status
      try {
        const profile = await this.getFinancialProfile();
        const hasProfile = !!(profile && profile.questionnaire_data);
        const hasExtract = !!(profile && profile.objective_data);
        
        let hasAnalysis = false;
        try {
          await this.getFinancialAnalysis();
          hasAnalysis = true;
        } catch {
          hasAnalysis = false;
        }
        
        return {
          has_profile: hasProfile,
          has_extract: hasExtract,
          has_analysis: hasAnalysis,
          should_redirect_to: hasAnalysis ? 'dashboard' : 'wizard'
        };
      } catch (profileError) {
        console.error('Erro ao verificar perfil:', profileError);
        return {
          has_profile: false,
          has_extract: false,
          has_analysis: false,
          should_redirect_to: 'wizard'
        };
      }
    }
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