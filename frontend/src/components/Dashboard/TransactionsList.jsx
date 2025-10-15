import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { ArrowUpDown, Calendar, DollarSign, Tag } from 'lucide-react';
import { financialDashboardService } from '../../services/financialDashboardService';

const TransactionsList = ({ transactions, summary }) => {
  const [sortBy, setSortBy] = useState('amount'); // 'amount', 'date', 'category'
  const [sortOrder, setSortOrder] = useState('desc'); // 'asc', 'desc'
  const [filterCategory, setFilterCategory] = useState('all');

  // Obter categorias únicas
  const categories = ['all', ...new Set(transactions.map(t => t.category))];

  // Filtrar e ordenar transações
  const processedTransactions = transactions
    .filter(transaction => 
      filterCategory === 'all' || transaction.category === filterCategory
    )
    .sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'amount':
          comparison = Math.abs(a.amount) - Math.abs(b.amount);
          break;
        case 'date':
          comparison = new Date(a.date) - new Date(b.date);
          break;
        case 'category':
          comparison = a.category.localeCompare(b.category);
          break;
        default:
          comparison = 0;
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  // Alternar ordenação
  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  // Obter cor do nível de impacto
  const getImpactColor = (impactLevel) => {
    switch (impactLevel?.toLowerCase()) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // Obter cor da categoria
  const getCategoryColor = (category) => {
    const colors = {
      'Alimentação': 'bg-orange-100 text-orange-800',
      'Transporte': 'bg-blue-100 text-blue-800',
      'Saúde': 'bg-green-100 text-green-800',
      'Entretenimento': 'bg-purple-100 text-purple-800',
      'Educação': 'bg-yellow-100 text-yellow-800',
      'Casa': 'bg-red-100 text-red-800',
      'Moradia': 'bg-red-100 text-red-800',
      'Compras': 'bg-pink-100 text-pink-800',
      'Mercado': 'bg-pink-100 text-pink-800',
      'Transferências': 'bg-gray-100 text-gray-800',
      'Renda': 'bg-emerald-100 text-emerald-800',
      'Serviços': 'bg-indigo-100 text-indigo-800',
      'Outros': 'bg-slate-100 text-slate-800'
    };
    
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <DollarSign className="h-5 w-5" />
          <span>Transações Principais</span>
        </CardTitle>
        <CardDescription>
          Suas transações mais relevantes organizadas e categorizadas
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        {/* Resumo das transações */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="text-center">
            <div className="text-lg font-bold text-blue-600">
              {summary.total_transactions}
            </div>
            <div className="text-xs text-gray-600">Total de Transações</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-green-600">
              {financialDashboardService.formatCurrency(summary.total_income)}
            </div>
            <div className="text-xs text-gray-600">Receitas</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-red-600">
              {financialDashboardService.formatCurrency(Math.abs(summary.total_expenses))}
            </div>
            <div className="text-xs text-gray-600">Despesas</div>
          </div>
        </div>

        {/* Controles de filtro e ordenação */}
        <div className="flex flex-wrap gap-3 mb-4 p-3 bg-white border rounded-lg">
          {/* Filtro por categoria */}
          <div className="flex items-center space-x-2">
            <Tag className="h-4 w-4 text-gray-500" />
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="all">Todas as categorias</option>
              {categories.slice(1).map(category => (
                <option key={category} value={category}>{category}</option>
              ))}
            </select>
          </div>

          {/* Botões de ordenação */}
          <div className="flex items-center space-x-2">
            <ArrowUpDown className="h-4 w-4 text-gray-500" />
            <Button
              variant={sortBy === 'amount' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleSort('amount')}
            >
              Valor {sortBy === 'amount' && (sortOrder === 'desc' ? '↓' : '↑')}
            </Button>
            <Button
              variant={sortBy === 'date' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleSort('date')}
            >
              Data {sortBy === 'date' && (sortOrder === 'desc' ? '↓' : '↑')}
            </Button>
            <Button
              variant={sortBy === 'category' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleSort('category')}
            >
              Categoria {sortBy === 'category' && (sortOrder === 'desc' ? '↓' : '↑')}
            </Button>
          </div>
        </div>

        {/* Lista de transações */}
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {processedTransactions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              Nenhuma transação encontrada com os filtros selecionados.
            </div>
          ) : (
            processedTransactions.map((transaction, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <div className="flex-1">
                      <div className="font-medium text-gray-900 text-sm">
                        {transaction.description || 'Transação sem descrição'}
                      </div>
                      <div className="flex items-center space-x-2 mt-1">
                        <Calendar className="h-3 w-3 text-gray-400" />
                        <span className="text-xs text-gray-500">
                          {transaction.date ? new Date(transaction.date.split('/').reverse().join('-')).toLocaleDateString('pt-BR') : 'Data não informada'}
                        </span>
                        <Badge className={`text-xs ${getCategoryColor(transaction.category)}`}>
                          {transaction.category || 'Sem categoria'}
                        </Badge>
                        {transaction.impact_level && (
                          <Badge className={`text-xs border ${getImpactColor(transaction.impact_level)}`}>
                            {transaction.impact_level}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="text-right">
                  <div className={`font-semibold ${
                    transaction.amount >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {transaction.amount >= 0 ? '+' : ''}
                    {financialDashboardService.formatCurrency(transaction.amount)}
                  </div>
                  {transaction.confidence && (
                    <div className="text-xs text-gray-500">
                      Confiança: {(transaction.confidence * 100).toFixed(0)}%
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer com estatísticas */}
        {processedTransactions.length > 0 && (
          <div className="mt-4 pt-3 border-t">
            <div className="flex justify-between text-sm text-gray-600">
              <span>
                Mostrando {processedTransactions.length} de {transactions.length} transações
              </span>
              <span>
                Valor total: {financialDashboardService.formatCurrency(
                  processedTransactions.reduce((sum, t) => sum + t.amount, 0)
                )}
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default TransactionsList;