import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { dashboardService } from '../../services/dashboardService';
import { FinancialQuestionnaire } from '../Questionario/financialQuestionnaire';
import { ExtractUpload } from '../Upload/extractUpload';
import { SimpleDashboard } from '../Dashboard/simpleDashboard';

export const SetupWizard = () => {
  const [currentStep, setCurrentStep] = useState('questionnaire');
  const [questionnaireData, setQuestionnaireData] = useState(null);
  const [extractData, setExtractData] = useState(null);
  const [error, setError] = useState(null);
  const { token } = useAuth();

  const handleQuestionnaireComplete = async (data) => {
    try {
      console.log('=== SetupWizard - handleQuestionnaireComplete ===');
      console.log('Dados recebidos do questionário:', data);
      console.log('Tipo dos dados:', typeof data);
      console.log('É um objeto?', typeof data === 'object' && data !== null);
      console.log('Dados como JSON string:', JSON.stringify(data, null, 2));
      console.log('Token disponível:', !!token);

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
      return <FinancialQuestionnaire onComplete={handleQuestionnaireComplete} />;

    case 'upload':
      return (
        <ExtractUpload
          onUploadComplete={handleUploadComplete}
          questionnaireData={questionnaireData} // Passar dados do questionário se necessário
        />
      );

    case 'dashboard':
      return (
        <SimpleDashboard
          questionnaireData={questionnaireData}
          extractData={extractData}
        />
      );

    default:
      return <SimpleDashboard />;
  }
};