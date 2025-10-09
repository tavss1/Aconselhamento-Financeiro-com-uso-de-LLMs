# Versão completa com integração CrewAI para processamento de análise financeira
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import json
import os
import sys
import uuid
import re
import tempfile
from datetime import datetime

# Adicionar path para importar as ferramentas CrewAI
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports do CrewAI
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool

# Imports das ferramentas especializadas
from crew.tools import (
    BankStatementParserTool, 
    FinancialAdvisorTool,
    DashboardDataCompilerTool
)

# Importações para autenticação
from db.database import get_db
from db.models import Usuario, FinancialProfile, LLMResponse
from schemas.auth import UserRegister, TokenResponse, UserProfile as UserProfileSchema
from schemas.financial import FinancialProfileCreate, FinancialProfileResponse, UploadResponse
from schemas.llm import LLMComparisonResponse, LLMResponse as LLMResponseSchema
from middleware.auth import hash_password, verify_password, create_access_token, get_current_user_id

# Configuração CrewAI
os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["CREWAI_LLM_PROVIDER"] = "ollama"
os.environ["CREWAI_USE_LOCAL_LLM_ONLY"] = "true"

# Configuração do LLM para agentes
llm = LLM(
    model="ollama/gemma3",
    base_url="http://localhost:11434"
)

app = FastAPI(
    title="Financial Planning AI API - CrewAI Integration",
    description="API com integração completa do sistema de agentes CrewAI para análise financeira",
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

# ============================================================================
# CLASSES CREWAI INTEGRADAS
# ============================================================================

class StandaloneUserProfileBuilderToolSchema(BaseModel):
    user_data_json: Any = Field(description="JSON string OU objeto dict com dados do usuário")

class StandaloneUserProfileBuilderTool(BaseTool):
    """Ferramenta para construir perfil financeiro a partir de dados diretos."""
    
    name: str = "StandaloneUserProfileBuilder"
    description: str = "Constrói perfil financeiro normalizado a partir de dados do usuário"
    args_schema = StandaloneUserProfileBuilderToolSchema

    def _run(self, user_data_json: Any) -> str:
        """Constrói perfil financeiro."""
        try:
            if isinstance(user_data_json, dict):
                user_data = user_data_json
            else:
                user_data = json.loads(user_data_json)
            
            # Processar dados
            dependents = user_data.get("dependents", [])
            total_dependents = len(dependents) if isinstance(dependents, list) else 0
            
            idade = int(user_data.get("age", 30))
            renda = float(user_data.get("monthly_income", 5000))
            risk_profile = user_data.get("risk_profile", "moderado")
            
            financial_goal = user_data.get("financial_goal", "Reserva de emergência")
            target_amount = float(user_data.get("target_amount", 1200))
            time_frame = user_data.get("time_frame", "1 ano")
            
            estimated_expenses = renda * 0.7
            savings_capacity = renda - estimated_expenses
            debt_to_income = user_data.get("debt_to_income_ratio", 0.2)
            
            perfil = {
                "ok": True,
                "timestamp": datetime.now().isoformat(),
                "profile_id": f"api_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "usuario_id": user_data.get("user_id", 1),
                "dados_pessoais": {
                    "idade": idade,
                    "renda_mensal": renda,
                    "total_dependentes": total_dependents,
                    "detalhes_dependentes": dependents,
                    "risk_profile": risk_profile,
                    "transportation_methods": user_data.get("transportation_methods", ""),
                },
                "capacidade_poupanca": savings_capacity,
                "debt_to_income": debt_to_income,
                "savings_rate": (savings_capacity / renda * 100) if renda > 0 else 0,
                "objetivo": {
                    "descricao": financial_goal,
                    "valor_objetivo": target_amount,
                    "prazo": time_frame,
                    "meses_estimados_pelo_fluxo": int(target_amount / savings_capacity) if savings_capacity > 0 else 999
                },
                "classificacao_risco": self._classify_risk(debt_to_income, savings_capacity, idade)
            }
            
            return json.dumps(perfil, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Erro ao construir perfil: {str(e)}"})
    
    def _classify_risk(self, debt_ratio: float, savings: float, age: int) -> str:
        """Classifica perfil de risco financeiro."""
        risk_score = 0
        
        if debt_ratio < 0.2:
            risk_score += 4
        elif debt_ratio < 0.3:
            risk_score += 3
        elif debt_ratio < 0.5:
            risk_score += 2
        else:
            risk_score += 1
            
        if savings > 2000:
            risk_score += 3
        elif savings > 1000:
            risk_score += 2
        elif savings > 0:
            risk_score += 1
            
        if age < 30:
            risk_score += 2
        elif age < 50:
            risk_score += 3
        else:
            risk_score += 1
            
        if risk_score >= 8:
            return "Baixo Risco"
        elif risk_score >= 6:
            return "Risco Moderado" 
        else:
            return "Alto Risco"

class FinancialAdvisorCrew:
    """Crew de aconselhamento financeiro para API integrada."""
    
    def __init__(self, user_data: Dict[str, Any]):
        self.user_data = user_data
        self.user_data_json = json.dumps(user_data, ensure_ascii=False)
    
    def create_data_extractor_agent(self) -> Agent:
        """Cria agente extrator de dados financeiros."""
        return Agent(
            role="Analista Financeiro de Transações",
            goal="Extrair e categorizar transações financeiras de extratos bancários CSV, identificando padrões de gastos e oportunidades de economia.",
            backstory=(
                "Você é um especialista em finanças pessoais e tem como missão identificar padrões "
                "de consumo e categorizar transações bancárias de forma precisa e organizada. "
                "Seu trabalho é a base para que o consultor financeiro possa gerar conselhos personalizados."
            ),
            verbose=True,
            llm=llm,
            tools=[BankStatementParserTool()],
            memory=True,
            allow_delegation=False,
            max_iter=1
        )
    
    def create_financial_advisor_agent(self) -> Agent:
        """Cria agente consultor financeiro."""
        return Agent(
            role="Consultor Financeiro Pessoal",
            goal="Fornecer conselhos financeiros usando APENAS a ferramenta FinancialAdvisor",
            backstory=(
                "Você é um consultor financeiro certificado com uma regra fundamental: "
                "SEMPRE use exclusivamente a ferramenta FinancialAdvisor disponível para "
                "gerar conselhos. NUNCA invente ações como 'return the JSON content' ou "
                "similares. Sua única ação válida é 'FinancialAdvisor'."
            ),
            verbose=True,
            llm=llm,
            tools=[FinancialAdvisorTool()],
            allow_delegation=False,
            memory=False,
            max_iter=1
        )
    
    def create_extract_task(self, agent: Agent, csv_file_path: str, categorization_method: str = "ollama") -> Task:
        """Cria task de extração de dados."""
        return Task(
            description=f"""
            Você deve processar o extrato bancário diretamente usando a ferramenta BankStatementParserTool.

            Action: BankStatementParserTool
            Action Input: {{
            "file_path": "{csv_file_path}",
            "llm_enhanced": false,
            "categorization_method": "{categorization_method}",
            "ollama_model": "gemma3",
            "block_size": 10
            }}
            Retorne APENAS o JSON gerado pela ferramenta como resultado final.
            """,
            expected_output="""
            JSON estruturado contendo:
            - ok: true
            - transacoes: array completo com data, descricao, valor, categoria
            - totais_por_categoria: array com categoria e valor total
            - n_transacoes: quantidade total
            - timestamp: data/hora do processamento
            """,
            agent=agent,
            llm=llm
        )
    
    def create_advice_task(self, agent: Agent, profile_json: str, transactions_json: str) -> Task:
        """Cria task de geração de conselhos."""
        try:
            profile_data = json.loads(profile_json)
            objetivo = profile_data.get("objetivo", {})
            objetivo_desc = objetivo.get("descricao", "Não definido")
            objetivo_valor = objetivo.get("valor_objetivo", 0)
            objetivo_prazo = objetivo.get("prazo", "Não definido")
        except Exception:
            objetivo_desc = "Não definido"
            objetivo_valor = 0
            objetivo_prazo = "Não definido"

        preview_tx = transactions_json[:180] + "..." if transactions_json else "[Será obtido do contexto anterior]"
        description = f"""
            GERAR CONSELHOS FINANCEIROS PERSONALIZADOS

            OBJETIVO PRINCIPAL: {objetivo_desc} | META: R$ {objetivo_valor:,.2f} | PRAZO: {objetivo_prazo}

            Você é um consultor financeiro especializado em fornecer conselhos personalizados com base no perfil financeiro e nas transações categorizadas do usuário. 
            Gere um aconselhamento financeiro detalhado com base no perfil do usuário e nas transações categorizadas.
            O perfil descreve metas, renda, hábitos e objetivos. As transações categorizadas virão do contexto anterior.

            Perfil (resumo):
            {profile_json[:180]}...

            Transações:
            {preview_tx}

            Action: FinancialAdvisorTool
            Action Input: {{
                "profile_json": {{ ... }},
                "transactions_json": {{ ... }},
                "model": "gemma3"
            }}

            Use a ferramenta FinancialAdvisorTool para formatar a resposta final em JSON:
            {{
            "resumo": "...",
            "alertas": ["..."],
            "plano": {{
                "agora": ["..."],
                "30_dias": ["..."],
                "12_meses": ["..."]
            }},
            "metas_mensuraveis": [
                {{"meta": "...", "kpi": "...", "meta_num": 0, "prazo_meses": 12}}
            ]
            }}

            REGRAS IMPORTANTES:
            NÃO escreva nenhum texto fora do JSON.
            NUNCA use ações como "Manual Response Generation" ou "Final Answer".
            A única ação válida é "FinancialAdvisorTool".

            Responda APENAS com JSON válido.
        """
        return Task(
            description=description,
            expected_output="JSON válido contendo campos: resumo, alertas, plano, metas_mensuraveis.",
            agent=agent,
            tools=[FinancialAdvisorTool()],
            llm=llm,
            max_iter=1
        )
    
    def _clean_json_text(self, text: str) -> str:
        """Remove delimitadores Markdown e espaços extras."""
        if not text:
            return ""
        cleaned = re.sub(r"^[`']{3,}\s*json\s*", "", text.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"[`']{3,}\s*$", "", cleaned.strip())
        cleaned = re.sub(r"<\/?json>", "", cleaned.strip(), flags=re.IGNORECASE)
        return cleaned.strip()

    async def run_analysis(self, csv_file_path: str, categorization_method: str = "ollama") -> Dict[str, Any]:
        """Executa análise financeira completa de forma assíncrona."""
        try:
            # ETAPA 1: Construir perfil
            profile_tool = StandaloneUserProfileBuilderTool()
            profile_result = profile_tool._run(user_data_json=self.user_data)
            profile_data = json.loads(profile_result)
            if not profile_data.get("ok"):
                raise Exception(f"Erro ao construir perfil: {profile_data.get('error')}")

            # ETAPA 2 e 3: Pipeline CrewAI
            data_extractor = self.create_data_extractor_agent()
            financial_advisor = self.create_financial_advisor_agent()

            extract_task = self.create_extract_task(
                agent=data_extractor,
                csv_file_path=csv_file_path,
                categorization_method=categorization_method
            )

            profile_min = json.dumps(profile_data, ensure_ascii=False, separators=(",", ":"))
            advice_task = self.create_advice_task(
                agent=financial_advisor,
                profile_json=profile_min,
                transactions_json=None
            )
            
            advice_task.context = [extract_task]

            # Criar e executar crew
            crew_pipeline = Crew(
                agents=[data_extractor, financial_advisor],
                tasks=[extract_task, advice_task],
                process=Process.sequential,
                llm=llm,
                memory=True,
                shared_memory=True,
                verbose=True
            )

            pipeline_result = crew_pipeline.kickoff()

            # Processar resultados
            extract_result = extract_task.output.raw if hasattr(extract_task, 'output') else "{}"
            advice_result = advice_task.output.raw if hasattr(advice_task, 'output') else "{}"

            extract_result_clean = self._clean_json_text(extract_result)
            advice_result_clean = self._clean_json_text(advice_result)

            try:
                extract_data = json.loads(extract_result_clean)
            except json.JSONDecodeError:
                extract_data = {"ok": False, "error": "Falha ao extrair dados"}

            try:
                advice_data = json.loads(advice_result_clean)
            except json.JSONDecodeError:
                advice_data = {"ok": False, "error": "Falha ao gerar conselhos"}

            # ETAPA 4: Compilar dashboard
            dashboard_tool = DashboardDataCompilerTool()
            advice_for_dashboard = json.dumps({"advice": advice_data}, ensure_ascii=False)
            
            dashboard_result = dashboard_tool._run(
                transactions_json=extract_result_clean,
                advice_json=advice_for_dashboard,
                evaluation_json=json.dumps({
                    "ok": True,
                    "message": "LLM local executado com sucesso",
                    "model_used": "ollama/gemma3"
                })
            )

            dashboard_data = json.loads(dashboard_result)

            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "profile": profile_data,
                "transactions": extract_data,
                "advice": advice_data,
                "dashboard": dashboard_data,
                "metadata": {
                    "csv_file": csv_file_path,
                    "user_data": self.user_data,
                    "llm_model": "ollama/gemma3"
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# ============================================================================
# FUNÇÕES HELPER
# ============================================================================

def save_llm_response_to_db(
    profile_id: int, 
    crew_results: Dict[str, Any], 
    db: Session
) -> None:
    """
    Salva os resultados da análise CrewAI na tabela llm_responses.
    
    Args:
        profile_id: ID do perfil financeiro
        crew_results: Resultados completos da análise CrewAI
        db: Sessão do banco de dados
    """
    try:
        # Preparar dados das respostas LLM individuais
        llm_responses_data = []
        
        # Resposta do BankStatementParser (extração de transações)
        if crew_results.get("transactions", {}).get("ok"):
            transactions_response = {
                "llm_name": "BankStatementParser_Gemma3",
                "task": "transaction_extraction_categorization",
                "advice": json.dumps(crew_results["transactions"], ensure_ascii=False),
                "confidence_score": 0.9,  # Alta confiança para dados estruturados
                "processing_time": 0.0,  # Tempo será calculado se disponível
                "timestamp": crew_results.get("timestamp"),
                "success": True
            }
            llm_responses_data.append(transactions_response)
        
        # Resposta do FinancialAdvisor (conselhos financeiros)
        if crew_results.get("advice", {}).get("resumo"):
            advisor_response = {
                "llm_name": "FinancialAdvisor_Gemma3",
                "task": "financial_advice_generation",
                "advice": json.dumps(crew_results["advice"], ensure_ascii=False),
                "confidence_score": 0.85,  # Boa confiança para conselhos
                "processing_time": 0.0,
                "timestamp": crew_results.get("timestamp"),
                "success": True
            }
            llm_responses_data.append(advisor_response)
        
        # Determinar a melhor resposta (priorizar conselhos financeiros)
        best_response = advisor_response if crew_results.get("advice", {}).get("resumo") else transactions_response
        
        # Preparar métricas de comparação
        score_metrics = {
            "overall_success": crew_results.get("success", False),
            "total_agents": 2,
            "successful_agents": len(llm_responses_data),
            "profile_completeness": {
                "has_transactions": bool(crew_results.get("transactions", {}).get("transacoes")),
                "has_advice": bool(crew_results.get("advice", {}).get("resumo")),
                "has_dashboard": bool(crew_results.get("dashboard", {}).get("ok"))
            },
            "data_quality": {
                "transaction_count": len(crew_results.get("transactions", {}).get("transacoes", [])),
                "categories_count": len(crew_results.get("transactions", {}).get("totais_por_categoria", [])),
                "advice_items": len(crew_results.get("advice", {}).get("plano", {}).get("agora", []))
            },
            "execution_timestamp": crew_results.get("timestamp"),
            "llm_model": crew_results.get("metadata", {}).get("llm_model", "ollama/gemma3")
        }
        
        # Criar entrada na tabela llm_responses
        llm_response_entry = LLMResponse(
            perfil_financeiro_id=profile_id,
            llm_responses=json.dumps(llm_responses_data, ensure_ascii=False, indent=2),
            default_response=json.dumps(best_response, ensure_ascii=False, indent=2),
            score=json.dumps(score_metrics, ensure_ascii=False, indent=2)
        )
        
        db.add(llm_response_entry)
        db.commit()
        db.refresh(llm_response_entry)
        
        print(f"✅ LLM Response salva no banco: ID {llm_response_entry.id}")
        
    except Exception as e:
        print(f"❌ Erro ao salvar LLM Response: {str(e)}")
        db.rollback()
        raise

# ============================================================================
# SCHEMAS PARA API
# ============================================================================

class FinancialAnalysisRequest(BaseModel):
    """Schema para requisição de análise financeira."""
    user_data: Dict[str, Any] = Field(description="Dados do perfil financeiro do usuário")
    categorization_method: str = Field(default="ollama", description="Método de categorização")
    
class FinancialAnalysisResponse(BaseModel):
    """Schema para resposta de análise financeira."""
    success: bool
    timestamp: str
    profile: Optional[Dict[str, Any]] = None
    transactions: Optional[Dict[str, Any]] = None
    advice: Optional[Dict[str, Any]] = None
    dashboard: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ProcessingStatus(BaseModel):
    """Status de processamento."""
    status: str
    progress: int
    message: str
    created_at: str

# ============================================================================
# ROTAS DA API
# ============================================================================

# Rotas básicas
@app.get("/")
async def root():
    """Endpoint raiz para verificar se a API está funcionando"""
    return {"message": "Financial Planning AI API com CrewAI funcionando!", "status": "online", "version": "2.0.0"}

@app.get("/health")
async def health_check():
    """Health check da API"""
    return {"status": "healthy", "service": "financial-ai-api", "crewai": "enabled"}
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
async def login_user(request: Request, db: Session = Depends(get_db)):
    """Autentica um usuário e retorna token de acesso"""
    try:
        # Verificar Content-Type e processar accordingly
        content_type = request.headers.get("content-type", "")
        print(f"\n=== LOGIN DEBUG ===")
        print(f"Content-Type: {content_type}")
        
        if "application/json" in content_type:
            # Processar como JSON
            body = await request.body()
            print(f"Body raw: {body}")
            data = json.loads(body.decode('utf-8'))
            print(f"Data parsed: {data}")
            
            email = data.get("email")
            password = data.get("password")
        # elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        #     # Processar como form data
        #     form = await request.form()
        #     email = form.get("email")
        #     password = form.get("password")
        #     print(f"Form data: email={email}, password=***")
        else:
            raise HTTPException(status_code=400, detail="Content-Type não suportado")
        
        if not email or not password:
            raise HTTPException(status_code=400, detail="Email e senha são obrigatórios")
        
        print(f"Processando login para: {email}")
        print("===================\n")
        
        # Buscar usuário por email
        user = db.query(Usuario).filter(Usuario.email == email).first()
        
        if not user or not verify_password(password, user.password):
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
        print(f"ERRO NO LOGIN: {str(e)}")
        print(f"TIPO DO ERRO: {type(e)}")
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

@app.get("/")
async def root():
    """Endpoint raiz para verificar se a API está funcionando"""
    return {"message": "API de Autenticação funcionando!", "status": "online"}

@app.post("/api/test-json")
async def test_json(data: dict):
    """Endpoint de teste para JSON"""
    print(f"Recebido: {data}")
    return {"received": data, "message": "JSON recebido com sucesso"}

@app.get("/health")
async def health_check():
    """Health check da API"""
    return {"status": "healthy", "service": "auth-api"}

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

@app.post("/api/upload-extract", response_model=UploadResponse)
async def upload_bank_statement(
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Upload e processamento de extrato bancário"""
    try:
        # Validar tipo de arquivo
        allowed_extensions = ['.csv', '.xlsx', '.xls', '.ofx', '.pdf']
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

# ============================================================================
# NOVAS ROTAS CREWAI
# ============================================================================

@app.post("/api/financial/analyze-with-crewai", response_model=FinancialAnalysisResponse)
async def analyze_financial_data_with_crewai(
    background_tasks: BackgroundTasks,
    request: FinancialAnalysisRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Executa análise financeira completa usando CrewAI"""
    try:
        # Buscar perfil financeiro do usuário
        profile = db.query(FinancialProfile).filter(
            FinancialProfile.usuario_id == current_user_id
        ).first()
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Perfil financeiro não encontrado. Complete seu perfil primeiro."
            )

        # Verificar se há extrato carregado
        extrato_data = json.loads(profile.extrato) if profile.extrato else {}
        if not extrato_data.get("file_info"):
            raise HTTPException(
                status_code=400,
                detail="Nenhum extrato bancário carregado. Faça upload do extrato primeiro."
            )

        # Obter caminho do arquivo CSV
        csv_file_path = extrato_data["file_info"]["file_path"]
        if not os.path.exists(csv_file_path):
            raise HTTPException(
                status_code=404,
                detail="Arquivo de extrato não encontrado no servidor"
            )

        # Preparar dados do usuário
        questionnaire_data = json.loads(profile.questionnaire_data)
        objetivo_data = json.loads(profile.objetivo) if profile.objetivo else {}
        
        user_data = {
            "user_id": current_user_id,
            "age": questionnaire_data.get("idade", 25),
            "monthly_income": questionnaire_data.get("renda_mensal", 3000),
            "dependents": questionnaire_data.get("dependentes", []),
            "risk_profile": questionnaire_data.get("perfil_risco", "moderado"),
            "financial_goal": objetivo_data.get("descricao", "Reserva de emergência"),
            "target_amount": objetivo_data.get("valor_objetivo", 1000),
            "time_frame": objetivo_data.get("prazo", "12 meses"),
            "debt_to_income_ratio": questionnaire_data.get("divida_renda_ratio", 0.3),
            "liquid_assets": questionnaire_data.get("patrimonio_liquido", 5000),
            "transportation_methods": questionnaire_data.get("meio_transporte", "Transporte público")
        }

        # Criar e executar crew
        crew_system = FinancialAdvisorCrew(user_data)
        
        print(f"🚀 Iniciando análise CrewAI para usuário {current_user_id}")
        
        results = await crew_system.run_analysis(
            csv_file_path=csv_file_path,
            categorization_method=request.categorization_method
        )

        if results["success"]:
            # Atualizar perfil com dados da análise
            # if not hasattr(profile, 'analise_resultado'):
            #     # Se não existe a coluna, adicionar aos dados do extrato
            #     extrato_data["analysis_results"] = analysis_data
            #     profile.extrato = json.dumps(extrato_data, ensure_ascii=False)
            # else:
            #     # Se existe a coluna específica, usar ela
            #     profile.analise_resultado = json.dumps(analysis_data, ensure_ascii=False)
            
            # ✅ NOVO: Salvar respostas LLM na tabela llm_responses
            try:
                save_llm_response_to_db(profile.id, results, db)
                print(f"✅ Respostas LLM salvas na tabela llm_responses para perfil {profile.id}")
            except Exception as llm_save_error:
                print(f"⚠️ Erro ao salvar LLM responses (análise continua): {str(llm_save_error)}")
                # Não interrompe o fluxo principal em caso de erro na gravação LLM
            
            db.commit()
            
            print(f"✅ Análise CrewAI concluída com sucesso para usuário {current_user_id}")

        return results

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro na análise CrewAI: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno na análise: {str(e)}")

@app.get("/api/dashboard/financial-analysis")
async def get_financial_analysis(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Endpoint para obter análise financeira completa para o dashboard"""
    try:
        # Buscar perfil financeiro do usuário
        profile = db.query(FinancialProfile).filter(FinancialProfile.usuario_id == user_id).first()
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Perfil financeiro não encontrado. Complete seu perfil primeiro."
            )
        
        # Verificar se existe análise prévia
        extrato_data = json.loads(profile.extrato) if profile.extrato else {}
        analysis_results = extrato_data.get("analysis_results")
        
        if not analysis_results or not analysis_results.get("processed"):
            # Se não há análise, retornar dados básicos/fallback
            return {
                "dashboard": {
                    "dashboard_data": {
                        "transactions_analysis": {
                            "summary": {
                                "total_transactions": 0,
                                "total_income": 0,
                                "total_expenses": 0
                            },
                            "categories_breakdown": []
                        },
                        "financial_health": {
                            "score": 50,
                            "status": "Aguardando análise"
                        },
                        "alerts_and_notifications": {
                            "urgent": ["Execute a análise financeira para obter insights personalizados"],
                            "info": []
                        }
                    }
                },
                "message": "Análise não executada. Use o endpoint /api/financial/analyze-with-crewai"
            }
        
        # Buscar arquivo de análise mais recente
        analysis_files = [f for f in os.listdir('.') if f.startswith('financial_analysis_') and f.endswith('.json')]
        
        if analysis_files:
            # Pegar o arquivo mais recente
            latest_file = sorted(analysis_files, reverse=True)[0]
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            
            return {
                "dashboard": analysis_data.get("dashboard", {}),
                "timestamp": analysis_data.get("timestamp"),
                "source": "crewai_analysis",
                "file": latest_file
            }
        else:
            # Fallback com dados básicos
            questionnaire_data = json.loads(profile.questionnaire_data) if profile.questionnaire_data else {}
            
            return {
                "dashboard": {
                    "dashboard_data": {
                        "transactions_analysis": {
                            "summary": {
                                "total_transactions": 0,
                                "total_income": questionnaire_data.get("renda_mensal", 0),
                                "total_expenses": questionnaire_data.get("renda_mensal", 0) * 0.7
                            },
                            "categories_breakdown": []
                        },
                        "financial_health": {
                            "score": 60,
                            "status": "Dados preliminares"
                        },
                        "alerts_and_notifications": {
                            "urgent": [],
                            "info": ["Execute análise completa para dados detalhados"]
                        }
                    }
                },
                "message": "Dados de fallback. Para análise completa, execute processamento CrewAI"
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar análise financeira: {str(e)}")

@app.get("/api/financial/analysis-status/{user_id}")
async def get_analysis_status(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Retorna o status da análise financeira do usuário"""
    try:
        # Verificar permissão (usuário só pode ver próprio status)
        if user_id != current_user_id:
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        profile = db.query(FinancialProfile).filter(
            FinancialProfile.usuario_id == user_id
        ).first()
        
        if not profile:
            return ProcessingStatus(
                status="not_found",
                progress=0,
                message="Perfil financeiro não encontrado",
                created_at=datetime.now().isoformat()
            )
        
        extrato_data = json.loads(profile.extrato) if profile.extrato else {}
        analysis_results = extrato_data.get("analysis_results")
        
        if not analysis_results:
            return ProcessingStatus(
                status="pending",
                progress=0,
                message="Análise não iniciada",
                created_at=profile.data_criado.isoformat()
            )
        
        if analysis_results.get("processed"):
            return ProcessingStatus(
                status="completed",
                progress=100,
                message="Análise concluída com sucesso",
                created_at=analysis_results.get("timestamp", datetime.now().isoformat())
            )
        else:
            return ProcessingStatus(
                status="processing",
                progress=50,
                message="Análise em andamento",
                created_at=analysis_results.get("timestamp", datetime.now().isoformat())
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/api/llm/responses/{profile_id}")
async def get_llm_responses(
    profile_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Retorna as respostas LLM salvas para um perfil financeiro"""
    try:
        # Verificar se o perfil pertence ao usuário atual
        profile = db.query(FinancialProfile).filter(
            FinancialProfile.id == profile_id,
            FinancialProfile.usuario_id == current_user_id
        ).first()
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Perfil financeiro não encontrado ou acesso negado"
            )
        
        # Buscar respostas LLM mais recentes para este perfil
        llm_responses = db.query(LLMResponse).filter(
            LLMResponse.perfil_financeiro_id == profile_id
        ).order_by(LLMResponse.data_criado.desc()).limit(5).all()
        
        if not llm_responses:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma análise LLM encontrada para este perfil"
            )
        
        # Formatar dados para resposta
        responses_data = []
        for llm_resp in llm_responses:
            response_data = {
                "id": llm_resp.id,
                "timestamp": llm_resp.data_criado.isoformat(),
                "llm_responses": json.loads(llm_resp.llm_responses),
                "default_response": json.loads(llm_resp.default_response),
                "score_metrics": json.loads(llm_resp.score)
            }
            responses_data.append(response_data)
        
        return {
            "profile_id": profile_id,
            "total_analyses": len(responses_data),
            "latest_analysis": responses_data[0] if responses_data else None,
            "all_analyses": responses_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/api/llm/latest-response")
async def get_latest_llm_response(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Retorna a resposta LLM mais recente do usuário atual"""
    try:
        # Buscar perfil do usuário
        profile = db.query(FinancialProfile).filter(
            FinancialProfile.usuario_id == current_user_id
        ).first()
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Perfil financeiro não encontrado"
            )
        
        # Buscar resposta LLM mais recente
        latest_llm_response = db.query(LLMResponse).filter(
            LLMResponse.perfil_financeiro_id == profile.id
        ).order_by(LLMResponse.data_criado.desc()).first()
        
        if not latest_llm_response:
            return {
                "has_analysis": False,
                "message": "Nenhuma análise LLM encontrada. Execute uma análise primeiro."
            }
        
        return {
            "has_analysis": True,
            "analysis_id": latest_llm_response.id,
            "timestamp": latest_llm_response.data_criado.isoformat(),
            "llm_responses": json.loads(latest_llm_response.llm_responses),
            "best_response": json.loads(latest_llm_response.default_response),
            "quality_metrics": json.loads(latest_llm_response.score)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/api/test-crewai")
async def test_crewai_connection():
    """Testa a conexão com o sistema CrewAI"""
    try:
        # Teste básico das ferramentas
        test_data = {
            "user_id": 999,
            "age": 25,
            "monthly_income": 3000,
            "financial_goal": "Teste API",
            "target_amount": 1000,
            "time_frame": "6 meses"
        }
        
        profile_tool = StandaloneUserProfileBuilderTool()
        result = profile_tool._run(user_data_json=test_data)
        
        return {
            "crewai_status": "operational",
            "llm_model": "ollama/gemma3",
            "tools_available": ["BankStatementParserTool", "FinancialAdvisorTool", "DashboardDataCompilerTool"],
            "test_result": json.loads(result),
            "timestamp": datetime.now().isoformat(),
            "database_features": {
                "llm_responses_table": "enabled",
                "automatic_save": "enabled"
            }
        }
        
    except Exception as e:
        return {
            "crewai_status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)