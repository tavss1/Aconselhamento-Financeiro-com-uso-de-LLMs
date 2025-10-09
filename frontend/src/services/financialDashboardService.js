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

    // Verificar se temos a estrutura esperada
    const dashboard = rawData.dashboard || rawData.dashboard_data || rawData;
    const profile = rawData.profile || {};
    const transactions = rawData.transactions || {};
    
    console.log('📊 Estrutura encontrada:', {
      hasDashboard: !!dashboard,
      hasProfile: !!profile,
      hasTransactions: !!transactions,
      dashboardKeys: dashboard ? Object.keys(dashboard) : [],
      rawDataKeys: Object.keys(rawData)
    });

    // Construir objeto de retorno com valores seguros
    return {
      // Informações do perfil
      profile: {
        id: profile?.profile_id || profile?.id || null,
        age: profile?.dados_pessoais?.idade || profile?.age || profile?.questionnaire_data?.age || 25,
        monthlyIncome: profile?.renda_mensal || profile?.monthly_income || profile?.questionnaire_data?.monthly_income || 0,
        monthlyExpenses: profile?.gastos_mensais || profile?.monthly_expenses || 0,
        savingsCapacity: profile?.capacidade_poupanca || profile?.savings_capacity || 0,
        debtToIncome: profile?.debt_to_income || profile?.questionnaire_data?.debt_to_income_ratio || 0.3,
        savingsRate: profile?.savings_rate || 0,
        liquidAssets: profile?.ativos_liquidos || profile?.liquid_assets || profile?.questionnaire_data?.liquid_assets || 0,
        riskProfile: profile?.dados_pessoais?.risk_profile || profile?.risk_profile || profile?.questionnaire_data?.risk_profile || 'moderado',
        goal: profile?.objetivo || profile?.objective_data || {}
      },

      // Análise de transações
      transactions: {
        summary: dashboard?.dashboard_data?.transactions_analysis?.summary || dashboard?.transactions_analysis?.summary || {
          total_transactions: 0,
          total_income: 0,
          total_expenses: 0,
          net_flow: 0
        },
        categoriesBreakdown: dashboard?.dashboard_data?.transactions_analysis?.categories_breakdown || dashboard?.transactions_analysis?.categories_breakdown || [],
        topTransactions: dashboard?.dashboard_data?.transactions_analysis?.top_transactions || dashboard?.transactions_analysis?.top_transactions || [],
        rawTransactions: transactions?.transacoes || transactions?.transactions || []
      },

      // Conselhos financeiros
      advice: {
        overallAssessment: dashboard?.dashboard_data?.financial_advice?.overall_assessment || 
                          dashboard?.financial_advice?.overall_assessment || 
                          'Análise não disponível. Execute uma análise financeira primeiro.',
        recommendations: dashboard?.dashboard_data?.financial_advice?.recommendations_by_timeline || 
                        dashboard?.financial_advice?.recommendations_by_timeline || 
                        dashboard?.dashboard_data?.financial_advice?.recommendations || 
                        dashboard?.financial_advice?.recommendations || [],
        measurableGoals: dashboard?.dashboard_data?.financial_advice?.measurable_goals || 
                        dashboard?.financial_advice?.measurable_goals || [],
        alerts: dashboard?.dashboard_data?.financial_advice?.alerts || 
               dashboard?.financial_advice?.alerts || []
      },

      // Visualizações
      charts: {
        expensePieChart: dashboard?.dashboard_data?.visualizations?.expense_pie_chart || 
                       dashboard?.visualizations?.expense_pie_chart || [],
        monthlyFlowChart: dashboard?.dashboard_data?.visualizations?.monthly_flow_chart || 
                         dashboard?.visualizations?.monthly_flow_chart || [],
        categoryTrendChart: dashboard?.dashboard_data?.visualizations?.category_trend_chart || 
                           dashboard?.visualizations?.category_trend_chart || []
      },

      // Métricas comparativas
      benchmarks: dashboard?.dashboard_data?.comparative_metrics?.benchmarks || 
                 dashboard?.comparative_metrics?.benchmarks || {},
      spendingPatterns: dashboard?.dashboard_data?.comparative_metrics?.spending_patterns || 
                       dashboard?.comparative_metrics?.spending_patterns || {},

      // Alertas e notificações
      alerts: dashboard?.dashboard_data?.alerts_and_notifications || 
             dashboard?.alerts_and_notifications || [],

      // Metadata
      metadata: {
        generatedAt: dashboard?.dashboard_data?.metadata?.generated_at || 
                    dashboard?.metadata?.generated_at || 
                    new Date().toISOString(),
        totalDataPoints: dashboard?.dashboard_data?.metadata?.total_data_points || 
                        dashboard?.metadata?.total_data_points || 0,
        llmModel: rawData?.metadata?.llm_model || 'Não especificado'
      }
    };
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
          { name: 'Reserva de Emergência', status: 'poor', points: 0 },
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

    // Fator 3: Reserva de emergência
    const liquidAssets = profile?.liquidAssets || 0;
    const monthlyExpenses = profile?.monthlyExpenses || 1; // Evitar divisão por zero
    const emergencyMonths = liquidAssets / monthlyExpenses;
    if (emergencyMonths >= 6) {
      score += 25;
      factors.push({ name: 'Reserva de Emergência', status: 'excellent', points: 25 });
    } else if (emergencyMonths >= 3) {
      score += 15;
      factors.push({ name: 'Reserva de Emergência', status: 'good', points: 15 });
    } else if (emergencyMonths >= 1) {
      score += 5;
      factors.push({ name: 'Reserva de Emergência', status: 'fair', points: 5 });
    } else {
      factors.push({ name: 'Reserva de Emergência', status: 'poor', points: 0 });
    }

    // Fator 4: Fluxo de caixa
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

    let healthStatus = 'poor';
    if (score >= 80) healthStatus = 'excellent';
    else if (score >= 60) healthStatus = 'good';
    else if (score >= 40) healthStatus = 'fair';

    return {
      score,
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