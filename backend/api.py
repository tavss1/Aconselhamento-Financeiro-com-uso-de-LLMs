from fastapi import FastAPI,  HTTPException, Depends, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
#from main import FinancialAdvisorCrew  
# from pydantic import BaseModel
# from typing import Dict, Any
import json
import os
import uuid
from datetime import datetime

# Importações para autenticação
from db.database import get_db
from db.models import Usuario, FinancialProfile
from schemas.auth import UserRegister, TokenResponse, UserProfile as UserProfileSchema
from schemas.financial import FinancialProfileCreate, FinancialProfileResponse, UploadResponse
from middleware.auth import hash_password, verify_password, create_access_token, get_current_user_id

app = FastAPI(
    title="Financial Planning AI API",
    description="API para planejamento financeiro com LLMs",
    version="1.0.0"
)

# Configurar CORS para React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "http://127.0.0.1:3000"],  # URL do React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints para verificação de status da API
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

# TODO -> Ajustar este endpoint para diminuir os IF 
@app.post("/api/auth/login", response_model=TokenResponse)
async def login_user(user_credentials: Request, db: Session = Depends(get_db)):
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
    
# Endpoints de Perfil Financeiro
@app.post("/api/financial-profile", response_model=FinancialProfileResponse)
async def create_financial_profile(
    profile_data: FinancialProfileCreate, 
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Cria ou atualiza o perfil financeiro do usuário"""
    try:
        # Verificar se já existe um perfil para este usuário
        existing_profile = db.query(FinancialProfile).filter(
            FinancialProfile.usuario_id == current_user_id
        ).first()
        
        # Converter dados do questionário e objetivo para JSON
        questionnaire_dict = profile_data.questionnaire_data.dict()
        objective_dict = profile_data.objective_data.dict()
        
        if existing_profile:
            # Atualizar perfil existente
            existing_profile.questionnaire_data = json.dumps(questionnaire_dict, ensure_ascii=False)
            existing_profile.objetivo = json.dumps(objective_dict, ensure_ascii=False)
            
            db.commit()
            db.refresh(existing_profile)
            profile = existing_profile
        else:
            # Criar novo perfil
            new_profile = FinancialProfile(
                usuario_id=current_user_id,
                questionnaire_data=json.dumps(questionnaire_dict, ensure_ascii=False),
                objetivo=json.dumps(objective_dict, ensure_ascii=False),
                extrato=json.dumps({}, ensure_ascii=False)  # Extrato vazio inicialmente
            )
            
            db.add(new_profile)
            db.commit()
            db.refresh(new_profile)
            profile = new_profile
        
        # Preparar resposta
        return {
            "id": profile.id,
            "usuario_id": profile.usuario_id,
            "questionnaire_data": json.loads(profile.questionnaire_data),
            "objetivo": json.loads(profile.objetivo) if profile.objetivo else None,
            "extrato": json.loads(profile.extrato) if profile.extrato else None,
            "data_criado": profile.data_criado.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@app.get("/api/financial-profile", response_model=FinancialProfileResponse)
async def get_financial_profile(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Retorna o perfil financeiro do usuário"""
    try:
        profile = db.query(FinancialProfile).filter(
            FinancialProfile.usuario_id == current_user_id
        ).first()
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Perfil financeiro não encontrado"
            )
        
        return {
            "id": profile.id,
            "usuario_id": profile.usuario_id,
            "questionnaire_data": json.loads(profile.questionnaire_data),
            "objetivo": json.loads(profile.objetivo) if profile.objetivo else None,
            "extrato": json.loads(profile.extrato) if profile.extrato else None,
            "data_criado": profile.data_criado.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@app.post("/api/upload-statement", response_model=UploadResponse)
async def upload_bank_statement(
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Upload e processamento de extrato bancário"""
    try:
        # Validar tipo de arquivo
        allowed_extensions = ['.csv', '.ofx']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de arquivo não suportado. Use: {', '.join(allowed_extensions)}"
            )
        
        # Criar diretório de upload se não existir
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Gerar nome único para o arquivo
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Salvar arquivo
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Informações do arquivo para resposta
        file_info = {
            "original_name": file.filename,
            "saved_name": unique_filename,
            "file_path": file_path,
            "file_size": len(content),
            "file_type": file_extension,
            "upload_time": datetime.utcnow().isoformat()
        }
        
        # Buscar perfil financeiro do usuário
        profile = db.query(FinancialProfile).filter(
            FinancialProfile.usuario_id == current_user_id
        ).first()
        
        profile_updated = False
        if profile:
            # Atualizar extrato no perfil financeiro
            extrato_data = {
                "file_info": file_info,
                "processed": False,
                "processed_at": None
            }
            
            profile.extrato = json.dumps(extrato_data, ensure_ascii=False)
            db.commit()
            profile_updated = True
        
        return {
            "message": "Arquivo enviado com sucesso",
            "file_info": file_info,
            "profile_updated": profile_updated
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")

@app.get("/api/processing-status/{profile_id}")
async def get_processing_status(
    profile_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Retorna o status de processamento do perfil financeiro"""
    try:
        profile = db.query(FinancialProfile).filter(
            FinancialProfile.id == profile_id,
            FinancialProfile.usuario_id == current_user_id
        ).first()
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Perfil não encontrado"
            )
        
        # Verificar se há dados processados
        has_questionnaire = bool(profile.questionnaire_data)
        has_extrato = bool(profile.extrato and profile.extrato != '{}')
        
        status = {
            "profile_id": profile.id,
            "has_questionnaire": has_questionnaire,
            "has_extrato": has_extrato,
            "ready_for_processing": has_questionnaire and has_extrato,
            "created_at": profile.data_criado.isoformat()
        }
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)