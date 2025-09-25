import React from 'react';
import { Brain } from 'lucide-react';

export const RecentAdviceCard = ({ recentAdvice, onGenerateAdvice, generatingAdvice }) => {
  return (
    <div className="bg-white p-6 rounded-xl shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-800">
          Últimos Conselhos
        </h3>
        <button
          onClick={onGenerateAdvice}
          disabled={generatingAdvice}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center"
        >
          <Brain className="h-4 w-4 mr-2" />
          {generatingAdvice ? 'Gerando...' : 'Gerar Novo'}
        </button>
      </div>

      <div className="space-y-3">
        {recentAdvice?.slice(0, 3).map((advice, index) => (
          <div key={index} className="p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-700 line-clamp-2">
              {typeof advice.advice === 'string' 
                ? advice.advice 
                : advice.advice?.advice || 'Conselho não disponível'
              }
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
  );
};