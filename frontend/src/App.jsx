import React, { useState, useEffect } from 'react';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/AuthContext';
import { LoginForm } from './components/Auth/LoginForm';
import { SetupWizard } from './components/Wizard/setupWizard';
import { LoadingSpinner } from './components/Components/loadingSpinner';
import { dashboardService } from './services/dashboardService';
import Dashboard from './pages/Dashboard';
import { Home } from 'lucide-react';

const AppContent = () => {
  const { isAuthenticated, loading, user, token, logout } = useAuth();
  const [currentView, setCurrentView] = useState('wizard'); // 'wizard' | 'dashboard'
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
      const analysisStatus = await dashboardService.checkAnalysisStatus();
      
      console.log('📊 Status da análise do usuário:', analysisStatus);
      
      if (analysisStatus.has_analysis && analysisStatus.should_redirect_to === 'dashboard') {
        console.log('✅ Usuário possui análise concluída, redirecionando para dashboard');
        setCurrentView('dashboard');
        setUserHasProfile(true);
        setAutoRedirected(true);
        
        // Remover a notificação após alguns segundos
        setTimeout(() => setAutoRedirected(false), 5000);
      } else {
        console.log('📝 Usuário precisa completar perfil/análise, mantendo no wizard');
        setCurrentView('wizard');
        setUserHasProfile(false);
      }
    } catch (error) {
      console.error('❌ Erro ao verificar status de análise:', error);
      // Em caso de erro, manter no wizard por segurança
      setCurrentView('wizard');
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

  // Debug info (remover em produção)
  const debugInfo = {
    loading,
    checkingAnalysis,
    authenticated: isAuthenticated(),
    hasUser: !!user,
    hasToken: !!token,
    currentView,
    userHasProfile,
    tokenFromStorage: !!localStorage.getItem('access_token'),
    userFromStorage: !!localStorage.getItem('user')
  };

  if (!isAuthenticated()) {
    console.log('🚫 Usuário não autenticado, mostrando login');
    return (
      <div>
        <LoginForm />
        {/* Debug info - remover em produção */}
        <div className="fixed bottom-4 right-4 bg-black text-white p-2 text-xs rounded">
          <pre>{JSON.stringify(debugInfo, null, 2)}</pre>
        </div>
      </div>
    );
  }

  // Se o usuário está autenticado, mostrar wizard ou dashboard
  const handleWizardComplete = () => {
    setCurrentView('dashboard');
    setUserHasProfile(true);
  };

  const handleViewDashboard = () => {
    setCurrentView('dashboard');
  };

  const handleBackToWizard = () => {
    setCurrentView('wizard');
  };

  return (
    <div className="App">
      {currentView === 'wizard' ? (
        <SetupWizard 
          onComplete={handleWizardComplete}
          onViewDashboard={handleViewDashboard}
          onBackToWizard={handleBackToWizard}
        />
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
                    Bem-vindo de volta! Você foi redirecionado automaticamente para seu dashboard com análise financeira concluída.
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {/* Header simples para navegação */}
          <div className="bg-white shadow-sm border-b">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                <h1 className="text-xl font-semibold text-gray-900">
                  Aconselhamento Financeiro com uso de LLMs
                </h1>
                <div className="flex space-x-4">
                  <button
                    onClick={handleBackToWizard}
                    className="text-blue-600 hover:text-blue-900 px-3 py-2 rounded-md text-sm font-medium flex items-center gap-2"
                  >
                    <Home className="h-4 w-4" />
                    Início
                  </button>
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
          <Dashboard onBackToHome={handleBackToWizard} />
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