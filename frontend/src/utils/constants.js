export const API_BASE_URL = 'http://localhost:8000';

export const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

export const RISK_PROFILES = [
  { value: 'conservador', label: 'Conservador' },
  { value: 'moderado', label: 'Moderado' },
  { value: 'agressivo', label: 'Agressivo' }
];

// export const INVESTMENT_EXPERIENCE = [
//   { value: 'iniciante', label: 'Iniciante' },
//   { value: 'intermediario', label: 'Intermediário' },
//   { value: 'avancado', label: 'Avançado' }
// ];

export const MEIOS_TRANSPORTE = [
  { value: 'carro', label: 'Carro' },
  { value: 'moto', label: 'Moto' },
  { value: 'transporte publico', label: 'Transporte Público' },
  { value: 'bicicleta', label: 'Bicicleta' },
  { value: 'a pé', label: 'A Pé' },
  { value: 'carona', label: 'Carona' }
];

export const DEPENDENTES = [
  { value: 'pet', label: 'Animal de Estimação' },
  { value: 'filho', label: 'Filho(s)' },
  { value: 'parentes', label: 'Parentes' },
  { value: 'nenhum', label: 'Nenhum' }
];

export const FINANCIAL_GOALS = [
  { value: 'reserva de emergencia', label: 'Reserva de Emergência' },
  { value: 'viagem', label: 'Planejar Viagem' },
  { value: 'investimento', label: 'Crescimento Patrimonial' },
  { value: 'quitar dívida', label: 'Quitar Dívida' }
];

export const NAVIGATION_TABS = [
  { id: 'overview', label: 'Aconselhamento', icon: 'TrendingUp' },
  { id: 'advice', label: 'Histórico', icon: 'Brain' },
  { id: 'comparison', label: 'Comparação LLMs', icon: 'FileText' }
];