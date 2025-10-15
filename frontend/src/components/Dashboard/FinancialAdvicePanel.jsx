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
    mediumTerm: false,
    longTerm: false,
    goals: false
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Função para processar alertas (strings ou array)
  const processAlerts = (alerts) => {
    if (typeof alerts === 'string') {
      return [{ title: 'Alerta', message: alerts }];
    }
    if (Array.isArray(alerts)) {
      return alerts.map((alert, index) => {
        if (typeof alert === 'string') {
          return { title: `Alerta ${index + 1}`, message: alert };
        }
        return alert;
      });
    }
    return [];
  };

  // Função para processar metas mensuráveis (objeto ou array)
  const processMeasurableGoals = (goals) => {
    if (!goals) return [];
    
    if (typeof goals === 'object' && !Array.isArray(goals)) {
      // Se for objeto, converter para array de objetivos
      return Object.entries(goals).map(([key, value]) => ({
        title: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        description: value,
        target: 'Conforme descrito',
        timeframe: 'Conforme descrito'
      }));
    }
    
    if (Array.isArray(goals)) {
      return goals;
    }
    
    return [];
  };

  // Configuração de prioridades
  const getPriorityConfig = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'alta':
      case 'high':
      case 'critical':
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

  // Renderizar seção de recomendações
  const renderRecommendationSection = (recommendations, title, icon, color, badgeVariant, sectionKey) => {
    if (!recommendations || recommendations.length === 0) return null;

    const Icon = icon;
    
    return (
      <div className="border rounded-lg">
        <Button
          variant="ghost"
          className="w-full justify-between p-4"
          onClick={() => toggleSection(sectionKey)}
        >
          <div className="flex items-center space-x-2">
            <Icon className={`h-4 w-4 ${color}`} />
            <span className="font-medium">{title}</span>
            <Badge variant={badgeVariant} className="text-xs">
              {recommendations.length} ações
            </Badge>
          </div>
          {expandedSections[sectionKey] ? <ChevronUp /> : <ChevronDown />}
        </Button>
        
        {expandedSections[sectionKey] && (
          <div className="px-4 pb-4 space-y-3">
            {recommendations.map((rec, index) => {
              const config = getPriorityConfig(rec.impact || rec.priority);
              const IconItem = config.icon;
              
              return (
                <div key={index} className={`p-3 rounded-lg ${config.bg} ${config.border} border`}>
                  <div className="flex items-start space-x-3">
                    <IconItem className={`h-4 w-4 mt-0.5 ${config.color}`} />
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
                      {rec?.effort && (
                        <div className="text-xs text-gray-500 mt-1">
                          <strong>Esforço necessário:</strong> {rec.effort}
                        </div>
                      )}
                    </div>
                    <Badge variant={config.badge} className="text-xs">
                      {rec?.impact || rec?.priority || 'Média'}
                    </Badge>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Score de Saúde Financeira */}
      {advice?.overallAssessment?.health_score && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-blue-500" />
              <span>Score de Saúde Financeira</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-4">
              <div className="text-3xl font-bold text-blue-600">
                {advice.overallAssessment.health_score.toFixed(1)}/10
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-600">Prioridade:</div>
                <Badge 
                  variant={advice.overallAssessment.priority_level === 'high' ? 'destructive' : 'default'}
                  className="text-xs"
                >
                  {advice.overallAssessment.priority_level}
                </Badge>
              </div>
            </div>
            
            {/* Principais preocupações */}
            {advice.overallAssessment.main_concerns && advice.overallAssessment.main_concerns.length > 0 && (
              <div className="mb-4">
                <h4 className="font-medium text-gray-800 mb-2">Principais Preocupações:</h4>
                <div className="space-y-1">
                  {advice.overallAssessment.main_concerns.map((concern, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                      <span className="text-sm text-gray-700">{concern}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Principais pontos fortes */}
            {advice.overallAssessment.main_strengths && advice.overallAssessment.main_strengths.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-800 mb-2">Pontos Fortes:</h4>
                <div className="space-y-1">
                  {advice.overallAssessment.main_strengths.map((strength, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm text-gray-700">{strength}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Resumo da Análise */}
      {advice?.summary && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Lightbulb className="h-5 w-5 text-yellow-500" />
              <span>Resumo da Análise</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm max-w-none">
              <p className="text-gray-700 leading-relaxed">
                {advice.summary}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Alertas Críticos */}
      {advice?.alerts && processAlerts(advice.alerts).length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-red-700">
              <AlertTriangle className="h-5 w-5" />
              <span>Alertas Importantes</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {processAlerts(advice.alerts).map((alert, index) => (
              <Alert key={index} className="border-red-200 bg-white">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  <strong>{alert?.title || 'Alerta'}:</strong> {alert?.message || alert}
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
          {renderRecommendationSection(
            advice?.recommendations?.immediate, 
            'Ações Imediatas', 
            AlertTriangle, 
            'text-red-600', 
            'destructive', 
            'immediate'
          )}

          {/* Curto Prazo */}
          {renderRecommendationSection(
            advice?.recommendations?.short_term, 
            'Curto Prazo (1-6 meses)', 
            Clock, 
            'text-orange-600', 
            'warning', 
            'shortTerm'
          )}

          {/* Médio Prazo */}
          {renderRecommendationSection(
            advice?.recommendations?.medium_term, 
            'Médio Prazo (6-12 meses)', 
            Target, 
            'text-blue-600', 
            'default', 
            'mediumTerm'
          )}

          {/* Longo Prazo */}
          {renderRecommendationSection(
            advice?.recommendations?.long_term, 
            'Longo Prazo (12+ meses)', 
            TrendingUp, 
            'text-green-600', 
            'success', 
            'longTerm'
          )}
        </CardContent>
      </Card>

      {/* Metas Mensuráveis */}
      {advice?.measurableGoals && processMeasurableGoals(advice.measurableGoals).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Target className="h-5 w-5 text-purple-500" />
              <span>Metas Mensuráveis</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {processMeasurableGoals(advice.measurableGoals).map((goal, index) => (
                <div key={index} className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                  <div className="font-medium text-purple-800 mb-1">
                    {goal?.title || goal?.goal || 'Meta não especificada'}
                  </div>
                  <div className="text-sm text-purple-600 mb-2">
                    {goal?.description || goal?.target || 'Descrição não disponível'}
                  </div>
                  {goal?.timeframe && (
                    <div className="text-xs text-purple-500 mt-1">
                      <strong>Prazo:</strong> {goal.timeframe}
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