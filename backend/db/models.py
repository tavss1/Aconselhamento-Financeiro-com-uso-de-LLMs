# Modelos SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)  # Hash da senha
    criado_em = Column(DateTime, default=datetime.utcnow)
    ultimo_login = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    perfil_financeiro = relationship("FinancialProfile", back_populates="usuario")

# TODO: Verificar qual o caminho o usuário pode seguir p solicitar requisição
# É necessário que seja feito 2/3 dos pontos para que seja feito a requisição (?):
#     * Questionario - Necessário! (?)
#     * Objetivo - Pode ser null - ou ser mascarado como "não informado"
#     * Extrato - Necessário!

class FinancialProfile(Base):
    __tablename__ = "perfil_financeiro"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    questionnaire_data = Column(Text, nullable=False)  # JSON com respostas do questionário
    objetivo = Column(Text, nullable=True)  # JSON com objetivo - *verificar 
    extrato = Column(Text, nullable=False)  # JSON com extrato bancário
    data_criado = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    usuario = relationship("Usuario", back_populates="perfil_financeiro")
    llm_responses = relationship("LLMResponse", back_populates="perfil_financeiro")

# TODO: Rever modelo para armazenar as respostas das LLMs
class LLMResponse(Base):
    __tablename__ = "llm_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    # Pela Arq de Software, a resposta das LLMs tem que buscar o perfil financeiro do usuario
    perfil_financeiro_id = Column(Integer, ForeignKey("perfil_financeiro.id"), nullable=False) 
    llm_responses = Column(Text, nullable=False)  # JSON com todas as respostas dos LLMs
    default_response = Column(Text, nullable=False)  # JSON com a melhor resposta
    score = Column(Text, nullable=False)  # JSON com métricas de comparação
    data_criado = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    perfil_financeiro = relationship("FinancialProfile", back_populates="llm_responses")