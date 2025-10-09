import React, { useState, useEffect } from 'react';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/AuthContext';
import { LoginForm } from './components/Auth/LoginForm';
import { SetupWizard } from './components/Wizard/setupWizard';
import { LoadingSpinner } from './components/Components/loadingSpinner';
import Dashboard from './pages/Dashboard';

const AppContent = () => {
  const { isAuthenticated, loading, user, token, logout } = useAuth();
  const [currentView, setCurrentView] = useState('wizard'); // 'wizard' | 'dashboard'
  const [userHasProfile, setUserHasProfile] = useState(false);

  // Log de debug
  console.log('🏠 App - Estado de autenticação:', {
    loading,
    authenticated: isAuthenticated(),
    hasUser: !!user,
    hasToken: !!token
  });

  // Verificar se o usuário já tem perfil completo
  useEffect(() => {
    if (isAuthenticated) {
      // Aqui você pode verificar se o usuário já tem perfil completo
      // Por exemplo, fazendo uma chamada para a API
      const checkUserProfile = async () => {
        try {
          const token = localStorage.getItem('access_token');
          if (token) {
            // Fazer chamada para verificar perfil
            // Por enquanto, vamos deixar como false para sempre mostrar o wizard primeiro
            setUserHasProfile(false);
          }
        } catch (error) {
          console.error('Erro ao verificar perfil do usuário:', error);
          setUserHasProfile(false);
        }
      };
      
      checkUserProfile();
    }
  }, [isAuthenticated]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner size="large" />
        <div className="ml-4 text-sm text-gray-600">
          Verificando autenticação...
        </div>
      </div>
    );
  }

  // Debug info (remover em produção)
  const debugInfo = {
    loading,
    authenticated: isAuthenticated(),
    hasUser: !!user,
    hasToken: !!token,
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
        />
      ) : (
        <div>
          {/* Header simples para navegação */}
          <div className="bg-white shadow-sm border-b">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                <h1 className="text-xl font-semibold text-gray-900">
                  Aconselhamento Financeiro
                </h1>
                <div className="flex space-x-4">
                  <button
                    onClick={handleBackToWizard}
                    className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium"
                  >
                    Configurações
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
          <Dashboard />
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