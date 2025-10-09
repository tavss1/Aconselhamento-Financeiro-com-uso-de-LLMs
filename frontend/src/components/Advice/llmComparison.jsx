import React from 'react';
import { FileText } from 'lucide-react';

export const LLMComparison = ({ llmComparison }) => {
  if (!llmComparison?.responses) {
    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-xl shadow-md">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">
            Comparação de Modelos LLM
          </h2>
          <div className="text-center py-12">
            <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 text-lg">
              Execute uma análise financeira para ver a comparação entre LLMs
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl shadow-md">
        <h2 className="text-2xl font-semibold text-gray-800 mb-6">
          Comparação de Modelos LLM
        </h2>

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
                      index === 0 ? 'bg-yellow-500' : 
                      index === 1 ? 'bg-gray-400' : 
                      index === 2 ? 'bg-orange-500' : 'bg-gray-300'
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
                
                <div className="text-gray-700 text-sm line-clamp-3">
                  {response.error ? (
                    <span className="text-red-600">Erro: {response.error}</span>
                  ) : (
                    typeof response.advice === 'object' 
                      ? JSON.stringify(response.advice, null, 2).substring(0, 200) + '...'
                      : response.advice.substring(0, 200) + '...'
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};