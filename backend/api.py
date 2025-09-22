# api.py
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from main import FinancialAdvisorCrew  
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import json
import os
import uuid
from datetime import datetime

# Importações para autenticação
from db.database import get_db
from db.models import Usuario, FinancialProfile
from schemas.auth import UserRegister, UserLogin, TokenResponse, UserProfile as UserProfileSchema
from middleware.auth import hash_password, verify_password, create_access_token, get_current_user_id

app = FastAPI(
    title="Financial Planning AI API",
    description="API para planejamento financeiro com LLMs",
    version="1.0.0"
)

# Configurar CORS para React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # URL do React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints para verificação da API
@app.get("/")
async def root():
    """Endpoint raiz para verificar se a API está funcionando"""
    return {"message": "API de Autenticação funcionando!", "status": "online"}

@app.get("/health")
async def health_check():
    """Health check da API"""
    return {"status": "healthy", "service": "auth-api"}

# Rotas de Autenticação
@app.post("/api/auth/register", response_model=TokenResponse)
async def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Registra um novo usuário"""
    try:
        # Verificar se o email já existe
        existing_user = db.query(Usuario).filter(Usuario.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email já está em uso"
            )
        
        # Criar novo usuário
        hashed_password = hash_password(user_data.password)
        new_user = Usuario(
            nome=user_data.name,
            email=user_data.email,
            password=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Criar token de acesso
        access_token = create_access_token(data={"sub": str(new_user.id)})
        
        # Resposta com token e dados do usuário
        user_response = {
            "id": new_user.id,
            "name": new_user.nome,
            "email": new_user.email
        }
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_response
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@app.post("/api/auth/login", response_model=TokenResponse)
async def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Autentica um usuário e retorna token de acesso"""
    try:
        # Buscar usuário por email
        user = db.query(Usuario).filter(Usuario.email == user_credentials.email).first()
        
        if not user or not verify_password(user_credentials.password, user.password):
            raise HTTPException(
                status_code=401,
                detail="Email ou senha incorretos"
            )
        
        # Atualizar último login
        from datetime import datetime
        user.ultimo_login = datetime.utcnow()
        db.commit()
        
        # Criar token de acesso
        access_token = create_access_token(data={"sub": str(user.id)})
        
        # Resposta com token e dados do usuário
        user_response = {
            "id": user.id,
            "name": user.nome,
            "email": user.email
        }
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_response
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@app.get("/api/user/profile", response_model=UserProfileSchema)
async def get_user_profile(current_user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Retorna o perfil do usuário autenticado"""
    try:
        user = db.query(Usuario).filter(Usuario.id == current_user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="Usuário não encontrado"
            )
        
        return {
            "id": user.id,
            "name": user.nome,
            "email": user.email,
            "ultimo_login": user.ultimo_login.isoformat() if user.ultimo_login else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@app.post("/api/auth/validate-token")
async def validate_token(current_user_id: int = Depends(get_current_user_id)):
    """Valida o token JWT e retorna informações básicas do usuário"""
    return {
        "valid": True,
        "user_id": current_user_id,
        "message": "Token válido"
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)