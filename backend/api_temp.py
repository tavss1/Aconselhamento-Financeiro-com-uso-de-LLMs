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

# Configuração LLM 
os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["CREWAI_LLM_PROVIDER"] = "ollama"
os.environ["CREWAI_USE_LOCAL_LLM_ONLY"] = "true"


app = FastAPI(
    title="Aconselhamento Financeiro com LLMs API - CrewAI Integration",
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

class UserProfileBuilderToolSchema(BaseModel):
    user_data_json: Any = Field(description="JSON string OU objeto dict com dados do usuário")

class UserProfileBuilderTool(BaseTool):
    """Ferramenta para construir perfil financeiro a partir de dados diretos."""
    
    name: str = "UserProfileBuilder"
    description: str = "Constrói perfil financeiro normalizado a partir de dados do usuário"
    args_schema = UserProfileBuilderToolSchema

    def _run(self, user_data_json: Any) -> str:
        """Constrói perfil financeiro."""
        try:
            if isinstance(user_data_json, dict):
                user_data = user_data_json
            else:
                user_data = json.loads(user_data_json)
            
            # Processar dados conforme estrutura do frontend
            dependents = user_data.get("dependents", [])
            # Calcular total de dependentes baseado na estrutura [{"type": "nenhum", "quantity": 0}]
            total_dependents = 0
            if isinstance(dependents, list) and len(dependents) > 0:
                for dep in dependents:
                    if isinstance(dep, dict) and dep.get("type") != "nenhum":
                        total_dependents += int(dep.get("quantity", 0))
            
            # Validar e converter dados obrigatórios (sem valores padrão)
            if not user_data.get("age"):
                raise ValueError("Idade é obrigatória")
            idade = int(user_data.get("age"))
            
            if not user_data.get("monthly_income") or float(user_data.get("monthly_income")) <= 0:
                raise ValueError("Renda mensal é obrigatória e deve ser maior que zero")
            renda = float(user_data.get("monthly_income"))
            
            if not user_data.get("risk_profile"):
                raise ValueError("Perfil de risco é obrigatório")
            risk_profile = user_data.get("risk_profile")
            
            transportation_methods = user_data.get("transportation_methods", "")

            mensalidade_faculdade = user_data.get("mensalidade_faculdade")
            valor_mensalidade = user_data.get("valor_mensalidade", 0)

            if not user_data.get("financial_goal"):
                raise ValueError("Objetivo financeiro é obrigatório")
            financial_goal = user_data.get("financial_goal")
            
            if not user_data.get("target_amount") or float(user_data.get("target_amount")) <= 0:
                raise ValueError("Valor objetivo é obrigatório e deve ser maior que zero")
            target_amount = float(user_data.get("target_amount"))
            
            if not user_data.get("time_frame"):
                raise ValueError("Prazo para objetivo é obrigatório")
            time_frame = user_data.get("time_frame")
            
            # Cálculos financeiros
            if not user_data.get("user_id"):
                raise ValueError("ID do usuário é obrigatório")
            
            #todo adicionar campo de mensalidade
            perfil = {
                "ok": True,
                "timestamp": datetime.now().isoformat(),
                "profile_id": f"api_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "usuario_id": user_data.get("user_id"),
                "dados_pessoais": {
                    "idade": idade,
                    "renda_mensal": renda,
                    "total_dependentes": total_dependents,
                    "detalhes_dependentes": dependents,
                    "risk_profile": risk_profile,
                    "transportation_methods": transportation_methods,
                    "mensalidade_faculdade": mensalidade_faculdade,
                    "valor_mensalidade": valor_mensalidade,
                },
                "objetivo": {
                    "descricao": financial_goal,
                    "valor_objetivo": target_amount,
                    "prazo": time_frame,
                },
            }
            
            return json.dumps(perfil, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Erro ao construir perfil: {str(e)}"})
    
class FinancialAdvisorCrew:
    """Crew de aconselhamento financeiro para API integrada."""
    
    def __init__(self, user_data: Dict[str, Any], selected_model: str):
        self.user_data = user_data
        self.user_data_json = json.dumps(user_data, ensure_ascii=False)
        self.selected_model = selected_model
        self.llm=LLM(
            model=f"ollama/{selected_model}",
            base_url="http://localhost:11434"
        )

    def create_data_extractor_agent(self) -> Agent:
        """Cria agente extrator de dados financeiros."""
        return Agent(
            role="Extrator Financeiro de Transações",
            goal="Extrair e categorizar transações financeiras de extratos bancários CSV, identificando padrões de gastos e oportunidades de economia.",
            backstory=(
                "Você é um especialista em finanças pessoais e tem como missão identificar padrões "
                "de consumo e categorizar transações bancárias de forma precisa e organizada. "
                "Seu trabalho é a base para que o consultor financeiro possa gerar conselhos personalizados."
            ),
            verbose=True,
            llm=self.llm,
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
            llm=self.llm,
            tools=[FinancialAdvisorTool()],
            allow_delegation=False,
            memory=False,
            max_iter=1
        )

    def create_extract_task(self, agent: Agent, csv_file_path: str, categorization_method: str = "ollama", selected_model: str = "gemma3") -> Task:
        """Cria task de extração de dados."""
        return Task(
            description=f"""
            IMPORTANTE: Você deve processar o extrato bancário diretamente usando a ferramenta BankStatementParserTool E RETORNAR.
            EXATAMENTE a saída JSON da ferramenta, sem interpretação ou reformatação.
            
            Action: BankStatementParserTool
            Action Input: {{
            "file_path": "{csv_file_path}",
            "llm_enhanced": false,
            "categorization_method": "{categorization_method}",
            "ollama_model": "{selected_model}",
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
            llm=self.llm
        )

    def create_advice_task(self, agent: Agent, profile_json: str, transactions_json: str, selected_model: str = "gemma3") -> Task:
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

        # Escapar aspas duplas no profile_json para evitar problemas de formatação
        escaped_profile_json = profile_json.replace('"', '\\"')
        
        description = f"""
            GERAR CONSELHOS FINANCEIROS PERSONALIZADOS

            OBJETIVO PRINCIPAL: {objetivo_desc} | META: R$ {objetivo_valor:,.2f} | PRAZO: {objetivo_prazo}

            Você é um consultor financeiro especializado. Sua tarefa é usar a ferramenta FinancialAdvisorTool 
            para gerar conselhos personalizados com base no perfil do usuário e nas transações categorizadas 
            obtidas da tarefa anterior.

            IMPORTANTE: Use EXATAMENTE este formato para invocar a ferramenta com os dados da tarefa anterior:

            Action: FinancialAdvisorTool
            Action Input: {{
                "profile_json": "{escaped_profile_json}",
                "transactions_json": "{{json.dumps(context[extract_task])}}",
                "ollama_model": "{selected_model}",
            }}

            INSTRUÇÕES CRÍTICAS:
            1. Substitua "{{context[extract_task]}}" pelo JSON completo da tarefa de extração anterior
            2. Este JSON DEVE conter "transacoes" (array de transações) e "totais_por_categoria" (resumo)
            3. Use o perfil fornecido para o campo "profile_json"
            4. Mantenha o formato JSON válido sem quebras de linha

            A resposta deve ser um JSON estruturado com:
            - resumo: análise da situação financeira
            - alertas: avisos importantes
            - plano: ações para agora, 30 dias e 12 meses
            - metas_mensuraveis: objetivos quantificáveis

            ATENÇÃO: É OBRIGATÓRIO usar o JSON completo da extração anterior que contém 
            tanto as transações individuais quanto o resumo por categoria.
        """
        return Task(
            description=description,
            expected_output="JSON válido contendo campos: resumo, alertas, plano, metas_mensuraveis.",
            agent=agent,
            tools=[FinancialAdvisorTool()],
            llm=self.llm,
            max_iter=1
        )
    
    def create_advice_task_with_data(self, agent: Agent, profile_json: str, transactions_json: str, selected_model: str = "gemma3") -> Task:
        """Cria task de geração de conselhos com dados explícitos."""
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

        # Escapar aspas duplas nos JSONs
        escaped_profile_json = profile_json.replace('"', '\\"')
        escaped_transactions_json = transactions_json.replace('"', '\\"')
        
        description = f"""
            GERAR CONSELHOS FINANCEIROS PERSONALIZADOS

            OBJETIVO PRINCIPAL: {objetivo_desc} | META: R$ {objetivo_valor:,.2f} | PRAZO: {objetivo_prazo}

            Você é um consultor financeiro especializado. Use a ferramenta FinancialAdvisorTool 
            para gerar conselhos personalizados com os dados fornecidos explicitamente.

            IMPORTANTE: Use EXATAMENTE este formato:

            Action: FinancialAdvisorTool
            Action Input: {{
                "profile_json": "{escaped_profile_json}",
                "transactions_json": "{escaped_transactions_json}",
                "ollama_model": "{selected_model}"
            }}

            Os dados já estão prontos e válidos. Não modifique os JSONs fornecidos.
            
            A resposta deve ser um JSON estruturado com:
            - resumo: análise da situação financeira
            - alertas: avisos importantes
            - plano: ações para agora, 30 dias e 12 meses
            - metas_mensuraveis: objetivos quantificáveis
        """
        return Task(
            description=description,
            expected_output="JSON válido contendo campos: resumo, alertas, plano, metas_mensuraveis.",
            agent=agent,
            tools=[FinancialAdvisorTool()],
            llm=self.llm,
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

    def _normalize_extracted_result(self, extract_data: dict) -> dict:
        """Normaliza resultado da extração para schema canônico."""
        print(f"[INFO] Normalizando dados extraídos...")
        
        # Criar estrutura canônica
        normalized = {
            "ok": True,
            "timestamp": extract_data.get("timestamp", datetime.now().isoformat()),
            "transacoes": [],
            "totais_por_categoria": [],
            "n_transacoes": 0
        }
        
        # 1. Processar transações
        # Tentar diferentes chaves para transações
        transactions_sources = [
            extract_data.get("transacoes", []),
            extract_data.get("transactions", []),
            extract_data.get("items", [])
        ]
        
        for source in transactions_sources:
            if isinstance(source, list) and len(source) > 0:
                normalized["transacoes"] = source
                break
        
        # 2. Processar categorias
        # Verificar diferentes estruturas de categoria
        if "totais_por_categoria" in extract_data:
            normalized["totais_por_categoria"] = extract_data["totais_por_categoria"]
        elif "transaction_summary" in extract_data or "expenses_by_category" in extract_data or "revenues" in extract_data:
            # Estrutura alternativa: transaction_summary.categories
            summary = extract_data.get("transaction_summary") or extract_data.get("expenses_by_category") or extract_data.get("revenues")
            if isinstance(summary, dict) and "categories" in summary:
                categories = summary["categories"]
                if isinstance(categories, list):
                    # Mapear para formato padrão
                    normalized["totais_por_categoria"] = [
                        {
                            "categoria": cat.get("category", cat.get("name", "Outros")),
                            "valor": cat.get("total_value", cat.get("valor", cat.get("amount", 0)))
                        }
                        for cat in categories
                    ]
        
        # 3. Atualizar contadores
        normalized["n_transacoes"] = len(normalized["transacoes"])
        
        # 4. Garantir que pelo menos uma das estruturas está presente
        has_transactions = len(normalized["transacoes"]) > 0
        has_categories = len(normalized["totais_por_categoria"]) > 0
        
        if has_transactions or has_categories:
            normalized["ok"] = True
            print(f"[INFO] Normalização concluída: {normalized['n_transacoes']} transações, {len(normalized['totais_por_categoria'])} categorias")
        else:
            normalized["ok"] = False
            normalized["error"] = "Nenhuma transação ou categoria encontrada"
            print(f"[WARNING] Normalização falhou: dados insuficientes")
        
        return normalized

    async def run_analysis(self, csv_file_path: str, categorization_method: str = "ollama", selected_model: str = "gemma3") -> Dict[str, Any]:
        """Executa análise financeira completa de forma assíncrona."""
        try:
            print(f"🚀 DEBUG - Iniciando run_analysis com user_data: {self.user_data}")
            print(f"🎯 DEBUG - run_analysis iniciado com modelo: {selected_model}")
            print(f"🎯 DEBUG - Método de categorização: {categorization_method}")
            
            # ETAPA 1: Construir perfil
            profile_tool = UserProfileBuilderTool()
            profile_result = profile_tool._run(user_data_json=self.user_data)
            
            print(f"🔍 DEBUG - Profile result raw: {profile_result}")
            
            profile_data = json.loads(profile_result)
            if not profile_data.get("ok"):
                raise Exception(f"Erro ao construir perfil: {profile_data.get('error')}")

            print(f"✅ DEBUG - Perfil construído com sucesso: {json.dumps(profile_data, ensure_ascii=False, indent=2)}")

            # ETAPA 2: Pipeline CrewAI em etapas separadas para controle de dados
            data_extractor = self.create_data_extractor_agent()
            financial_advisor = self.create_financial_advisor_agent()

            # Executar extract_task primeiro isoladamente
            extract_task = self.create_extract_task(
                agent=data_extractor,
                csv_file_path=csv_file_path,
                categorization_method=categorization_method,
                selected_model=selected_model
            )

            print(f"🚀 DEBUG - Executando extract_task...")
            
            # Executar apenas extract_task
            extract_crew = Crew(
                agents=[data_extractor],
                tasks=[extract_task],
                process=Process.sequential,
                llm=self.llm,
                memory=False,
                verbose=True
            )
            
            extract_result_raw = extract_crew.kickoff()
            extract_result_clean = self._clean_json_text(extract_task.output.raw if hasattr(extract_task, 'output') else str(extract_result_raw))
            
            print(f"🔍 DEBUG - Extract result clean: {extract_result_clean[:300]}...")
            
            # Parse dos dados de extração
            try:
                extract_data = json.loads(extract_result_clean)
                print(f"✅ DEBUG - Extract data parsed successfully")
                
                # NOVO: Normalizar dados extraídos
                extract_data = self._normalize_extracted_result(extract_data)
                
                print(f"🔍 DEBUG - Transações encontradas: {len(extract_data.get('transacoes', []))}")
                print(f"� DEBUG - Categorias encontradas: {len(extract_data.get('totais_por_categoria', []))}")
                
                # NOVA VALIDAÇÃO: Aceitar se temos categorias OU transações
                has_transactions = len(extract_data.get("transacoes", [])) > 0
                has_categories = len(extract_data.get("totais_por_categoria", [])) > 0
                
                if not extract_data.get("ok") or (not has_transactions and not has_categories):
                    print(f"❌ DEBUG - Dados insuficientes: transações={has_transactions}, categorias={has_categories}")
                    raise Exception("Nenhuma transação ou categoria encontrada após normalização")
                
                # Sucesso - temos pelo menos categorias ou transações
                print(f"✅ DEBUG - Dados válidos encontrados: transações={has_transactions}, categorias={has_categories}")
                
            except json.JSONDecodeError as e:
                print(f"❌ DEBUG - Extract JSON decode error: {e}")
                print(f"🔍 DEBUG - Raw data que causou erro: {extract_result_clean[:300]}...")
                extract_data = {"ok": False, "error": "Falha ao extrair dados", "raw_data": extract_result_clean[:500]}
                
            except Exception as e:
                print(f"❌ DEBUG - Erro geral na extração: {e}")
                extract_data = {"ok": False, "error": str(e)}

            # Verificar se temos dados válidos antes de continuar
            if not extract_data.get("ok"):
                print("⚠️ DEBUG - Dados de extração inválidos, mas continuando com fallback...")
                # Criar dados mínimos para teste
                extract_data = {
                    "ok": True,
                    "transacoes": [{"data": "01/01/2024", "valor": 0, "descricao": "Teste", "categoria": "Outros"}],
                    "totais_por_categoria": [{"categoria": "Outros", "valor": 0}],
                    "n_transacoes": 1
                }
            
            print(f"🔍 DEBUG - Status final dos dados: OK={extract_data.get('ok')}, Transações={len(extract_data.get('transacoes', []))}")

            # ETAPA 3: Executar advice_task com dados explícitos
            print(f"🎯 DEBUG - Executando advice_task com dados explícitos...")
            
            profile_min = json.dumps(profile_data, ensure_ascii=False, separators=(",", ":"))
            extract_data_str = json.dumps(extract_data, ensure_ascii=False, separators=(",", ":"))
            
            advice_task = self.create_advice_task_with_data(
                agent=financial_advisor,
                profile_json=profile_min,
                transactions_json=extract_data_str,
                selected_model=selected_model
            )

            # Executar advice_task
            advice_crew = Crew(
                agents=[financial_advisor],
                tasks=[advice_task],
                process=Process.sequential,
                llm=self.llm,
                memory=False,
                verbose=True
            )
            
            advice_result_raw = advice_crew.kickoff()
            advice_result_clean = self._clean_json_text(advice_task.output.raw if hasattr(advice_task, 'output') else str(advice_result_raw))

            print(f"🔍 DEBUG - Advice result clean: {advice_result_clean[:300]}...")

            try:
                advice_data = json.loads(advice_result_clean)
                print(f"✅ DEBUG - Advice data parsed successfully")
                print(f"🔍 DEBUG - Conselhos gerados: {'Sim' if advice_data.get('resumo') else 'Não'}")
            except json.JSONDecodeError as e:
                print(f"❌ DEBUG - Advice JSON decode error: {e}")
                print(f"🔍 DEBUG - Tentando extrair dados parciais do advice_result_clean...")
                # Tentar extrair dados parciais mesmo com erro
                advice_data = {"ok": False, "error": "Falha ao gerar conselhos", "raw_data": advice_result_clean[:500]}

            # ETAPA 4: Compilar dashboard
            dashboard_tool = DashboardDataCompilerTool()
            
            # Garantir que advice_data tem a estrutura correta
            if "advice" not in advice_data:
                advice_for_dashboard = json.dumps({"advice": advice_data}, ensure_ascii=False)
            else:
                advice_for_dashboard = json.dumps(advice_data, ensure_ascii=False)
            
            print(f"🔍 DEBUG - Dados para dashboard - Advice: {len(advice_for_dashboard)} chars")
            print(f"🔍 DEBUG - Dados para dashboard - Transactions: {len(extract_result_clean)} chars")
            
            try:
                dashboard_result = dashboard_tool._run(
                    transactions_json=extract_data,  # Usar dados normalizados
                    advice_json=advice_for_dashboard,
                    evaluation_json=json.dumps({
                        "ok": True,
                        "message": "LLM local executado com sucesso",
                        "model_used": "ollama/" + selected_model,
                    })
                )
                
                dashboard_data = json.loads(dashboard_result)
                print(f"✅ DEBUG - Dashboard compilado com sucesso")
                
            except Exception as e:
                print(f"❌ DEBUG - Erro na compilação do dashboard: {e}")
                dashboard_data = {
                    "ok": False,
                    "error": f"Erro no dashboard: {e}",
                    "dashboard_data": {"metadata": {"generated_at": datetime.now().isoformat()}}
                }

            print(f"🎉 DEBUG - Análise financeira completa concluída!")
            print(f"   ✅ Perfil: {'OK' if profile_data.get('ok') else 'ERRO'}")
            print(f"   ✅ Transações: {len(extract_data.get('transacoes', []))} processadas")
            print(f"   ✅ Conselhos: {'OK' if advice_data.get('ok') else 'ERRO'}")
            print(f"   ✅ Dashboard: {'OK' if dashboard_data.get('ok') else 'ERRO'}")

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
                    "llm_model": "ollama/" + selected_model,
                    "flow_completed": True
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
        # Extrair cada tipo de resposta
        transactions_data = crew_results.get("transactions", {})
        advice_data = crew_results.get("advice", {})
        dashboard_data = crew_results.get("dashboard", {})
        
        # Preparar respostas para cada coluna específica
        transactions_response = json.dumps(transactions_data, ensure_ascii=False, indent=2)
        advice_response = json.dumps(advice_data, ensure_ascii=False, indent=2)
        dashboard_response = json.dumps(dashboard_data, ensure_ascii=False, indent=2)
        
        # Preparar métricas de qualidade e comparação
        score_metrics = {
            "overall_success": crew_results.get("success", False),
            "execution_timestamp": crew_results.get("timestamp"),
            "llm_model": crew_results.get("metadata", {}).get("llm_model"),
            "data_quality": {
                "transactions": {
                    "success": bool(transactions_data.get("ok")),
                    "transaction_count": len(transactions_data.get("transacoes", [])),
                    "categories_count": len(transactions_data.get("totais_por_categoria", [])),
                    "total_amount": sum([cat.get("valor", 0) for cat in transactions_data.get("totais_por_categoria", [])]),
                    "has_raw_data": bool(transactions_data.get("raw_data"))
                },
                "advice": {
                    "success": bool(advice_data.get("resumo")),
                    "has_alerts": len(advice_data.get("alertas", [])) > 0,
                    "action_plans": {
                        "immediate": len(advice_data.get("plano", {}).get("agora", [])),
                        "monthly": len(advice_data.get("plano", {}).get("30_dias", [])),
                        "yearly": len(advice_data.get("plano", {}).get("12_meses", []))
                    },
                    "measurable_goals": len(advice_data.get("metas_mensuraveis", [])),
                    "has_raw_data": bool(advice_data.get("raw_data"))
                },
                "dashboard": {
                    "success": bool(dashboard_data.get("ok")),
                    "components_count": len(dashboard_data.get("dashboard_data", {}).keys()) if dashboard_data.get("dashboard_data") else 0,
                    "has_raw_data": bool(dashboard_data.get("raw_data"))
                }
            },
            "performance_metrics": {
                "total_agents_used": 2,
                "successful_operations": sum([
                    1 if transactions_data.get("ok") else 0,
                    1 if advice_data.get("resumo") else 0,
                    1 if dashboard_data.get("ok") else 0
                ]),
                "completion_rate": crew_results.get("success", False),
                "errors_encountered": {
                    "transactions_error": transactions_data.get("error"),
                    "advice_error": advice_data.get("error"),
                    "dashboard_error": dashboard_data.get("error")
                }
            }
        }
        
        # Determinar modelo de IA usado
        modelo_ia = crew_results.get("metadata", {}).get("llm_model")
        
        # Criar entrada na tabela llm_responses com a nova estrutura
        llm_response_entry = LLMResponse(
            perfil_financeiro_id=profile_id,
            modelo_ia=modelo_ia,
            transactions_response=transactions_response,
            advice_response=advice_response,
            dashboard_response=dashboard_response,
            score=json.dumps(score_metrics, ensure_ascii=False, indent=2)
        )
        
        db.add(llm_response_entry)
        db.commit()
        db.refresh(llm_response_entry)
        
        print(f"✅ LLM Response salva no banco com nova estrutura: ID {llm_response_entry.id}")
        print(f"📊 Modelo IA: {modelo_ia}")
        print(f"📈 Transações: {len(transactions_data.get('transacoes', []))} registros")
        print(f"💡 Conselhos: {'✅' if advice_data.get('resumo') else '❌'}")
        print(f"📋 Dashboard: {'✅' if dashboard_data.get('ok') else '❌'}")
        
        # Debug adicional quando há problemas
        if not transactions_data.get("ok"):
            print(f"⚠️ Erro nas transações: {transactions_data.get('error', 'Desconhecido')}")
        if not advice_data.get("resumo"):
            print(f"⚠️ Erro nos conselhos: {advice_data.get('error', 'Desconhecido')}")
        if not dashboard_data.get("ok"):
            print(f"⚠️ Erro no dashboard: {dashboard_data.get('error', 'Desconhecido')}")
        
    except Exception as e:
        print(f"❌ Erro ao salvar LLM Response: {str(e)}")
        db.rollback()
        raise

# ============================================================================
# SCHEMAS PARA API
# ============================================================================

class FinancialAnalysisRequest(BaseModel):
    """Schema para requisição de análise financeira."""
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

@app.get("/api/auth/check-analysis-status")
async def check_analysis_status(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Verifica se o usuário possui análise CrewAI concluída"""
    try:
        # Buscar perfil do usuário
        profile = db.query(FinancialProfile).filter(
            FinancialProfile.usuario_id == current_user_id
        ).first()
        
        if not profile:
            return {
                "has_analysis": False,
                "has_profile": False,
                "should_redirect_to": "wizard",
                "message": "Perfil financeiro não encontrado"
            }
        
        # Buscar análise mais recente
        latest_analysis = db.query(LLMResponse).filter(
            LLMResponse.perfil_financeiro_id == profile.id
        ).order_by(LLMResponse.data_criado.desc()).first()
        
        if not latest_analysis:
            return {
                "has_analysis": False,
                "has_profile": True,
                "should_redirect_to": "wizard", 
                "message": "Nenhuma análise encontrada"
            }
        
        # Verificar se tem dashboard_response preenchido
        has_dashboard_data = (
            latest_analysis.dashboard_response and 
            latest_analysis.dashboard_response.strip() != "" and
            latest_analysis.dashboard_response != "null"
        )
        
        return {
            "has_analysis": has_dashboard_data,
            "has_profile": True,
            "should_redirect_to": "dashboard" if has_dashboard_data else "wizard",
            "analysis_date": latest_analysis.data_criado.isoformat() if latest_analysis else None,
            "message": "Análise encontrada" if has_dashboard_data else "Análise incompleta"
        }
        
    except Exception as e:
        print(f"Erro ao verificar status de análise: {e}")
        return {
            "has_analysis": False,
            "has_profile": False,
            "should_redirect_to": "wizard",
            "message": f"Erro interno: {str(e)}"
        }

@app.get("/")
async def root():
    """Endpoint raiz para verificar se a API está funcionando"""
    return {"message": "API de Autenticação funcionando!", "status": "online"}

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

    categorization_method = request.categorization_method

    if "/" in categorization_method:
        method, selected_model = categorization_method.split("/", 1)
    else:
        method = categorization_method
        selected_model = "gemma3"  # padrão

    print(f"🔍 DEBUG - Método: {method}, Modelo: {selected_model}")

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

        # Preparar dados do usuário conforme estrutura do frontend
        questionnaire_data = json.loads(profile.questionnaire_data) if profile.questionnaire_data else {}
        objetivo_data = json.loads(profile.objetivo) if profile.objetivo else {}
        
        print(f"🔍 DEBUG - Questionnaire data: {questionnaire_data}")
        print(f"🔍 DEBUG - Objetivo data: {objetivo_data}")
        
        # Validar dados essenciais
        if not questionnaire_data:
            raise HTTPException(
                status_code=400,
                detail="Dados do questionário não encontrados. Complete seu perfil financeiro primeiro."
            )
        
        if not objetivo_data:
            raise HTTPException(
                status_code=400,
                detail="Objetivo financeiro não encontrado. Complete seu perfil financeiro primeiro."
            )
        
        # Estrutura exata conforme frontend - adicionar mensalidade
        user_data = {
            "user_id": current_user_id,
            "age": questionnaire_data.get("age"),
            "monthly_income": questionnaire_data.get("monthly_income"),
            "risk_profile": questionnaire_data.get("risk_profile"),
            "transportation_methods": questionnaire_data.get("transportation_methods"),
            "mensalidade_faculdade": questionnaire_data.get("mensalidade_faculdade"),
            "valor_mensalidade": questionnaire_data.get("valor_mensalidade", 0),
            "dependents": questionnaire_data.get("dependents"),
            "financial_goal": objetivo_data.get("financial_goal"),
            "target_amount": objetivo_data.get("financial_goal_details", {}).get("target_amount"),
            "time_frame": objetivo_data.get("financial_goal_details", {}).get("time_frame")
        }
        
        print(f"🔍 DEBUG - User data preparado: {user_data}")
        
        # Validar todos os campos obrigatórios (sem valores padrão)
        if not user_data.get("age"):
            raise HTTPException(
                status_code=400,
                detail="Idade é obrigatória. Complete seu perfil financeiro primeiro."
            )
        
        if not user_data.get("monthly_income") or float(user_data["monthly_income"]) <= 0:
            raise HTTPException(
                status_code=400,
                detail="Renda mensal deve ser maior que zero. Atualize seu perfil financeiro."
            )
        
        if not user_data.get("risk_profile"):
            raise HTTPException(
                status_code=400,
                detail="Perfil de risco é obrigatório. Complete seu perfil financeiro primeiro."
            )
        
        if not user_data.get("financial_goal"):
            raise HTTPException(
                status_code=400,
                detail="Objetivo financeiro é obrigatório. Complete seu perfil financeiro primeiro."
            )
        
        if not user_data.get("target_amount") or float(user_data["target_amount"]) <= 0:
            raise HTTPException(
                status_code=400,
                detail="Valor objetivo deve ser maior que zero. Complete seu perfil financeiro primeiro."
            )
        
        if not user_data.get("time_frame"):
            raise HTTPException(
                status_code=400,
                detail="Prazo para objetivo é obrigatório. Complete seu perfil financeiro primeiro."
            )
        
        if not user_data.get("age"):
            raise HTTPException(
                status_code=400,
                detail="Idade é obrigatória. Atualize seu perfil financeiro."
            )

        # Criar e executar crew
        crew_system = FinancialAdvisorCrew(user_data, selected_model)
        
        print(f"🚀 Iniciando análise CrewAI para usuário {current_user_id}")
        print(f"🔍 DEBUG - User data final enviado para crew: {user_data}")
        
        results = await crew_system.run_analysis(
            csv_file_path=csv_file_path,
            selected_model=selected_model
        )

        if results["success"]:
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
        
        # Buscar a resposta LLM mais recente para este perfil
        latest_llm_response = db.query(LLMResponse).filter(
            LLMResponse.perfil_financeiro_id == profile.id
        ).order_by(LLMResponse.data_criado.desc()).first()
        
        if not latest_llm_response:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma análise financeira encontrada. Execute o processamento CrewAI primeiro usando /api/financial/analyze-with-crewai"
            )
        
        # Extrair dados das colunas da tabela llm_responses
        try:
            transactions_data = json.loads(latest_llm_response.transactions_response)
            advice_data = json.loads(latest_llm_response.advice_response)
            dashboard_data = json.loads(latest_llm_response.dashboard_response)
            quality_metrics = json.loads(latest_llm_response.score)
            
            # Estruturar resposta completa para o dashboard
            dashboard_response = {
                "success": True,
                "timestamp": latest_llm_response.data_criado.isoformat(),
                "profile_id": profile.id,
                "modelo_ia": latest_llm_response.modelo_ia,
                "data": {
                    "transactions": transactions_data,
                    "advice": advice_data,
                    "dashboard": dashboard_data,
                    "quality_metrics": quality_metrics
                },
                "summary": {
                    "total_transactions": len(transactions_data.get("transacoes", [])),
                    "total_categories": len(transactions_data.get("totais_por_categoria", [])),
                    "has_advice": bool(advice_data.get("resumo")),
                    "dashboard_ready": bool(dashboard_data.get("ok")),
                    "analysis_date": latest_llm_response.data_criado.isoformat()
                }
            }
            
            print(dashboard_response)

            return dashboard_response
                
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao processar dados da análise: {str(e)}"
            )

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
                "modelo_ia": llm_resp.modelo_ia,
                "transactions_response": json.loads(llm_resp.transactions_response),
                "advice_response": json.loads(llm_resp.advice_response),
                "dashboard_response": json.loads(llm_resp.dashboard_response),
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
            "modelo_ia": latest_llm_response.modelo_ia,
            "transactions_response": json.loads(latest_llm_response.transactions_response),
            "advice_response": json.loads(latest_llm_response.advice_response),
            "dashboard_response": json.loads(latest_llm_response.dashboard_response),
            "quality_metrics": json.loads(latest_llm_response.score)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)