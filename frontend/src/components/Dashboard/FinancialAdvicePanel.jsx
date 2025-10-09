import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Alert, AlertDescription } from '../ui/alert';
import { 
  Lightbulb, 
  Target, 
  Clock, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

const FinancialAdvicePanel = ({ advice }) => {
  const [expandedSections, setExpandedSections] = useState({
    immediate: true,
    shortTerm: false,
    longTerm: false,
    goals: false
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Configuração de prioridades
  const getPriorityConfig = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'alta':
      case 'high':
        return {
          color: 'text-red-600',
          bg: 'bg-red-50',
          border: 'border-red-200',
          badge: 'destructive',
          icon: AlertTriangle
        };
      case 'média':
      case 'medium':
        return {
          color: 'text-yellow-600',
          bg: 'bg-yellow-50',
          border: 'border-yellow-200',
          badge: 'warning',
          icon: Clock
        };
      case 'baixa':
      case 'low':
        return {
          color: 'text-green-600',
          bg: 'bg-green-50',
          border: 'border-green-200',
          badge: 'success',
          icon: CheckCircle
        };
      default:
        return {
          color: 'text-blue-600',
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          badge: 'default',
          icon: Lightbulb
        };
    }
  };

  // Configuração de timeline
  const getTimelineConfig = (timeline) => {
    switch (timeline?.toLowerCase()) {
      case 'imediato':
      case 'immediate':
        return { label: 'Imediato', color: 'text-red-600', icon: AlertTriangle };
      case 'curto prazo':
      case 'short_term':
        return { label: 'Curto Prazo', color: 'text-orange-600', icon: Clock };
      case 'longo prazo':
      case 'long_term':
        return { label: 'Longo Prazo', color: 'text-green-600', icon: TrendingUp };
      default:
        return { label: 'Geral', color: 'text-blue-600', icon: Target };
    }
  };

  return (
    <div className="space-y-6">
      {/* Avaliação Geral */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Lightbulb className="h-5 w-5 text-yellow-500" />
            <span>Avaliação Financeira</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="prose prose-sm max-w-none">
            <p className="text-gray-700 leading-relaxed">
              {advice?.overallAssessment || 'Análise financeira não disponível. Execute uma análise para ver recomendações personalizadas.'}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Alertas Críticos */}
      {advice?.alerts && advice.alerts.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-red-700">
              <AlertTriangle className="h-5 w-5" />
              <span>Alertas Importantes</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {advice.alerts.map((alert, index) => (
              <Alert key={index} className="border-red-200 bg-white">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  <strong>{alert?.title || 'Alerta'}:</strong> {alert?.message || 'Alerta sem detalhes'}
                </AlertDescription>
              </Alert>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Recomendações por Timeline */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Target className="h-5 w-5 text-blue-500" />
            <span>Plano de Ação</span>
          </CardTitle>
          <CardDescription>
            Recomendações organizadas por prioridade e prazo
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          
          {/* Ações Imediatas */}
          {advice?.recommendations?.immediate && advice.recommendations.immediate.length > 0 && (
            <div className="border rounded-lg">
              <Button
                variant="ghost"
                className="w-full justify-between p-4"
                onClick={() => toggleSection('immediate')}
              >
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                  <span className="font-medium">Ações Imediatas</span>
                  <Badge variant="destructive" className="text-xs">
                    {advice.recommendations.immediate.length} ações
                  </Badge>
                </div>
                {expandedSections.immediate ? <ChevronUp /> : <ChevronDown />}
              </Button>
              
              {expandedSections.immediate && (
                <div className="px-4 pb-4 space-y-3">
                  {advice.recommendations.immediate.map((rec, index) => {
                    const config = getPriorityConfig(rec.priority);
                    const Icon = config.icon;
                    
                    return (
                      <div key={index} className={`p-3 rounded-lg ${config.bg} ${config.border} border`}>
                        <div className="flex items-start space-x-3">
                          <Icon className={`h-4 w-4 mt-0.5 ${config.color}`} />
                          <div className="flex-1">
                            <div className="font-medium text-gray-800 mb-1">
                              {rec?.title || rec?.action || 'Ação recomendada'}
                            </div>
                            <p className="text-sm text-gray-600 mb-2">
                              {rec?.description || rec?.rationale || 'Descrição não disponível'}
                            </p>
                            {rec?.expected_outcome && (
                              <div className="text-xs text-gray-500">
                                <strong>Resultado esperado:</strong> {rec.expected_outcome}
                              </div>
                            )}
                          </div>
                          <Badge variant={config.badge} className="text-xs">
                            {rec?.priority || 'Alta'}
                          </Badge>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Curto Prazo */}
          {advice?.recommendations?.short_term && advice.recommendations.short_term.length > 0 && (
            <div className="border rounded-lg">
              <Button
                variant="ghost"
                className="w-full justify-between p-4"
                onClick={() => toggleSection('shortTerm')}
              >
                <div className="flex items-center space-x-2">
                  <Clock className="h-4 w-4 text-orange-600" />
                  <span className="font-medium">Curto Prazo (1-6 meses)</span>
                  <Badge variant="warning" className="text-xs">
                    {advice.recommendations.short_term.length} ações
                  </Badge>
                </div>
                {expandedSections.shortTerm ? <ChevronUp /> : <ChevronDown />}
              </Button>
              
              {expandedSections.shortTerm && (
                <div className="px-4 pb-4 space-y-3">
                  {advice.recommendations.short_term.map((rec, index) => {
                    const config = getPriorityConfig(rec?.priority);
                    const Icon = config.icon;
                    
                    return (
                      <div key={index} className={`p-3 rounded-lg ${config.bg} ${config.border} border`}>
                        <div className="flex items-start space-x-3">
                          <Icon className={`h-4 w-4 mt-0.5 ${config.color}`} />
                          <div className="flex-1">
                            <div className="font-medium text-gray-800 mb-1">
                              {rec?.title || rec?.action || 'Ação recomendada'}
                            </div>
                            <p className="text-sm text-gray-600 mb-2">
                              {rec?.description || rec?.rationale || 'Descrição não disponível'}
                            </p>
                            {rec?.expected_outcome && (
                              <div className="text-xs text-gray-500">
                                <strong>Resultado esperado:</strong> {rec.expected_outcome}
                              </div>
                            )}
                          </div>
                          <Badge variant={config.badge} className="text-xs">
                            {rec?.priority || 'Média'}
                          </Badge>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Longo Prazo */}
          {advice?.recommendations?.long_term && advice.recommendations.long_term.length > 0 && (
            <div className="border rounded-lg">
              <Button
                variant="ghost"
                className="w-full justify-between p-4"
                onClick={() => toggleSection('longTerm')}
              >
                <div className="flex items-center space-x-2">
                  <TrendingUp className="h-4 w-4 text-green-600" />
                  <span className="font-medium">Longo Prazo (6+ meses)</span>
                  <Badge variant="success" className="text-xs">
                    {advice.recommendations.long_term.length} ações
                  </Badge>
                </div>
                {expandedSections.longTerm ? <ChevronUp /> : <ChevronDown />}
              </Button>
              
              {expandedSections.longTerm && (
                <div className="px-4 pb-4 space-y-3">
                  {advice.recommendations.long_term.map((rec, index) => {
                    const config = getPriorityConfig(rec?.priority);
                    const Icon = config.icon;
                    
                    return (
                      <div key={index} className={`p-3 rounded-lg ${config.bg} ${config.border} border`}>
                        <div className="flex items-start space-x-3">
                          <Icon className={`h-4 w-4 mt-0.5 ${config.color}`} />
                          <div className="flex-1">
                            <div className="font-medium text-gray-800 mb-1">
                              {rec?.title || rec?.action || 'Ação recomendada'}
                            </div>
                            <p className="text-sm text-gray-600 mb-2">
                              {rec?.description || rec?.rationale || 'Descrição não disponível'}
                            </p>
                            {rec?.expected_outcome && (
                              <div className="text-xs text-gray-500">
                                <strong>Resultado esperado:</strong> {rec.expected_outcome}
                              </div>
                            )}
                          </div>
                          <Badge variant={config.badge} className="text-xs">
                            {rec?.priority || 'Baixa'}
                          </Badge>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Metas Mensuráveis */}
      {advice?.measurableGoals && advice.measurableGoals.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Target className="h-5 w-5 text-purple-500" />
              <span>Metas Mensuráveis</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {advice.measurableGoals.map((goal, index) => (
                <div key={index} className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                  <div className="font-medium text-purple-800 mb-1">
                    {goal?.goal || goal?.title || 'Meta não especificada'}
                  </div>
                  <div className="text-sm text-purple-600 mb-2">
                    <strong>Meta:</strong> {goal?.target_value || goal?.target || 'Valor não especificado'}
                  </div>
                  <div className="text-sm text-purple-600">
                    <strong>Prazo:</strong> {goal?.timeframe || goal?.deadline || 'Prazo não definido'}
                  </div>
                  {goal?.current_status && (
                    <div className="text-xs text-purple-500 mt-1">
                      Status atual: {goal.current_status}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default FinancialAdvicePanel;