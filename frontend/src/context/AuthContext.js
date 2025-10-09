import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/authService';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        // Primeiro, limpar qualquer token antigo que não seja access_token
        const oldToken = localStorage.getItem('token');
        if (oldToken) {
          console.log('🧹 Removendo token antigo');
          localStorage.removeItem('token');
        }

        const savedToken = localStorage.getItem('access_token');
        const savedUser = localStorage.getItem('user');
        
        console.log('🔍 Inicializando autenticação...');
        console.log('Token salvo:', !!savedToken);
        console.log('Usuário salvo:', !!savedUser);
        
        if (savedToken && savedUser) {
          console.log('📝 Validando token com backend...');
          // Validar token com o backend
          const isValid = await authService.validateToken();
          
          console.log('✅ Token válido:', isValid);
          
          if (isValid) {
            setToken(savedToken);
            setUser(JSON.parse(savedUser));
            console.log('🎉 Usuário autenticado com sucesso');
          } else {
            // Token inválido, limpar dados
            console.log('❌ Token inválido, limpando dados');
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            setToken(null);
            setUser(null);
          }
        } else {
          console.log('📭 Nenhum token ou usuário encontrado');
          setToken(null);
          setUser(null);
        }
      } catch (error) {
        console.error('❌ Erro ao inicializar autenticação:', error);
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        setToken(null);
        setUser(null);
      } finally {
        console.log('🏁 Inicialização da autenticação finalizada');
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    try {
      setLoading(true);
      const response = await authService.login(email, password);
      
      setUser(response.user);
      setToken(response.access_token);
      
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('user', JSON.stringify(response.user));
      
      return response;
    } catch (error) {
      console.error('Erro no login:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const register = async (name, email, password) => {
    try {
      setLoading(true);
      const response = await authService.register(name, email, password);
      
      setUser(response.user);
      setToken(response.access_token);
      
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('user', JSON.stringify(response.user));
      
      return response;
    } catch (error) {
      console.error('Erro no registro:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  };

  const isAuthenticated = () => {
    const authenticated = !!token && !!user;
    console.log('🔐 Verificando autenticação:', {
      hasToken: !!token,
      hasUser: !!user,
      authenticated
    });
    return authenticated;
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    isAuthenticated
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook customizado para usar o contexto de autenticação
export const useAuth = () => {
  const context = useContext(AuthContext);
  
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider');
  }
  
  return context;
};