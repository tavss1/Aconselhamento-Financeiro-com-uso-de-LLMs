import { apiClient } from './apiClient';
import { useState } from 'react';

class FinancialDashboardService {
  constructor() {
    this.apiClient = apiClient;
  }

  getToken() {
    return localStorage.getItem('access_token');
  }

  /**
   * Busca dados completos do dashboard financeiro
   * @returns {Promise<Object>} Dados completos do dashboard
   */
  async getDashboardData() {
    const token = this.getToken();
    if (!token) {
      throw new Error('Token de autenticação não encontrado');
    }

    try {
      console.log('🔍 Buscando dados do dashboard...');
      const response = await this.apiClient.get('/api/dashboard/financial-analysis', token);
      console.log('📥 Resposta recebida do backend:', response);
      
      const processedData = this.processDashboardData(response);
      console.log('✅ Dados processados com sucesso:', processedData);
      
      return processedData;
    } catch (error) {
      console.error('❌ Erro ao buscar dados do dashboard:', error);
      
      // Se o erro for 404 (perfil não encontrado), dar uma mensagem mais específica
      if (error.message && error.message.includes('404')) {
        throw new Error('Perfil financeiro não encontrado. Complete seu perfil primeiro.');
      }
      
      // Se for 500, pode ser problema no servidor
      if (error.message && error.message.includes('500')) {
        throw new Error('Erro no servidor. Tente novamente em alguns minutos.');
      }
      
      // Se for erro de processamento de dados
      if (error.message && error.message.includes('overall_assessment')) {
        throw new Error('Dados de análise não disponíveis. Execute uma análise financeira primeiro.');
      }
      
      throw new Error(error.message || 'Erro ao carregar dados do dashboard');
    }
  }

  async runFinancialAnalysis(analysisConfig = {}) {
    const requestBody = {
      config: {
        categorization_method: analysisConfig.method || "ollama"
      }
    };
    
    const token = this.getToken();
    return this.apiClient.post('/financial/run-analysis', requestBody, token);
  }

  async getAnalysisStatus(userId) {
    const token = this.getToken();
    return this.apiClient.get(`/financial/analysis-status/${userId}`, token);
  }

  async getAnalysisHistory() {
    const token = this.getToken();
    if (!token) {
      throw new Error('Token de autenticação não encontrado');
    }

    try {
      console.log('🔍 Buscando histórico de análises...');
      const response = await this.apiClient.get('/api/llm/latest-response', token);
      console.log('📥 Histórico recebido:', response);
      return response;
    } catch (error) {
      console.error('❌ Erro ao buscar histórico:', error);
      throw new Error(error.message || 'Erro ao carregar histórico de análises');
    }
  }

  async getAnalysisHistoryComplete() {
    const token = this.getToken();
    if (!token) {
      throw new Error('Token de autenticação não encontrado');
    }

    try {
      console.log('🔍 Buscando histórico completo de análises...');
      
      // Primeiro, buscar o perfil para obter o profile_id
      const profile = await this.apiClient.get('/api/financial-profile', token);
      if (!profile || !profile.id) {
        throw new Error('Perfil financeiro não encontrado');
      }

      // Agora buscar o histórico completo
      const response = await this.apiClient.get(`/api/llm/responses/${profile.id}`, token);
      console.log('📥 Histórico completo recebido:', response);
      return response;
    } catch (error) {
      console.error('❌ Erro ao buscar histórico completo:', error);
      throw new Error(error.message || 'Erro ao carregar histórico completo de análises');
    }
  }

  /**
   * Processa e normaliza os dados do dashboard
   * @param {Object} rawData - Dados brutos do backend
   * @returns {Object} Dados processados para o frontend
   */
  processDashboardData(rawData) {
    console.log('🔍 Processando dados do dashboard:', rawData);
    if (!rawData) {
      throw new Error('Dados do dashboard não encontrados');
    }

    // Tentar acessar a estrutura real do backend
    let dashboard = null;
    if (rawData.data?.dashboard?.dashboard_data) {
      dashboard = rawData.data.dashboard.dashboard_data;
      console.log('Estrutura: rawData.data.dashboard.dashboard_data');
    } else if (rawData.data?.dashboard) {
      dashboard = rawData.data.dashboard;
      console.log('Estrutura: rawData.data.dashboard');
    } else if (rawData.dashboard_data) {
      dashboard = rawData.dashboard_data;
      console.log('Estrutura: rawData.dashboard_data');
    } else if (rawData.dashboard) {
      dashboard = rawData.dashboard;
      console.log('Estrutura: rawData.dashboard');
    } else {
      dashboard = rawData;
      console.log('Estrutura: rawData (usando objeto raiz)');
    }

    // Log da estrutura completa para debug
    try {
      console.log('🔍 Chaves do rawData:', Object.keys(rawData));
      if (rawData.data) console.log('🔍 Chaves de rawData.data:', Object.keys(rawData.data));
      if (rawData.data?.dashboard) console.log('🔍 Chaves de rawData.data.dashboard:', Object.keys(rawData.data.dashboard));
      if (dashboard) console.log('🔍 Chaves do dashboard extraído:', Object.keys(dashboard));
    } catch (e) {
      console.log('Erro ao logar estrutura:', e);
    }

    // Extrair seções reais, sem valores default
    const metadata = dashboard?.metadata;
    const transactionsAnalysis = dashboard?.transactions_analysis;
    const financialAdvice = dashboard?.financial_advice;
    const visualizations = dashboard?.visualizations;
    const comparativeMetrics = dashboard?.comparative_metrics;
    const alertsAndNotifications = dashboard?.alerts_and_notifications;
    const modelInfo = dashboard?.model_info;

    // Log detalhado de cada seção
    console.log('🔍 metadata:', metadata);
    console.log('🔍 transactionsAnalysis:', transactionsAnalysis);
    console.log('🔍 financialAdvice:', financialAdvice);
    console.log('🔍 visualizations:', visualizations);
    console.log('🔍 comparativeMetrics:', comparativeMetrics);
    console.log('🔍 alertsAndNotifications:', alertsAndNotifications);
    console.log('🔍 modelInfo:', modelInfo);

    // Extrair dados do perfil dos comparative_metrics e transactions_analysis
    const spendingPatterns = comparativeMetrics?.spending_patterns;
    const summary = transactionsAnalysis?.summary;

    // Construir objeto de retorno fiel aos dados reais (NÃO usar valores default)
    const processedData = {
      profile: {
        id: rawData?.profile_id,
        age: metadata?.age,
        monthlyIncome: spendingPatterns?.monthly_income ?? summary?.total_income,
        monthlyExpenses: spendingPatterns?.monthly_expenses ?? summary?.total_expenses,
        savingsCapacity: spendingPatterns?.net_savings ?? summary?.net_flow,
        debtToIncome: comparativeMetrics?.debt_to_income,
        savingsRate: spendingPatterns?.savings_rate_percentage,
        liquidAssets: comparativeMetrics?.liquid_assets,
        riskProfile: metadata?.risk_profile || comparativeMetrics?.risk_profile || 'moderado',
        goal: metadata?.goal
      },
      transactions: {
        summary: summary,
        categoriesBreakdown: transactionsAnalysis?.categories_breakdown,
        topTransactions: transactionsAnalysis?.top_transactions,
        rawTransactions: transactionsAnalysis?.raw_transactions
      },
      advice: {
        overallAssessment: financialAdvice?.overall_assessment,
        recommendations: financialAdvice?.recommendations_by_timeline,
        measurableGoals: financialAdvice?.measurable_goals,
        summary: financialAdvice?.summary,
        alerts: financialAdvice?.alerts
      },
      charts: {
        expensePieChart: visualizations?.expense_pie_chart,
        monthlyFlowChart: visualizations?.monthly_flow_chart,
        categoryTrendChart: visualizations?.category_trend_chart
      },
      benchmarks: comparativeMetrics?.benchmarks,
      spendingPatterns: spendingPatterns,
      alerts: this.formatAlerts(alertsAndNotifications),
      metadata: {
        ...metadata,
        llmModel: modelInfo?.llm_used || metadata?.llm_model || 'ollama/gemma3',
        evaluationEnabled: modelInfo?.evaluation_enabled,
        riskProfile: metadata?.risk_profile || comparativeMetrics?.risk_profile || 'moderado'
      }
    };

    console.log('✅ Dados processados finais:', processedData);
    return processedData;
  }

  /**
   * Formata alertas da nova estrutura
   * @param {Object} alertsData - Dados de alertas
   * @returns {Array} Array de alertas formatados
   */
  formatAlerts(alertsData) {
    const alerts = [];
    
    // Alertas urgentes
    if (alertsData?.urgent) {
      alertsData.urgent.forEach(alert => {
        alerts.push({
          title: alert.title,
          message: alert.message,
          severity: alert.priority === 'critical' ? 'high' : 'medium',
          type: alert.type,
          actionRequired: alert.action_required
        });
      });
    }
    
    // Alertas informativos
    if (alertsData?.informational) {
      alertsData.informational.forEach(alert => {
        alerts.push({
          title: alert.title,
          message: alert.message,
          severity: 'low',
          type: alert.type,
          actionRequired: alert.action_required || false
        });
      });
    }
    
    return alerts;
  }

  /**
   * Formata valor monetário para exibição
   * @param {number} value - Valor numérico
   * @returns {string} Valor formatado em Real
   */
  formatCurrency(value) {
    if (typeof value !== 'number') return 'R$ 0,00';
    
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(Math.abs(value));
  }

  /**
   * Formata porcentagem para exibição
   * @param {number} value - Valor numérico
   * @returns {string} Valor formatado em porcentagem
   */
  formatPercentage(value) {
    if (typeof value !== 'number') return '0%';
    
    return new Intl.NumberFormat('pt-BR', {
      style: 'percent',
      minimumFractionDigits: 1,
      maximumFractionDigits: 1
    }).format(value / 100);
  }

  /**
   * Determina a cor baseada no tipo de transação
   * @param {number} amount - Valor da transação
   * @returns {string} Classe CSS para cor
   */
  getAmountColorClass(amount) {
    if (amount > 0) return 'text-green-600';
    if (amount < 0) return 'text-red-600';
    return 'text-gray-600';
  }

  /**
   * Calcula o status de saúde financeira
   * @param {Object} data - Dados do dashboard
   * @returns {Object} Status de saúde financeira
   */
  calculateFinancialHealth(data) {
    console.log('🔍 Calculando saúde financeira com dados:', data);
    
    // Verificações defensivas
    if (!data || !data.profile || !data.transactions) {
      console.warn('⚠️ Dados insuficientes para calcular saúde financeira');
      return {
        score: 0,
        status: 'poor',
        factors: [
          { name: 'Taxa de Poupança', status: 'poor', points: 0 },
          { name: 'Endividamento', status: 'poor', points: 0 },
          { name: 'Fluxo de Caixa', status: 'poor', points: 0 }
        ],
        maxScore: 100
      };
    }

    const { profile, transactions } = data;
    
    let score = 0;
    const factors = [];

    // Fator 1: Taxa de poupança
    const savingsRate = profile?.savingsRate || 0;
    if (savingsRate > 20) {
      score += 25;
      factors.push({ name: 'Taxa de Poupança', status: 'excellent', points: 25 });
    } else if (savingsRate > 10) {
      score += 15;
      factors.push({ name: 'Taxa de Poupança', status: 'good', points: 15 });
    } else if (savingsRate > 0) {
      score += 5;
      factors.push({ name: 'Taxa de Poupança', status: 'fair', points: 5 });
    } else {
      factors.push({ name: 'Taxa de Poupança', status: 'poor', points: 0 });
    }

    // Fator 2: Relação dívida/renda
    const debtToIncome = profile?.debtToIncome || 0;
    if (debtToIncome < 0.2) {
      score += 25;
      factors.push({ name: 'Endividamento', status: 'excellent', points: 25 });
    } else if (debtToIncome < 0.4) {
      score += 15;
      factors.push({ name: 'Endividamento', status: 'good', points: 15 });
    } else if (debtToIncome < 0.6) {
      score += 5;
      factors.push({ name: 'Endividamento', status: 'fair', points: 5 });
    } else {
      factors.push({ name: 'Endividamento', status: 'poor', points: 0 });
    }

    // Fator 3: Fluxo de caixa
    const netFlow = transactions?.summary?.net_flow || 0;
    if (netFlow > 0) {
      score += 25;
      factors.push({ name: 'Fluxo de Caixa', status: 'excellent', points: 25 });
    } else if (netFlow > -100) {
      score += 10;
  factors.push({ name: 'Fluxo de Caixa', status: 'fair', points: 10 });
    } else {
      factors.push({ name: 'Fluxo de Caixa', status: 'poor', points: 0 });
    }

    // Normalizar a pontuação para escala de 0 a 100 considerando 3 fatores (máx. 75)
    const rawScore = score; // máximo possível 75
    const normalizedScore = Math.round((rawScore / 75) * 100);

    let healthStatus = 'poor';
    if (normalizedScore >= 80) healthStatus = 'excellent';
    else if (normalizedScore >= 60) healthStatus = 'good';
    else if (normalizedScore >= 40) healthStatus = 'fair';

    return {
      score: normalizedScore,
      status: healthStatus,
      factors,
      maxScore: 100
    };
  }
}

// Criar e exportar instância
export const financialDashboardService = new FinancialDashboardService();

// Hook personalizado para análise financeira baseado na documentação da API
export const useFinancialAnalysis = () => {
  const [analysisResults, setAnalysisResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runCompleteAnalysis = async () => {
    setLoading(true);
    setError(null);

    try {
      console.log('🚀 Iniciando análise financeira completa...');

      // 1. Executar análise financeira com CrewAI
      console.log('📊 Executando análise com LLMs...');
      const results = await financialDashboardService.runFinancialAnalysis();
      console.log('✅ Análise executada:', results);

      // 2. Buscar dados do dashboard
      console.log('📈 Obtendo dados do dashboard...');
      const dashboardData = await financialDashboardService.getDashboardData();
      console.log('✅ Dados do dashboard obtidos:', dashboardData);

      // 3. Combinar resultados
      setAnalysisResults({
        analysis: results,
        dashboard: dashboardData,
        timestamp: new Date().toISOString()
      });

      console.log('🎉 Análise financeira completa finalizada!');
      return { analysis: results, dashboard: dashboardData };

    } catch (error) {
      console.error('❌ Erro na análise financeira:', error);
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  return {
    analysisResults,
    loading,
    error,
    runCompleteAnalysis
  };
};

// Função utilitária para monitorar status de análise
export const monitorAnalysisStatus = async (userId, onStatusUpdate) => {
  const pollInterval = 3000; // 3 segundos
  let attempts = 0;
  const maxAttempts = 20; // Máximo 1 minuto

  const poll = async () => {
    try {
      const status = await financialDashboardService.getAnalysisStatus(userId);
      onStatusUpdate(status);

      // Se ainda está processando e não atingiu o limite, continuar polling
      if (status.status === 'processing' && attempts < maxAttempts) {
        attempts++;
        setTimeout(poll, pollInterval);
      }
    } catch (error) {
      console.error('Erro ao verificar status:', error);
      onStatusUpdate({ status: 'error', error: error.message });
    }
  };

  // Iniciar polling
  poll();
};