import React, { useState } from 'react';
import { X, Brain, Check } from 'lucide-react';

const ModelSelectionModal = ({ isOpen, onClose, onConfirm, loading }) => {
  const [selectedModel, setSelectedModel] = useState('');

  // Lista de modelos disponíveis
  const availableModels = [
    {
      id: 'ollama/gemma3',
      name: 'Gemma 3 ',
      recommended: true
    },
    {
      id: 'ollama/llama2',
      name: 'Llama 2 ',
      recommended: false
    },
    {
      id: 'ollama/mistral',
      name: 'Mistral ',
      recommended: false
    },
  ];

  const handleConfirm = () => {
    if (selectedModel) {
      onConfirm(selectedModel);
      setSelectedModel('');
    }
  };

  const handleClose = () => {
    setSelectedModel('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <Brain className="h-6 w-6 text-blue-600" />
            <h2 className="text-xl font-semibold text-gray-900">
              Selecionar Modelo de IA
            </h2>
          </div>
          <button
            onClick={handleClose}
            disabled={loading}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <p className="text-gray-600 mb-4">
            Escolha o modelo de LLM para gerar seus conselhos financeiros:
          </p>

          <div className="space-y-3">
            {availableModels.map((model) => (
              <div
                key={model.id}
                className={`border rounded-lg p-3 cursor-pointer transition-all ${
                  selectedModel === model.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                onClick={() => !loading && setSelectedModel(model.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                      selectedModel === model.id
                        ? 'border-blue-500 bg-blue-500'
                        : 'border-gray-300'
                    }`}>
                      {selectedModel === model.id && (
                        <Check className="h-2.5 w-2.5 text-white" />
                      )}
                    </div>
                    
                    <span className="font-medium text-gray-900">
                      {model.name}
                    </span>
                  </div>
                  
                  {model.recommended && (
                    <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
                      Recomendado
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t bg-gray-50">
          <button
            onClick={handleClose}
            disabled={loading}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            disabled={!selectedModel || loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Gerando...
              </>
            ) : (
              <>
                <Brain className="h-4 w-4 mr-2" />
                Gerar Conselhos
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModelSelectionModal;