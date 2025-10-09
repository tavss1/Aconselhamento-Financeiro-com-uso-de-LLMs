import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { COLORS } from '../../utils/constants';

export const ExpenseChart = ({ expenseCategories }) => {
  if (!expenseCategories || Object.keys(expenseCategories).length === 0) {
    return null;
  }

  const data = Object.entries(expenseCategories).map(([key, value]) => ({
    name: key,
    value: Math.abs(value)
  }));

  return (
    <div className="bg-white p-6 rounded-xl shadow-md">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        Gastos por Categoria
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => `R$ ${value.toLocaleString('pt-BR')}`} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};