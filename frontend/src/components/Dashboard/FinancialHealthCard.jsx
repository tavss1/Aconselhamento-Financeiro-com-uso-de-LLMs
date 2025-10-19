import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Progress } from '../ui/progress';
import { Badge } from '../ui/badge';
import { Heart, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react';
import { financialDashboardService } from '../../services/financialDashboardService';

const FinancialHealthCard = ({ dashboardData }) => {
  const healthData = financialDashboardService.calculateFinancialHealth(dashboardData);
  
  // Configurações de cores e ícones baseadas no status
  const getHealthConfig = (status) => {
    switch (status) {
      case 'excellent':
        return {
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          icon: CheckCircle,
          label: 'Excelente',
          description: 'Sua saúde financeira está em ótimo estado!'
        };
      case 'good':
        return {
          color: 'text-blue-600',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          icon: TrendingUp,
          label: 'Boa',
          description: 'Você está no caminho certo, continue assim!'
        };
      case 'fair':
        return {
          color: 'text-yellow-600',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          icon: AlertCircle,
          label: 'Regular',
          description: 'Há espaço para melhorias em suas finanças.'
        };
      case 'poor':
        return {
          color: 'text-red-600',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          icon: AlertCircle,
          label: 'Precisa melhorar',
          description: 'Recomendamos atenção especial às suas finanças.'
        };
      default:
        return {
          color: 'text-gray-600',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          icon: Heart,
          label: 'Não avaliado',
          description: 'Dados insuficientes para avaliação.'
        };
    }
  };

  const getFactorConfig = (status) => {
    switch (status) {
      case 'excellent':
        return { color: 'text-green-600', bg: 'bg-green-100', badge: 'success' };
      case 'good':
        return { color: 'text-blue-600', bg: 'bg-blue-100', badge: 'default' };
      case 'fair':
        return { color: 'text-yellow-600', bg: 'bg-yellow-100', badge: 'warning' };
      case 'poor':
        return { color: 'text-red-600', bg: 'bg-red-100', badge: 'destructive' };
      default:
        return { color: 'text-gray-600', bg: 'bg-gray-100', badge: 'secondary' };
    }
  };

  const healthConfig = getHealthConfig(healthData.status);
  const HealthIcon = healthConfig.icon;

  return (
    <Card className={`${healthConfig.borderColor} ${healthConfig.bgColor}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <HealthIcon className={`h-5 w-5 ${healthConfig.color}`} />
            <CardTitle className="text-lg">Saúde Financeira</CardTitle>
          </div>
          <Badge variant={healthData.status === 'excellent' ? 'success' : 
                          healthData.status === 'good' ? 'default' :
                          healthData.status === 'fair' ? 'warning' : 'destructive'}>
            {healthConfig.label}
          </Badge>
        </div>
        <CardDescription>
          {healthConfig.description}
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Score geral */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">Pontuação Geral</span>
            <span className={`text-sm font-bold ${healthConfig.color}`}>
              {healthData.score}/{healthData.maxScore}
            </span>
          </div>
          <Progress 
            value={healthData.score} 
            max={healthData.maxScore}
            className="h-2"
          />
        </div>

        {/* Fatores individuais */}
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-gray-700">Fatores Avaliados</h4>
          
          {healthData.factors.map((factor, index) => {
            const factorConfig = getFactorConfig(factor.status);
            
            return (
              <div key={index} className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm">{factor.name}</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-500">
                      {factor.points}/25 pts
                    </span>
                    <Badge variant={factorConfig.badge} className="text-xs">
                      {factor.status === 'excellent' ? 'Excelente' :
                       factor.status === 'good' ? 'Bom' :
                       factor.status === 'fair' ? 'Regular' : 'Ruim'}
                    </Badge>
                  </div>
                </div>
                <Progress 
                  value={factor.points} 
                  max={25}
                  className="h-1"
                />
              </div>
            );
          })}
        </div>

        {/* Métricas específicas */}
        <div className="grid grid-cols-2 gap-4 pt-4 border-t">
          <div className="text-center">
            <div className="text-lg font-bold text-blue-600">
              {financialDashboardService.formatPercentage(dashboardData.profile.savingsRate)}
            </div>
            <div className="text-xs text-gray-600">Taxa de Poupança</div>
          </div>
          
          <div className="text-center">
            <div className="text-lg font-bold text-purple-600">
              {(() => {
                const debtRatio = dashboardData.profile.debtToIncome;
                console.log('🔍 debtToIncome value:', debtRatio, 'type:', typeof debtRatio);
                
                if (typeof debtRatio === 'number' && !isNaN(debtRatio)) {
                  // debtToIncome já vem como decimal (0.2 = 20%), então multiplicamos por 100
                  const result = financialDashboardService.formatPercentage(debtRatio * 100);
                  return result;
                }
                return '0,0%';
              })()}
            </div>
            <div className="text-xs text-gray-600">Endividamento</div>
          </div>
        </div>

        {/* Seção de reserva de emergência removida conforme solicitação */}
      </CardContent>
    </Card>
  );
};

export default FinancialHealthCard;