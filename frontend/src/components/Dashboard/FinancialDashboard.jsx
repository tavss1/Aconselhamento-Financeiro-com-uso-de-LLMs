import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Alert, AlertDescription } from '../ui/alert';
import { Loader2, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, ArrowLeft, Home } from 'lucide-react';
import { financialDashboardService } from '../../services/financialDashboardService';
import ExpenseBreakdownChart from './ExpenseBreakdownChart';
import FinancialHealthCard from './FinancialHealthCard';
import TransactionsList from './TransactionsList';
import FinancialAdvicePanel from './FinancialAdvicePanel';

const FinancialDashboard = ({ onBackToHome }) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // Carregar dados do dashboard
  const loadDashboardData = async () => {
    try {
      setError(null);
      const data = await financialDashboardService.getDashboardData();
      setDashboardData(data);
    } catch (err) {
      console.error('Erro ao carregar dashboard:', err);
      setError(err.message || 'Erro ao carregar dados do dashboard');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Atualizar dados
  const handleRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData();
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  // Renderizar loading
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Carregando seu dashboard financeiro...</p>
        </div>
      </div>
    );
  }

  // Renderizar erro
  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Alert className="border-red-200 bg-red-50">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {error}
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              className="ml-3"
              disabled={refreshing}
            >
              {refreshing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Tentando novamente...
                </>
              ) : (
                'Tentar novamente'
              )}
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Nenhum dado disponível. Certifique-se de ter preenchido seu perfil financeiro e enviado um extrato.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const { profile, transactions, advice, charts, alerts, metadata } = dashboardData;

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Botão de Navegação */}
      {onBackToHome && (
        <div className="mb-6">
          <button
            onClick={onBackToHome}
            className="flex items-center text-blue-600 hover:text-blue-800 px-4 py-2 rounded-lg hover:bg-blue-50 transition-colors font-medium"
          >
            <ArrowLeft className="h-5 w-5 mr-2" />
            Voltar para Configurações
          </button>
        </div>
      )}

      {/* Header com informações do usuário */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard Financeiro</h1>
          <p className="text-gray-600 mt-1">
            Análise gerada em {new Date(metadata.generatedAt).toLocaleDateString('pt-BR')}
          </p>
        </div>
        <Button
          onClick={handleRefresh}
          disabled={refreshing}
          variant="outline"
        >
          {refreshing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Atualizando...
            </>
          ) : (
            'Atualizar Dados'
          )}
        </Button>
      </div>

      {/* Alertas importantes */}
      {alerts && alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert, index) => (
            <Alert
              key={index}
              className={`${
                alert.severity === 'high'
                  ? 'border-red-200 bg-red-50'
                  : alert.severity === 'medium'
                  ? 'border-yellow-200 bg-yellow-50'
                  : 'border-blue-200 bg-blue-50'
              }`}
            >
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>{alert.title}:</strong> {alert.message}
              </AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* Cards de métricas principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Renda Mensal */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Renda Mensal</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {financialDashboardService.formatCurrency(profile.monthlyIncome)}
            </div>
          </CardContent>
        </Card>

        {/* Gastos Mensais */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Gastos Mensais</CardTitle>
            <TrendingDown className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {financialDashboardService.formatCurrency(profile.monthlyExpenses)}
            </div>
          </CardContent>
        </Card>

        {/* Capacidade de Poupança */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Capacidade Poupança</CardTitle>
            <CheckCircle className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {financialDashboardService.formatCurrency(profile.savingsCapacity)}
            </div>
            <p className="text-xs text-gray-600 mt-1">
              {financialDashboardService.formatPercentage(profile.savingsRate)} da renda
            </p>
          </CardContent>
        </Card>

        {/* Fluxo de Caixa */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Fluxo de Caixa</CardTitle>
            {transactions.summary.net_flow >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-600" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              transactions.summary.net_flow >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {financialDashboardService.formatCurrency(transactions.summary.net_flow)}
            </div>
            <p className="text-xs text-gray-600 mt-1">
              {transactions.summary.total_transactions} transações analisadas
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Grade principal */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Coluna esquerda - Gráficos e análises */}
        <div className="lg:col-span-2 space-y-6">
          {/* Saúde Financeira */}
          <FinancialHealthCard dashboardData={dashboardData} />

          {/* Breakdown de gastos */}
          <ExpenseBreakdownChart
            data={transactions.categoriesBreakdown}
            chartConfig={charts.expensePieChart}
          />

          {/* Lista de transações */}
          <TransactionsList
            transactions={transactions.topTransactions}
            summary={transactions.summary}
          />
        </div>

        {/* Coluna direita - Conselhos e alertas */}
        <div className="space-y-6">
          <FinancialAdvicePanel advice={advice} />
        </div>
      </div>

      {/* Footer com metadata */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle className="text-sm">Informações da Análise</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-gray-600">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <strong>Pontos de dados:</strong> {metadata.totalDataPoints}
            </div>
            <div>
              <strong>Modelo LLM:</strong> {metadata.llmModel || 'N/A'}
            </div>
            <div>
              <strong>Última atualização:</strong>{' '}
              {new Date(metadata.generatedAt).toLocaleString('pt-BR')}
            </div>
            <div>
              <strong>Perfil de risco:</strong> {profile.riskProfile}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default FinancialDashboard;