import React from 'react';
import { Brain } from 'lucide-react';
import { LoadingSpinner } from '../common/LoadingSpinner';

export const AdvicePanel = ({ 
  llmComparison, 
  generatingAdvice, 
  onGenerateAdvice 
}) => {
  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl shadow-md">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-semibold text-gray-800">
            Conselhos Financeiros Personalizados
          </h2>
          <button
            onClick={onGenerateAdvice}
            disabled={generatingAdvice}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center"
          >
            <Brain className="h-5 w-5 mr-2" />
            {generatingAdvice ? 'Analisando...' : 'Gerar Conselhos'}
          </button>
        </div>

        {generatingAdvice && (
          <div className="text-center py-12">
            <LoadingSpinner 
              size="medium" 
              message="Nossa IA está analisando seus dados financeiros..."
            />
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
  );
};