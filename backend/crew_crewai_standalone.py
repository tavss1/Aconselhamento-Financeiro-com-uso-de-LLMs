#!/usr/bin/env python3
"""
Sistema de Agentes CrewAI Standalone - Versão Robusta
====================================================

Sistema simplificado com execução direta de ferramentas quando apropriado
e uso de agentes LLM apenas para tarefas que exigem raciocínio complexo.

Fluxo:
1. Construir perfil (DIRETO)
2. Extrair e categorizar transações (AGENTE)
3. Gerar conselhos financeiros (AGENTE)
4. Compilar dashboard (DIRETO)
"""
import re
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Adicionar path para importar as ferramentas
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
from pydantic import BaseModel, Field

# Define chave dummy para evitar erro interno de validação
os.environ["OPENAI_API_KEY"] = "dummy"

# Desabilita checagem de modelo OpenAI
os.environ["CREWAI_LLM_PROVIDER"] = "ollama"

# (opcional) evita chamadas externas para OpenAI
os.environ["CREWAI_USE_LOCAL_LLM_ONLY"] = "true"

# Configuração do LLM para agentes
llm = LLM(
    model="ollama/gemma3",
    base_url="http://localhost:11434"
)

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
                "profile_id": f"standalone_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
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

# ============================================================================
# CREW STANDALONE ROBUSTA
# ============================================================================

class StandaloneFinancialAdvisorCrew:
    """Crew de aconselhamento financeiro standalone otimizada."""
    
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
            description = f"""
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
            llm=llm,
            output_file="extract_result.json"
        )
    
    def create_advice_task(self, agent: Agent, profile_json: str, transactions_json: str) -> Task:
        """Cria task de geração de conselhos com instruções rígidas para evitar corrupção de JSON.

        Estratégias aplicadas:
        - JSON minificado passado diretamente
        - Proibição explícita de blocos markdown (```)
        - Formato único e validável para Action / Action Input
        - Regras de validação embutidas para o modelo seguir
        - Reforço de NÃO duplicar ou alterar campos
        """

        # Extrair metadados do objetivo para reforço contextual (não re-injetar JSON completo)
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

         # Evita erro caso o transactions_json venha de contexto (None)
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
            max_iter=1,
            #context={"use_previous_output": True},
            output_file="advice_result.json"
        )
    def _clean_json_text(self, text: str) -> str:
        """
        Remove delimitadores Markdown (```json ... ``` ou '''json ... ''') e espaços extras
        antes de tentar o parse com json.loads().
        """
        if not text:
            return ""
        # Remove delimitadores iniciais como ```json ou '''json
        cleaned = re.sub(r"^[`']{3,}\s*json\s*", "", text.strip(), flags=re.IGNORECASE)
        # Remove delimitadores finais como ``` ou '''
        cleaned = re.sub(r"[`']{3,}\s*$", "", cleaned.strip())
        # Remove eventuais marcadores <json> ou </json>
        cleaned = re.sub(r"<\/?json>", "", cleaned.strip(), flags=re.IGNORECASE)
        return cleaned.strip()

    def run_complete_analysis(self, csv_file_path: str, categorization_method: str = "ollama") -> Dict[str, Any]:
        """
        Executa análise financeira completa com dois agentes CrewAI em pipeline sequencial:
        1. Construir perfil (direto)
        2. Extrair transações (agente)
        3. Gerar conselhos (agente)
        4. Compilar dashboard (direto)
        """
        print("\n" + "=" * 80)
        print("🤖 SISTEMA DE ANÁLISE FINANCEIRA - VERSÃO INTEGRADA (2 AGENTES CREWAI)")
        print("=" * 80)

        try:
            # ================================================================
            # ETAPA 1: CONSTRUIR PERFIL (EXECUÇÃO DIRETA)
            # ================================================================
            print("\n📊 ETAPA 1: Construindo perfil financeiro...")
            profile_tool = StandaloneUserProfileBuilderTool()
            profile_result = profile_tool._run(user_data_json=self.user_data)
            profile_data = json.loads(profile_result)
            if not profile_data.get("ok"):
                raise Exception(f"Erro ao construir perfil: {profile_data.get('error')}")
            print(f"✅ Perfil construído com sucesso para {self.user_data.get('user_id', 'usuário')}")

            # ================================================================
            # ETAPA 2 e 3: CREW SEQUENCIAL COM DOIS AGENTES
            # ================================================================
            print("\n🤝 Iniciando pipeline integrada (Extração ➜ Aconselhamento)...")

            # Criação dos agentes
            data_extractor = self.create_data_extractor_agent()
            financial_advisor = self.create_financial_advisor_agent()

            # Criação das tasks
            extract_task = self.create_extract_task(
                agent=data_extractor,
                csv_file_path=csv_file_path,
                categorization_method=categorization_method
            )

            # Minificar perfil para reduzir tokens
            profile_min = json.dumps(profile_data, ensure_ascii=False, separators=(",", ":"))

            advice_task = self.create_advice_task(
                agent=financial_advisor,
                profile_json=profile_min,
                transactions_json=None
            )
            
            advice_task.context = [extract_task]  # ✅ referência direta

            # Criar crew com memória compartilhada
            crew_pipeline = Crew(
                agents=[data_extractor, financial_advisor],
                tasks=[extract_task, advice_task],
                process=Process.sequential,
                llm=llm,
                memory=True,
                shared_memory=True,
                verbose=True
            )

            # Rodar crew completa
            pipeline_result = crew_pipeline.kickoff()

            print("\n🤝 Pipeline integrada concluída. Validando resultados...")
            print(pipeline_result)

            with open("extract_result.json", "r", encoding="utf-8") as f:
                extract_result = f.read()
            with open("advice_result.json", "r", encoding="utf-8") as f:
                advice_result = f.read()

            print("\n✅ Pipeline CrewAI executada com sucesso.")
            # extract_data = json.loads(extract_result)
            # advice_data = json.loads(advice_result)

            extract_result_clean = self._clean_json_text(extract_result)
            advice_result_clean = self._clean_json_text(advice_result)

            try:
                extract_data = json.loads(extract_result_clean)
            except json.JSONDecodeError as e:
                print("❌ Falha ao interpretar o JSON de extract_result:")
                print(f"🔹 Erro: {e}")
                print(f"🔹 Conteúdo bruto (primeiros 400 chars):\n{extract_result[:400]}")
                raise

            try:
                advice_data = json.loads(advice_result_clean)
            except json.JSONDecodeError as e:
                import re
                match = re.search(r'\{(?:[^{}]|(?R))*\}', advice_result_clean, re.DOTALL)
                if match:
                    try:
                        advice_data = json.loads(match.group(0))
                        print("✅ JSON extraído automaticamente do texto!")
                    except Exception:
                        advice_data = {"ok": False, "error": "Falha ao extrair JSON de advice_result."}
                else:
                    advice_data = {
                        "ok": False,
                        "error": "O modelo não retornou JSON. Conteúdo bruto foi texto em linguagem natural."
                    }

                print(f"🪶 Preview da saída original (200 chars):\n{advice_result_clean[:200]}\n")
                raise

            print("✅ JSONs carregados com sucesso!")
            print(f"📦 extract_result contém {len(extract_data.get('transacoes', []))} transações.")
            print(f"🧠 advice_result contém plano: {advice_data.get('resumo', '')[:80]}...\n")

            with open("extract_result_clean.json", "w", encoding="utf-8") as f:
                json.dump(extract_data, f, ensure_ascii=False, indent=2)

            with open("advice_result_clean.json", "w", encoding="utf-8") as f:
                json.dump(advice_data, f, ensure_ascii=False, indent=2)

            print("💾 Resultados limpos salvos como:")
            print("   • extract_result_clean.json")
            print("   • advice_result_clean.json\n")

            # ================================================================
            # ETAPA 4: COMPILAR DASHBOARD (EXECUÇÃO DIRETA)
            # ================================================================
            print("\n📊 ETAPA 4: Compilando dados para dashboard...")

            try:
                advice_json_obj = json.loads(advice_result_clean)
                if "advice" not in advice_json_obj:
                    advice_json_obj = {"advice": advice_json_obj}
                advice_for_dashboard = json.dumps({"advice": advice_json_obj}, ensure_ascii=False)
            except Exception:
                # fallback se não for JSON válido
                print(f"⚠️ Falha ao processar advice_result: {e}")
                advice_for_dashboard = json.dumps({"advice": {"ok": False, "error": "advice_result inválido"}}, ensure_ascii=False)

            dashboard_tool = DashboardDataCompilerTool()
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
            if not dashboard_data.get("ok"):
                raise Exception(f"Erro no dashboard: {dashboard_data.get('error')}")

            print("\n✅ Dashboard compilado com sucesso!")
            summary = dashboard_data.get("summary", {})
            print(f"   • Categorias: {summary.get('total_categories', 0)}")
            print(f"   • Conselhos: {summary.get('advice_items', 0)}")

            # ================================================================
            # SALVAR RESULTADOS
            # ================================================================
            output = {
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

            output_file = f"financial_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            print(f"\n💾 Resultados salvos em: {output_file}")
            print("=" * 80)
            print("🎉 Análise completa com sucesso!")
            print("=" * 80)
            output["success"] = True
            return output

        except Exception as e:
            import traceback
            print("\n❌ ERRO NA EXECUÇÃO:", e)
            print(traceback.format_exc())
            return {"success": False, "error": str(e)}

# ============================================================================
# FUNÇÃO DE DEMONSTRAÇÃO
# ============================================================================

def demo_crew_analysis():
    """Demonstração completa do sistema."""
    
    print("\n🚀 INICIANDO DEMONSTRAÇÃO DO SISTEMA")
    
    # Dados do usuário
    user_data = {
        "user_id": 1,
        "age": 22,
        "monthly_income": 1500.00,
        "dependents": [],
        "risk_profile": "moderado",
        "financial_goal": "Reserva emergencial",
        "target_amount": 1200,
        "time_frame": "1 ano",
        "debt_to_income_ratio": 0.25,
        "liquid_assets": 25000.0,
        "transportation_methods": "transporte público"
    }
    
    print("\n👤 PERFIL DO USUÁRIO:")
    for key, value in user_data.items():
        print(f"   • {key}: {value}")
    
    # Arquivo CSV
    csv_file = "C:\\Users\\Bruno\\Downloads\\NU_533941896_01ABR2025_30ABR2025.csv"
    
    if not os.path.exists(csv_file):
        print(f"\n⚠️  Arquivo não encontrado: {csv_file}")
        print("   Procurando alternativas...")
        
        alternatives = ["test.csv", "extrato.csv", "extrato_categorizados_final.csv"]
        for alt in alternatives:
            if os.path.exists(alt):
                csv_file = alt
                print(f"   ✅ Usando: {csv_file}")
                break
        else:
            print("   ❌ Nenhum arquivo CSV encontrado")
            return
    
    print(f"\n📄 ARQUIVO: {csv_file}")
    
    # Executar análise
    crew_system = StandaloneFinancialAdvisorCrew(user_data)
    results = crew_system.run_complete_analysis(
        csv_file_path=csv_file,
        categorization_method="ollama"
    )
    
    # Resumo final
    if results["success"]:
        print("\n📈 RESUMO EXECUTIVO:")
        print("-" * 80)
        print(f"✅ Pipeline executada com sucesso")
        print(f"✅ Arquivo de saída gerado")
        print(f"✅ Dashboard pronto para uso")
    else:
        print("\n❌ FALHA NA EXECUÇÃO")
        print(f"Erro: {results['error']}")

if __name__ == "__main__":
    demo_crew_analysis()