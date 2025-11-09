import React, { useState, useEffect } from 'react';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/AuthContext';
import { LoginForm } from './components/Auth/LoginForm';
import { SetupWizard } from './components/Wizard/setupWizard';
import { SimpleDashboard } from './components/Dashboard/simpleDashboard';
import { LoadingSpinner } from './components/Components/loadingSpinner';
import { dashboardService } from './services/dashboardService';
import Dashboard from './pages/Dashboard';
import { UserCog, Home, User } from 'lucide-react';

const AppContent = () => {
  const { isAuthenticated, loading, user, token, logout } = useAuth();
  const [currentView, setCurrentView] = useState('profile'); // 'profile' | 'home' | 'dashboard'
  const [userHasProfile, setUserHasProfile] = useState(false);
  const [checkingAnalysis, setCheckingAnalysis] = useState(false);
  const [autoRedirected, setAutoRedirected] = useState(false);

  // Log de debug
  console.log('🏠 App - Estado de autenticação:', {
    loading,
    authenticated: isAuthenticated(),
    hasUser: !!user,
    hasToken: !!token
  });

  // Verificar se o usuário já tem perfil completo e análise
  useEffect(() => {
    if (isAuthenticated()) {
      checkUserAnalysisStatus();
    }
  }, [isAuthenticated]);

  const checkUserAnalysisStatus = async () => {
    setCheckingAnalysis(true);
    try {
      console.log('🔍 Iniciando verificação do status de análise...');
      const analysisStatus = await dashboardService.checkAnalysisStatus();
      
      console.log('📊 Status da análise do usuário:', analysisStatus);
      console.log('📋 Detalhes:', {
        has_profile: analysisStatus.has_profile,
        has_extract: analysisStatus.has_extract,
        has_analysis: analysisStatus.has_analysis,
        should_redirect_to: analysisStatus.should_redirect_to,
        current_view: currentView
      });
      
      // Fluxo simplificado:
      // 1. Se tem perfil completo → Home (baseado em has_profile do backend)
      // 2. Se não tem perfil completo → Profile (wizard)
      
      if (analysisStatus.has_profile) {
        console.log('✅ Usuário possui perfil financeiro completo, redirecionando para home');
        setCurrentView('home');
        setUserHasProfile(true);
        setAutoRedirected(true);
        setTimeout(() => setAutoRedirected(false), 5000);
      } else {
        console.log('📝 Usuário precisa completar perfil, mantendo no wizard de perfil');
        console.log('❌ Motivo: has_profile =', analysisStatus.has_profile);
        setCurrentView('profile');
        setUserHasProfile(false);
      }
    } catch (error) {
      console.error('❌ Erro ao verificar status de análise:', error);
      console.error('❌ Erro detalhado:', error.response || error.message);
      // Em caso de erro, manter no profile por segurança
      setCurrentView('profile');
      setUserHasProfile(false);
    } finally {
      setCheckingAnalysis(false);
    }
  };

  if (loading || checkingAnalysis) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="large" />
        <div className="ml-4 text-sm text-gray-600">
          {loading ? 'Verificando autenticação...' : 'Verificando análise financeira...'}
        </div>
      </div>
    );
  }

  if (!isAuthenticated()) {
    return (
      <div>
        <LoginForm />
      </div>
    );
  }

  // Navegação entre as views
  const handleProfileComplete = () => {
    setCurrentView('home');
    setUserHasProfile(true);
  };

  const handleAnalysisComplete = () => {
    setCurrentView('dashboard');
  };

  const handleBackToHome = () => {
    setCurrentView('home');
  };

  const handleBackToProfile = () => {
    setCurrentView('profile');
  };

  // Componente de Header reutilizável
  const Header = ({ title, showProfileButton = true, showHomeButton = false }) => (
    <div className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <h1 className="text-xl font-semibold text-gray-900">
            {title}
          </h1>
          <div className="flex space-x-4">
            {showHomeButton && (
              <button
                onClick={handleBackToHome}
                className="text-blue-600 hover:text-blue-900 px-3 py-2 rounded-md text-sm font-medium flex items-center gap-2"
              >
                <Home className="h-4 w-4" />
                Voltar para Home
              </button>
            )}
            {showProfileButton && (
              <button
                onClick={handleBackToProfile}
                className="text-blue-600 hover:text-blue-900 px-3 py-2 rounded-md text-sm font-medium flex items-center gap-2"
              >
                <UserCog className="h-4 w-4" />
                Editar Perfil
              </button>
            )}
            <button
              onClick={() => {
                logout();
                window.location.reload();
              }}
              className="text-red-600 hover:text-red-900 px-3 py-2 rounded-md text-sm font-medium"
            >
              Sair
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="App">
      {currentView === 'profile' ? (
        <SetupWizard 
          onComplete={handleProfileComplete}
          onBackToProfile={handleBackToProfile}
        />
      ) : currentView === 'home' ? (
        <div>
          {/* Notificação de redirecionamento automático */}
          {autoRedirected && (
            <div className="bg-green-50 border-l-4 border-green-400 p-4 mb-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-green-700">
                    Bem-vindo de volta! Você foi redirecionado automaticamente para a tela inicial.
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {/* Header usando componente reutilizável */}
          <Header 
            title="Aconselhamento Financeiro com uso de LLMs"
            showProfileButton={true}
            showHomeButton={false}
          />
          
          <SimpleDashboard 
            onAnalysisComplete={handleAnalysisComplete}
            onBackToHome={handleBackToHome}
            onBackToProfile={handleBackToProfile}
          />
        </div>
      ) : (
        <div>
          {/* Notificação de redirecionamento automático */}
          {autoRedirected && (
            <div className="bg-green-50 border-l-4 border-green-400 p-4 mb-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-green-700">
                    Bem-vindo ao seu dashboard completo! Análise financeira concluída.
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {/* Header usando componente reutilizável */}
          <Header 
            title="Dashboard Financeiro Completo"
            showProfileButton={false}
            showHomeButton={true}
          />
          <Dashboard onBackToHome={handleBackToHome} />
        </div>
      )}
    </div>
  );
};

const App = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;