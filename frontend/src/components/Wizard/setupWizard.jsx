import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { dashboardService } from '../../services/dashboardService';
import { FinancialQuestionnaire } from '../Questionario/financialQuestionnaire';
import { ExtractUpload } from '../Upload/extractUpload';
import { SimpleDashboard } from '../Dashboard/simpleDashboard';

export const SetupWizard = ({ onComplete, onViewDashboard, onBackToWizard }) => {
  const [currentStep, setCurrentStep] = useState('questionnaire');
  const [questionnaireData, setQuestionnaireData] = useState(null);
  const [extractData, setExtractData] = useState(null);
  const [error, setError] = useState(null);
  const [showDashboardOption, setShowDashboardOption] = useState(false);
  const { token, user, isAuthenticated } = useAuth();

  // Verificar se usuário já possui análise ao carregar o wizard
  useEffect(() => {
    checkForExistingAnalysis();
  }, []);

  const checkForExistingAnalysis = async () => {
    try {
      const analysisStatus = await dashboardService.checkAnalysisStatus();
      if (analysisStatus.has_analysis) {
        setShowDashboardOption(true);
      }
    } catch (error) {
      console.error('Erro ao verificar análise existente:', error);
    }
  };

  const handleQuestionnaireComplete = async (data) => {
    try {
      console.log('=== SetupWizard - handleQuestionnaireComplete ===');
      console.log('Dados recebidos do questionário:', data);
      console.log('Tipo dos dados:', typeof data);
      console.log('É um objeto?', typeof data === 'object' && data !== null);
      console.log('Dados como JSON string:', JSON.stringify(data, null, 2));
      console.log('Token disponível:', !!token);
      console.log('Usuário autenticado:', isAuthenticated());
      console.log('Usuário:', user);

      // Verificar se o usuário está autenticado
      if (!isAuthenticated() || !token) {
        throw new Error('Usuário não está autenticado. Faça login novamente.');
      }

      // Verificar se dashboardService está disponível
      if (!dashboardService) {
        throw new Error('DashboardService não está disponível');
      }

      setError(null); // Limpar erros anteriores

      const response = await dashboardService.saveFinancialProfile(data);

      console.log('Perfil salvo com sucesso:', response);

      // Salvar dados do questionário no estado para uso posterior
      setQuestionnaireData(data);
      setCurrentStep('upload');

    } catch (error) {
      console.error('Erro ao salvar perfil:', error);

      // Extrair mensagem de erro mais específica
      let errorMessage = 'Erro desconhecido ao salvar perfil';

      if (error.message && error.message !== '[object Object]') {
        errorMessage = error.message;
      } else if (error.detail) {
        errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail);
      }

      setError(`Erro ao salvar perfil: ${errorMessage}`);
    }
  };

  const handleUploadComplete = (uploadData) => {
    console.log('Upload concluído:', uploadData);

    // Salvar dados do extrato
    setExtractData(uploadData);
    setCurrentStep('dashboard');
  };

  // Mostrar erro se houver
  if (error) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-red-800 font-medium">Erro</h3>
          <p className="text-red-700 mt-1 text-sm">{error}</p>
          <div className="mt-3 space-x-2">
            <button
              onClick={() => setError(null)}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Tentar Novamente
            </button>
            <button
              onClick={() => {
                setError(null);
                setCurrentStep('questionnaire');
              }}
              className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Voltar ao Questionário
            </button>
          </div>

          {/* Informações de debug */}
          <details className="mt-3">
            <summary className="text-xs text-red-600 cursor-pointer">Detalhes técnicos</summary>
            <pre className="text-xs bg-red-100 p-2 mt-2 rounded overflow-auto">
              {JSON.stringify({ currentStep, questionnaireData, token: !!token }, null, 2)}
            </pre>
          </details>
        </div>
      </div>
    );
  }

  switch (currentStep) {
    case 'questionnaire':
      return (
        <div>
          {/* Banner para usuários com análise existente */}
          {showDashboardOption && (
            <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <svg className="h-5 w-5 text-blue-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <p className="text-sm font-medium text-blue-800">
                      Você já possui uma análise financeira concluída!
                    </p>
                    <p className="text-xs text-blue-600">
                      Você pode ir diretamente para o dashboard ou atualizar seus dados aqui.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => onViewDashboard && onViewDashboard()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
                >
                  Ver Dashboard
                </button>
              </div>
            </div>
          )}
          
          <FinancialQuestionnaire onComplete={handleQuestionnaireComplete} />
        </div>
      );

    case 'upload':
      return (
        <ExtractUpload
          onUploadComplete={handleUploadComplete}
          questionnaireData={questionnaireData} // Passar dados do questionário se necessário
        />
      );

    case 'dashboard':
      return (
        <div className="space-y-6">
          <SimpleDashboard
            questionnaireData={questionnaireData}
            extractData={extractData}
            onAnalysisComplete={() => {
              console.log('✅ Pipeline de aconselhamento concluída, redirecionando para dashboard...');
              if (onViewDashboard) {
                onViewDashboard();
              }
            }}
            onBackToHome={() => {
              console.log('🏠 Voltando para tela inicial...');
              if (onBackToWizard) {
                onBackToWizard();
              } else {
                setCurrentStep('questionnaire');
              }
            }}
          />
          
          {/* Botões de ação após configuração inicial */}
          <div className="flex justify-center space-x-4 mt-8 p-6 bg-gray-50 rounded-lg">
            <button
              onClick={() => onViewDashboard && onViewDashboard()}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Ver Dashboard Completo
            </button>
            <button
              onClick={() => setCurrentStep('questionnaire')}
              className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
            >
              Editar Perfil
            </button>
            <button
              onClick={() => setCurrentStep('upload')}
              className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
            >
              Enviar Novo Extrato
            </button>
          </div>
        </div>
      );

    default:
      return <SimpleDashboard onBackToHome={() => setCurrentStep('questionnaire')} />;
  }
};