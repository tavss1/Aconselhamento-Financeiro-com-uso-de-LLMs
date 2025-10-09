import React, { useState, useEffect } from 'react';
import { DollarSign, TrendingUp, LogOut, Brain, FileText } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { useAuth } from '../../context/AuthContext';
import { dashboardService } from '../../services/dashboardService';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

const NAVIGATION_TABS = [
  { id: 'overview', label: 'Visão Geral', icon: TrendingUp },
  { id: 'advice', label: 'Conselhos IA', icon: Brain },
  { id: 'comparison', label: 'Comparação LLMs', icon: FileText }
];

export const SimpleDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [llmComparison, setLlmComparison] = useState(null);
  const [generatingAdvice, setGeneratingAdvice] = useState(false);
  const { token, user, logout } = useAuth();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const data = await dashboardService.getFinancialReports(token);
      setDashboardData(data);
    } catch (error) {
      console.error('Erro ao carregar dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateFinancialAdvice = async () => {
    setGeneratingAdvice(true);
    try {
      const result = await dashboardService.generateFinancialAdvice(token);
      setLlmComparison(result);
      fetchDashboardData();
    } catch (error) {
      console.error('Erro:', error);
      alert('Erro ao gerar conselhos financeiros');
    } finally {
      setGeneratingAdvice(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <DollarSign className="h-8 w-8 text-blue-600 mr-3" />
              <h1 className="text-2xl font-bold text-gray-800">Aconselhamento Financeiro com uso de LLMs</h1>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-gray-600">Olá, {user?.name}</span>
              <button
                onClick={logout}
                className="flex items-center text-gray-500 hover:text-gray-700"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {NAVIGATION_TABS.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center px-1 py-4 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="h-5 w-5 mr-2" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Cards de Resumo */}
            {dashboardData?.financial_summary && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white p-6 rounded-xl shadow-md">
                  <div className="flex items-center">
                    <TrendingUp className="h-8 w-8 text-green-600" />
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Receitas</p>
                      <p className="text-2xl font-semibold text-gray-900">
                        R$ {dashboardData.financial_summary.total_income?.toLocaleString('pt-BR')}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-xl shadow-md">
                  <div className="flex items-center">
                    <TrendingUp className="h-8 w-8 text-red-600 rotate-180" />
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Gastos</p>
                      <p className="text-2xl font-semibold text-gray-900">
                        R$ {Math.abs(dashboardData.financial_summary.total_expenses)?.toLocaleString('pt-BR')}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-xl shadow-md">
                  <div className="flex items-center">
                    <DollarSign className="h-8 w-8 text-blue-600" />
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500">Saldo</p>
                      <p className={`text-2xl font-semibold ${
                        dashboardData.financial_summary.balance >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        R$ {dashboardData.financial_summary.balance?.toLocaleString('pt-BR')}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Gráficos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Gráfico de Categorias */}
              {dashboardData?.expense_categories && Object.keys(dashboardData.expense_categories).length > 0 && (
                <div className="bg-white p-6 rounded-xl shadow-md">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">
                    Gastos por Categoria
                  </h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={Object.entries(dashboardData.expense_categories).map(([key, value]) => ({
                          name: key,
                          value: Math.abs(value)
                        }))}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {Object.entries(dashboardData.expense_categories).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => `R$ ${value.toLocaleString('pt-BR')}`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Conselhos Recentes */}
              <div className="bg-white p-6 rounded-xl shadow-md">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-gray-800">
                    Últimos Conselhos
                  </h3>
                  <button
                    onClick={generateFinancialAdvice}
                    disabled={generatingAdvice}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center"
                  >
                    <Brain className="h-4 w-4 mr-2" />
                    {generatingAdvice ? 'Gerando...' : 'Gerar Novo'}
                  </button>
                </div>

                <div className="space-y-3">
                  {dashboardData?.recent_advice?.slice(0, 3).map((advice, index) => (
                    <div key={index} className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-700">
                        {typeof advice.advice === 'string' ? advice.advice : advice.advice?.advice || 'Conselho não disponível'}
                      </p>
                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(advice.created_at).toLocaleDateString('pt-BR')}
                      </p>
                    </div>
                  )) || (
                    <p className="text-gray-500 text-center py-8">
                      Nenhum conselho gerado ainda. Clique em "Gerar Novo" para começar.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Advice Tab */}
        {activeTab === 'advice' && (
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-xl shadow-md">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-semibold text-gray-800">
                  Conselhos Financeiros Personalizados
                </h2>
                <button
                  onClick={generateFinancialAdvice}
                  disabled={generatingAdvice}
                  className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center"
                >
                  <Brain className="h-5 w-5 mr-2" />
                  {generatingAdvice ? 'Analisando...' : 'Gerar Conselhos'}
                </button>
              </div>

              {generatingAdvice && (
                <div className="text-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <p className="text-gray-600">
                    Nossa IA está analisando seus dados financeiros...
                  </p>
                </div>
              )}

              {llmComparison?.best_response && (
                <div className="space-y-4">
                  <div className="bg-green-50 border border-green-200 p-6 rounded-lg">
                    <h3 className="text-lg font-semibold text-green-800 mb-3">
                      Melhor Conselho - {llmComparison.best_response.llm_name}
                    </h3>
                    <div className="text-gray-700 whitespace-pre-line">
                      {typeof llmComparison.best_response.advice === 'object' 
                        ? JSON.stringify(llmComparison.best_response.advice, null, 2)
                        : llmComparison.best_response.advice
                      }
                    </div>
                    <div className="mt-4 flex items-center text-sm text-green-600">
                      <span className="mr-4">
                        Confiança: {(llmComparison.best_response.confidence_score * 100).toFixed(1)}%
                      </span>
                      <span>
                        Tempo: {llmComparison.best_response.processing_time.toFixed(2)}s
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {!llmComparison && !generatingAdvice && (
                <div className="text-center py-12">
                  <Brain className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500 text-lg">
                    Clique em "Gerar Conselhos" para receber análises personalizadas
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Comparison Tab */}
        {activeTab === 'comparison' && (
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-xl shadow-md">
              <h2 className="text-2xl font-semibold text-gray-800 mb-6">
                Comparação de Modelos LLM
              </h2>

              {llmComparison?.responses ? (
                <div className="space-y-6">
                  {/* Métricas Gerais */}
                  {llmComparison.metrics && (
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <h4 className="text-sm font-medium text-blue-800">Total de LLMs</h4>
                        <p className="text-2xl font-bold text-blue-900">
                          {llmComparison.metrics.total_llms_tested}
                        </p>
                      </div>
                      <div className="bg-green-50 p-4 rounded-lg">
                        <h4 className="text-sm font-medium text-green-800">Respostas Válidas</h4>
                        <p className="text-2xl font-bold text-green-900">
                          {llmComparison.metrics.valid_responses}
                        </p>
                      </div>
                      <div className="bg-yellow-50 p-4 rounded-lg">
                        <h4 className="text-sm font-medium text-yellow-800">Confiança Média</h4>
                        <p className="text-2xl font-bold text-yellow-900">
                          {(llmComparison.metrics.average_confidence * 100).toFixed(1)}%
                        </p>
                      </div>
                      <div className="bg-purple-50 p-4 rounded-lg">
                        <h4 className="text-sm font-medium text-purple-800">Tempo Médio</h4>
                        <p className="text-2xl font-bold text-purple-900">
                          {llmComparison.metrics.average_processing_time.toFixed(2)}s
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Ranking */}
                  {llmComparison.metrics?.llm_ranking && (
                    <div className="mb-8">
                      <h3 className="text-lg font-semibold text-gray-800 mb-4">Ranking dos LLMs</h3>
                      <div className="space-y-3">
                        {llmComparison.metrics.llm_ranking.map((llm, index) => (
                          <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                            <div className="flex items-center">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold mr-4 ${
                                index === 0 ? 'bg-yellow-500' : index === 1 ? 'bg-gray-400' : index === 2 ? 'bg-orange-500' : 'bg-gray-300'
                              }`}>
                                {llm.position}
                              </div>
                              <span className="font-medium">{llm.llm_name}</span>
                            </div>
                            <div className="flex items-center space-x-4">
                              <span className="text-sm text-gray-600">
                                Score: {(llm.composite_score * 100).toFixed(1)}%
                              </span>
                              <span className="text-sm text-gray-600">
                                Confiança: {(llm.confidence_score * 100).toFixed(1)}%
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Todas as Respostas */}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800 mb-4">Todas as Respostas</h3>
                    <div className="space-y-4">
                      {llmComparison.responses.map((response, index) => (
                        <div key={index} className={`p-4 rounded-lg border ${
                          response.llm_name === llmComparison.best_response?.llm_name 
                            ? 'border-green-300 bg-green-50' 
                            : 'border-gray-200 bg-white'
                        }`}>
                          <div className="flex justify-between items-start mb-3">
                            <h4 className="font-medium text-gray-800">
                              {response.llm_name}
                              {response.llm_name === llmComparison.best_response?.llm_name && (
                                <span className="ml-2 px-2 py-1 bg-green-200 text-green-800 text-xs rounded-full">
                                  Melhor
                                </span>
                              )}
                            </h4>
                            <div className="text-sm text-gray-500 space-x-4">
                              <span>Confiança: {(response.confidence_score * 100).toFixed(1)}%</span>
                              <span>Tempo: {response.processing_time.toFixed(2)}s</span>
                            </div>
                          </div>
                          
                          <div className="text-gray-700 text-sm">
                            {response.error ? (
                              <span className="text-red-600">Erro: {response.error}</span>
                            ) : (
                              <div className="max-h-32 overflow-hidden">
                                {typeof response.advice === 'object' 
                                  ? JSON.stringify(response.advice, null, 2).substring(0, 200) + '...'
                                  : response.advice.substring(0, 200) + (response.advice.length > 200 ? '...' : '')
                                }
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12">
                  <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500 text-lg">
                    Execute uma análise financeira para ver a comparação entre LLMs
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};