import React, { useState } from 'react';
import { RISK_PROFILES, FINANCIAL_GOALS, MEIOS_TRANSPORTE, DEPENDENTES } from '../../utils/constants';

export const FinancialQuestionnaire = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [validationErrors, setValidationErrors] = useState({});
  const [formData, setFormData] = useState({
    age: '',
    monthly_income: '',
    risk_profile: '',
    transportation_methods: '',
    // Simplificado: apenas um campo para objetivo
    financial_goal: '',
    financial_goal_details: {
      target_amount: '',
      time_frame: ''
    },
    // Simplificado: apenas um array para dependentes com type e quantity
    dependents: []
  });

  const steps = [
    {
      title: 'Informações Pessoais',
      fields: [
        { name: 'age', label: 'Idade', type: 'number', required: true },
        { name: 'monthly_income', label: 'Renda Mensal (R$)', type: 'number', required: true }
      ]
    },
    {
      title: 'Perfil de Investidor',
      fields: [
        {
          name: 'risk_profile',
          label: 'Perfil de Risco',
          type: 'select',
          options: RISK_PROFILES,
          required: true
        },
      ]
    },
    {
      title: 'Meios de Transporte (mais frequentemente usado)',
      fields: [
        {
          name: 'transportation_methods',
          label: 'Meios de Transporte',
          type: 'select',
          options: MEIOS_TRANSPORTE,
          required: true
        }
      ]
    },
    {
      title: 'Dependentes',
      fields: [
        {
          name: 'dependents',
          label: 'Dependentes',
          type: 'dependent_checkbox',
          options: DEPENDENTES,
          required: true
        }
      ]
    },
    {
      title: 'Objetivos Financeiros',
      fields: [
        {
          name: 'financial_goal',
          label: 'Objetivo Financeiro',
          type: 'select',
          options: FINANCIAL_GOALS,
          required: true
        }
      ]
    }
  ];

  // Função para validar os campos obrigatórios do step atual
  const validateCurrentStep = () => {
    const currentFields = steps[currentStep].fields;
    const errors = {};
    let isValid = true;

    currentFields.forEach(field => {
      if (field.required) {
        const value = formData[field.name];

        // Validação para diferentes tipos de campo
        if (field.type === 'dependent_checkbox') {
          if (!value || value.length === 0) {
            errors[field.name] = `${field.label} é obrigatório`;
            isValid = false;
          }
        } else if (field.type === 'select') {
          if (!value || value === '') {
            errors[field.name] = `${field.label} é obrigatório`;
            isValid = false;
          }
        } else {
          // Para inputs normais (text, number, etc.)
          if (!value || value === '') {
            errors[field.name] = `${field.label} é obrigatório`;
            isValid = false;
          }
        }
      }
    });

    setValidationErrors(errors);
    return isValid;
  };

  const handleNext = () => {
    // Validar campos obrigatórios antes de avançar
    if (!validateCurrentStep()) {
      return;
    }

    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
      setValidationErrors({});
    } else {
      // separação dos dados do objetivo do questionário
      const { financial_goal, financial_goal_details, ...questionnaireData } = formData;

      const processedData = {
        questionnaire_data: questionnaireData,
        objective_data: {
          financial_goal: financial_goal,
          financial_goal_details: financial_goal_details
        }
      };

      console.log('Dados processados:', processedData);
      onComplete(processedData);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const updateFormData = (name, value) => {
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const renderField = (field) => {
    switch (field.type) {
      case 'select':
        return (
          <div>
            <select
              value={formData[field.name]}
              onChange={(e) => {
                updateFormData(field.name, e.target.value);

                // Se for objetivos financeiros, reset dos detalhes
                if (field.name === 'financial_goal') {
                  updateFormData('financial_goal_details', {
                    target_amount: '',
                    time_frame: ''
                  });
                }

                // Limpa erro quando usuário interage com o campo
                if (validationErrors[field.name]) {
                  setValidationErrors(prev => {
                    const newErrors = { ...prev };
                    delete newErrors[field.name];
                    return newErrors;
                  });
                }
              }}
              className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 ${validationErrors[field.name]
                ? 'border-red-500 focus:ring-red-500'
                : 'border-gray-300'
                }`}
              required={field.required}
            >
              <option value="">Selecione...</option>
              {field.options.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            {/* Campos de valor e prazo para objetivos financeiros */}
            {field.name === 'financial_goal' && formData[field.name] && (
              <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
                <h4 className="text-sm font-medium text-green-800 mb-3">
                  Detalhes do objetivo selecionado:
                </h4>

                <div className="space-y-3">
                  <div>
                    <label className="block text-sm text-green-700 mb-1">
                      Valor desejado (R$) - opcional:
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="Ex: 50000.00"
                      value={formData.financial_goal_details?.target_amount || ''}
                      onChange={(e) => {
                        updateFormData('financial_goal_details', {
                          ...formData.financial_goal_details,
                          target_amount: e.target.value
                        });
                      }}
                      className="w-full px-3 py-2 text-sm border border-green-300 rounded focus:ring-1 focus:ring-green-500 focus:border-green-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm text-green-700 mb-1">
                      Prazo para conclusão - opcional:
                    </label>
                    <input
                      type="text"
                      placeholder="Ex: 2 anos, 6 meses, 10 anos"
                      value={formData.financial_goal_details?.time_frame || ''}
                      onChange={(e) => {
                        updateFormData('financial_goal_details', {
                          ...formData.financial_goal_details,
                          time_frame: e.target.value
                        });
                      }}
                      className="w-full px-3 py-2 text-sm border border-green-300 rounded focus:ring-1 focus:ring-green-500 focus:border-green-500"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        );

      case 'dependent_checkbox':
        return (
          <div className={`space-y-4 ${validationErrors[field.name] ? 'border-2 border-red-200 rounded-lg p-2' : ''}`}>
            {field.options.map(option => (
              <div key={option.value} className="border rounded-lg p-4">
                <label className="flex items-center space-x-2 mb-2">
                  <input
                    type="checkbox"
                    checked={formData[field.name]?.some(dep => dep.type === option.value) || false}
                    onChange={(e) => {
                      const currentDependents = formData[field.name] || [];

                      // Limpa erro quando usuário interage
                      if (validationErrors[field.name]) {
                        setValidationErrors(prev => {
                          const newErrors = { ...prev };
                          delete newErrors[field.name];
                          return newErrors;
                        });
                      }

                      if (e.target.checked) {
                        // Se selecionou "nenhum", remove todos os outros
                        if (option.value === 'nenhum') {
                          updateFormData(field.name, [{ type: 'nenhum', quantity: 0 }]);
                        } else {
                          // Remove "nenhum" se existir e adiciona o novo dependente
                          const filteredDependents = currentDependents.filter(dep => dep.type !== 'nenhum');
                          updateFormData(field.name, [...filteredDependents, { type: option.value, quantity: 1 }]);
                        }
                      } else {
                        // Remove o dependente
                        updateFormData(field.name, currentDependents.filter(dep => dep.type !== option.value));
                      }
                    }}
                    className="rounded text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm font-medium text-gray-700">{option.label}</span>
                </label>

                {/* Campo de quantidade (apenas se selecionado e não for "nenhum") */}
                {formData[field.name]?.some(dep => dep.type === option.value) && option.value !== 'nenhum' && (
                  <div className="ml-6 mt-2">
                    <label className="block text-xs text-gray-600 mb-1">
                      Quantidade:
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={formData[field.name]?.find(dep => dep.type === option.value)?.quantity || 1}
                      onChange={(e) => {
                        const currentDependents = formData[field.name] || [];
                        const updatedDependents = currentDependents.map(dep =>
                          dep.type === option.value
                            ? { ...dep, quantity: parseInt(e.target.value) || 1 }
                            : dep
                        );
                        updateFormData(field.name, updatedDependents);
                      }}
                      className="w-20 px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        );

      default:
        return (
          <input
            type={field.type}
            value={formData[field.name]}
            onChange={(e) => {
              updateFormData(field.name, e.target.value);
              // Limpa erro quando usuário interage com o campo
              if (validationErrors[field.name]) {
                setValidationErrors(prev => {
                  const newErrors = { ...prev };
                  delete newErrors[field.name];
                  return newErrors;
                });
              }
            }}
            className={`w-full px-4 py-3 border rounded-lg focus:ring-2 ${validationErrors[field.name]
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:ring-blue-500'
              }`}
            required={field.required}
            min={field.type === 'number' ? '0' : undefined}
            step={field.type === 'number' && field.name === 'monthly_income' ? '0.01' : undefined}
          />
        );
    }
  };

  const currentStepData = steps[currentStep];

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold text-gray-800">
              {currentStepData.title}
            </h2>
            <span className="text-sm text-gray-500">
              Passo {currentStep + 1} de {steps.length}
            </span>
          </div>

          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            />
          </div>
        </div>

        <div className="space-y-6">
          {currentStepData.fields.map((field, index) => (
            <div key={index}>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              {renderField(field)}

              {/* Exibir erro de validação */}
              {validationErrors[field.name] && (
                <p className="mt-1 text-sm text-red-600">
                  {validationErrors[field.name]}
                </p>
              )}

              {/* Resumo dos dependentes selecionados */}
              {field.name === 'dependents' && formData.dependents?.length > 0 && !formData.dependents?.some(dep => dep.type === 'nenhum') && (
                <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                  <h4 className="text-sm font-medium text-blue-800 mb-2">Resumo dos dependentes:</h4>
                  <div className="space-y-1">
                    {formData.dependents.map(dependent => {
                      const option = DEPENDENTES.find(d => d.value === dependent.type);
                      return (
                        <div key={dependent.type} className="text-sm text-blue-700">
                          {option?.label}: {dependent.quantity} {dependent.quantity === 1 ? 'dependente' : 'dependentes'}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Resumo do objetivo financeiro selecionado */}
              {field.name === 'financial_goal' && formData.financial_goal && (
                <div className="mt-4 p-3 bg-green-50 rounded-lg">
                  <h4 className="text-sm font-medium text-green-800 mb-2">Resumo do objetivo:</h4>
                  <div className="text-sm text-green-700">
                    {(() => {
                      const option = FINANCIAL_GOALS.find(g => g.value === formData.financial_goal);
                      const details = formData.financial_goal_details;
                      return (
                        <div>
                          <div className="font-medium">{option?.label}</div>
                          {details?.target_amount && (
                            <div className="ml-2 text-xs">Valor: R$ {parseFloat(details.target_amount).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
                          )}
                          {details?.time_frame && (
                            <div className="ml-2 text-xs">Prazo: {details.time_frame}</div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="flex justify-between mt-8">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 0}
            className="px-6 py-2 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Anterior
          </button>

          <button
            onClick={handleNext}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            {currentStep === steps.length - 1 ? 'Finalizar' : 'Próximo'}
          </button>
        </div>
      </div>
    </div>
  );
};