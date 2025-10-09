import React from 'react';
import { TrendingUp, DollarSign } from 'lucide-react';

export const FinancialSummaryCards = ({ financialSummary }) => {
  if (!financialSummary) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div className="bg-white p-6 rounded-xl shadow-md">
        <div className="flex items-center">
          <TrendingUp className="h-8 w-8 text-green-600" />
          <div className="ml-4">
            <p className="text-sm font-medium text-gray-500">Receitas</p>
            <p className="text-2xl font-semibold text-gray-900">
              R$ {financialSummary.total_income?.toLocaleString('pt-BR')}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-md">
        <div className="flex items-center">
          <TrendingUp className="h-8 w-8 text-red-600 rotate-180" />
          <div className="ml-4">
            <p className="text-sm font-medium text-gray-500">Gastos</p>
            <p className="text-2xl font-semibold text-gray-900">
              R$ {Math.abs(financialSummary.total_expenses)?.toLocaleString('pt-BR')}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-md">
        <div className="flex items-center">
          <DollarSign className="h-8 w-8 text-blue-600" />
          <div className="ml-4">
            <p className="text-sm font-medium text-gray-500">Saldo</p>
            <p className={`text-2xl font-semibold ${
              financialSummary.balance >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              R$ {financialSummary.balance?.toLocaleString('pt-BR')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};