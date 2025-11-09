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
    console.log('🚀 [runFinancialAnalysis] Iniciando análise financeira');
    console.log('⚙️ [runFinancialAnalysis] Configuração recebida:', analysisConfig);
    
    // Primeiro, obter dados do perfil para construir user_data
    console.log('📋 [runFinancialAnalysis] Buscando perfil financeiro...');
    const profile = await this.getFinancialProfile();
    
    if (!profile) {
      throw new Error('Perfil financeiro não encontrado. Complete seu perfil primeiro.');
    }
    
    console.log('✅ [runFinancialAnalysis] Perfil encontrado:', {
      hasQuestionnaireData: !!profile.questionnaire_data,
      hasObjectiveData: !!profile.objective_data
    });
    
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
        transportation_methods: profile.questionnaire_data.transportation_methods,
        mensalidade_faculdade: profile.questionnaire_data.mensalidade_faculdade,
        valor_mensalidade: profile.questionnaire_data.valor_mensalidade
      },
      categorization_method: analysisConfig.categorization_method || "ollama/gemma3"
    };
    
    console.log('� [runFinancialAnalysis] ROTA: /api/financial/analyze-with-crewai');
    console.log('📊 [runFinancialAnalysis] Payload completo:', JSON.stringify(requestBody, null, 2));
    console.log('🤖 [runFinancialAnalysis] Modelo selecionado:', requestBody.categorization_method);
    
    const token = this.getToken();
    console.log('🔑 [runFinancialAnalysis] Token disponível:', !!token);
    
    console.log('📡 [runFinancialAnalysis] Enviando requisição POST...');
    const result = await this.apiClient.post('/api/financial/analyze-with-crewai', requestBody, token);
    
    console.log('✅ [runFinancialAnalysis] Resposta recebida da API:', result);
    console.log('📈 [runFinancialAnalysis] Tamanho da resposta:', JSON.stringify(result).length, 'caracteres');
    
    // Adicionar flag indicando que a análise foi concluída com sucesso
    const finalResult = {
      ...result,
      _analysisCompleted: true,
      _shouldRedirectToDashboard: true
    };
    
    console.log('🎯 [runFinancialAnalysis] Resultado final com flags:', {
      hasOriginalData: !!result,
      _analysisCompleted: finalResult._analysisCompleted,
      _shouldRedirectToDashboard: finalResult._shouldRedirectToDashboard
    });
    
    return finalResult;
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
    // Usar o método novo que já existe para buscar análises existentes
    console.log('📊 [getFinancialReports] Buscando relatórios financeiros existentes...');
    try {
      const result = await this.getFinancialAnalysis();
      console.log('✅ [getFinancialReports] Relatórios encontrados:', !!result);
      console.log('📈 [getFinancialReports] Detalhes:', {
        hasData: !!result,
        dataKeys: result ? Object.keys(result) : []
      });
      return result;
    } catch (error) {
      console.log('⚠️ [getFinancialReports] Nenhum relatório encontrado (normal para primeira análise):', error.message);
      throw error; // Re-lançar para que o chamador saiba que não há dados
    }
  }

  async generateFinancialAdvice(token) {
    // Usar o método de análise financeira para gerar nova análise
    console.log('🚀 [generateFinancialAdvice] Gerando nova análise financeira...');
    return this.runFinancialAnalysis();
  }
}

// Criar e exportar instância
export const dashboardService = new DashboardService();