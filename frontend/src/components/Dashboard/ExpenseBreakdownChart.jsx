import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { financialDashboardService } from '../../services/financialDashboardService';

const ExpenseBreakdownChart = ({ data, chartConfig }) => {
  // Cores para o gráfico
  const COLORS = [
    '#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00ff00',
    '#ff00ff', '#00ffff', '#ff0000', '#0000ff', '#ffff00',
    '#800080', '#ffa500', '#a52a2a', '#808080', '#000080'
  ];

  // Preparar dados para o gráfico baseado na nova estrutura
  let chartData = [];

  // Verificar se os dados estão na nova estrutura (categories_breakdown)
  if (Array.isArray(data) && data.length > 0) {
    // Nova estrutura: array de objetos com category, amount, etc.
    chartData = data
      .filter(item => item.amount < 0) // Apenas gastos (valores negativos)
      .map((item, index) => ({
        name: item.category || 'Categoria não especificada',
        value: Math.abs(item.amount), // Usar valor absoluto para o gráfico
        originalValue: item.amount,
        color: item.color || COLORS[index % COLORS.length],
        percentage: item.percentage || 0,
        transaction_count: item.transaction_count || 0,
        icon: item.icon || 'circle'
      }));
  } else if (typeof data === 'object' && data !== null) {
    // Estrutura antiga: objeto com categorias como chaves
    chartData = Object.entries(data).map(([category, amount], index) => ({
      name: category,
      value: Math.abs(amount), // Usar valor absoluto para o gráfico
      originalValue: amount,
      color: COLORS[index % COLORS.length],
      percentage: 0, // Será calculado abaixo
      transaction_count: 0,
      icon: 'circle'
    }));
  }

  // Se não há dados, mostrar estado vazio
  if (chartData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Distribuição de Gastos por Categoria</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="text-gray-500">
              Nenhum dado de gastos disponível para análise
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Calcular total e porcentagens se não foram fornecidas
  const total = chartData.reduce((sum, item) => sum + item.value, 0);
  chartData.forEach(item => {
    if (!item.percentage) {
      item.percentage = ((item.value / total) * 100).toFixed(2);
    }
  });

  // Ordenar por valor (maiores primeiro)
  chartData.sort((a, b) => b.value - a.value);

  // Componente customizado para tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const percentage = ((data.value / total) * 100).toFixed(2);
      return (
        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
          <p className="font-semibold text-gray-800">{data.name}</p>
          <p className="text-blue-600">
            Valor: {financialDashboardService.formatCurrency(data.originalValue)}
          </p>
          <p className="text-gray-600">
            Porcentagem: {percentage}%
          </p>
          {data.transaction_count > 0 && (
            <p className="text-gray-500 text-sm">
              {data.transaction_count} {data.transaction_count === 1 ? 'transação' : 'transações'}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  // Componente customizado para legenda
  const CustomLegend = ({ payload }) => {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-4">
        {payload.map((entry, index) => {
          const item = chartData.find(item => item.name === entry.value);
          const percentage = item ? ((item.value / total) * 100).toFixed(2) : '0.00';
          return (
            <div key={index} className="flex items-center space-x-2 text-sm">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-gray-700 truncate">{entry.value}</span>
              <span className="text-gray-500 text-xs ml-auto">
                {percentage}%
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <span>Distribuição de Gastos por Categoria</span>
        </CardTitle>
        <CardDescription>
          Análise dos seus gastos organizados por categoria
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Gráfico de pizza */}
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ value, name }) => {
                    const percentage = ((value / total) * 100).toFixed(2);
                    return `${percentage}%`;
                  }}
                  outerRadius={90}
                  innerRadius={30}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Lista detalhada */}
          <div className="space-y-3">
            <h4 className="font-semibold text-gray-800 mb-3">Detalhamento por Categoria</h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {chartData.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <div>
                      <span className="text-sm font-medium text-gray-700">
                        {item.name}
                      </span>
                      {item.transaction_count > 0 && (
                        <div className="text-xs text-gray-500">
                          {item.transaction_count} {item.transaction_count === 1 ? 'transação' : 'transações'}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-gray-800">
                      {financialDashboardService.formatCurrency(item.originalValue)}
                    </div>
                    <div className="text-xs text-gray-500">
                      {((item.value / total) * 100).toFixed(2)}% do total
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Resumo estatístico */}
        <div className="mt-6 pt-4 border-t">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-lg font-bold text-blue-600">
                {chartData.length}
              </div>
              <div className="text-xs text-gray-600">Categorias</div>
            </div>
            <div>
              <div className="text-lg font-bold text-green-600">
                {financialDashboardService.formatCurrency(total)}
              </div>
              <div className="text-xs text-gray-600">Total de Gastos</div>
            </div>
            <div>
              <div className="text-lg font-bold text-purple-600">
                {financialDashboardService.formatCurrency(total / chartData.length)}
              </div>
              <div className="text-xs text-gray-600">Média por Categoria</div>
            </div>
          </div>
        </div>

        {/* Top 3 categorias */}
        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
          <h5 className="font-semibold text-blue-800 mb-2">Top 3 Categorias de Gastos</h5>
          <div className="space-y-1">
            {chartData.slice(0, 3).map((item, index) => (
              <div key={index} className="flex justify-between text-sm">
                <span className="text-blue-700">
                  {index + 1}. {item.name}
                </span>
                <span className="font-medium text-blue-800">
                  {((item.value / total) * 100).toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default ExpenseBreakdownChart;