"""
Finance Advisory Tools for CrewAI Agents
---------------------------------------

This module defines a set of CrewAI Tools tailored for a financial
advisory application that:
  1) builds a structured user financial profile from a questionnaire,
  2) parses and categorizes bank statements,
  3) queries local LLMs to produce personalized advice,
  4) evaluates multiple models' advice using a rubric,
  5) generates a JSON-ready report for a React dashboard.

Notes
-----
- No external SaaS APIs are used. The LocalLLMClient can invoke a local
  inference binary via subprocess (e.g., `ollama`, `llama.cpp`, `text-generation-inference` CLI),
  or any CLI you expose that prints model output to STDOUT.
- All tools return JSON strings for easy handoff between agents.
- Lightweight dependencies; optional extras guarded by try/except.

Author: Your Team
"""
from __future__ import annotations

import os
import re
import json
import csv
import math
import shlex
import pickle
import pathlib
import datetime as dt
import subprocess
from typing import Any, Dict, List, Optional, Tuple, ClassVar, ClassVar

# CrewAI BaseTool
try:
    from crewai.tools import BaseTool
except Exception:  # Fallback stub for linting/tests if crewai isn't installed yet
    class BaseTool:  
        name: str = ""
        description: str = ""
        def __init__(self, *args, **kwargs): pass
        def _run(self, *args, **kwargs): raise NotImplementedError

# Pydantic for arg schemas (nice in CrewAI UIs)
try:
    from pydantic import BaseModel, Field
except Exception:  # minimal shim
    class BaseModel:  # type: ignore
        def __init__(self, **data): self.__dict__.update(data)
    def Field(default=None, description: str = "", example: Any = None):
        return default

# Pandas is used for tabular processing
try:
    import pandas as pd
except Exception:
    pd = None  # tools will degrade gracefully if pandas isn't present


# Optional: langchain_ollama for enhanced LLM categorization
try:
    from langchain_ollama import ChatOllama
    from langchain.schema import HumanMessage
    from tqdm import tqdm
except Exception:
    ChatOllama = None
    HumanMessage = None
    tqdm = None

# ----------------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------------

def _now_iso() -> str:
    return dt.datetime.now().isoformat()

class JSONableError(Exception):
    pass

class LocalLLMClient:
    """Simple local LLM client that shells out to a command-line runner.

    You can configure via environment variables:
      - LLM_CMD: Full command template, e.g. "ollama run {model} --prompt {prompt}"
                 or "./main -m models/model.gguf -p {prompt}"
      - LLM_MODEL: Default model name/tag (e.g., "llama3:8b")
      - LLM_TIMEOUT: Seconds before killing the subprocess (str -> int)

    Alternatively, pass a custom `cmd_template` at init time.
    The template must contain "{prompt}" and may contain "{model}".
    """
    def __init__(
        self,
        cmd_template: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.cmd_template = cmd_template or os.getenv("LLM_CMD", "ollama run {model} {prompt}")
        self.default_model = default_model or os.getenv("LLM_MODEL", "gemma3")
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", "120"))

    def generate(self, prompt: str, model: Optional[str] = None) -> str:
        model = model or self.default_model
        if "{prompt}" not in self.cmd_template:
            raise JSONableError("cmd_template must contain {prompt}")
        cmd = self.cmd_template.format(prompt=shlex.quote(prompt), model=model)
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            raise JSONableError("Local LLM timed out")
        if proc.returncode != 0:
            raise JSONableError(f"Local LLM failed: {proc.stderr.strip()}")
        return proc.stdout.strip()

# ----------------------------------------------------------------------------
# Database Access Integration
# ----------------------------------------------------------------------------

# Import database components
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from db.database import SessionLocal
    from db.models import FinancialProfile
except ImportError:
    # Fallback quando database não está disponível
    SessionLocal = None
    FinancialProfile = None

class DatabaseFinancialProfileArgs(BaseModel):
    usuario_id: int = Field(description="ID do usuário para buscar dados financeiros")

class DatabaseFinancialProfileTool(BaseTool):
    name: str = "DatabaseFinancialProfile"
    description: str = (
        "Acessa a base de dados para recuperar informações do perfil financeiro de um usuário específico, "
        "incluindo dados do questionário e objetivos financeiros da tabela perfil_financeiro."
    )

    def _run(self, usuario_id: int) -> str:
        """
        Busca dados do perfil financeiro de um usuário no banco de dados.
        
        Args:
            usuario_id (int): ID do usuário para buscar dados
            
        Returns:
            str: JSON string com dados do perfil ou erro
        """
        # Verificação de disponibilidade do banco
        if not SessionLocal or not FinancialProfile:
            return self._create_error_response(
                "Database connection not available. Please configure database components."
            )

        db_session = None
        try:
            # Criar sessão do banco
            db_session = SessionLocal()
            
            # Buscar perfil financeiro mais recente do usuário
            profile = self._get_latest_profile(db_session, usuario_id)
            
            if not profile:
                return self._create_error_response(
                    f"No financial profile found for user ID {usuario_id}"
                )
            
            # Processar dados do perfil
            processed_data = self._process_profile_data(profile)
            
            return json.dumps(processed_data, ensure_ascii=False)
            
        except Exception as e:
            error_msg = f"Database error: {str(e)}"
            return self._create_error_response(error_msg)
            
        finally:
            # Garantir fechamento da sessão
            if db_session:
                try:
                    db_session.close()
                except Exception:
                    pass  # Ignorar erros de fechamento

    def _get_latest_profile(self, db_session, usuario_id: int):
        """Busca o perfil financeiro mais recente de um usuário."""
        try:
            return (
                db_session.query(FinancialProfile)
                .filter(FinancialProfile.usuario_id == usuario_id)
                .order_by(FinancialProfile.data_criado.desc())
                .first()
            )
        except Exception as e:
            print(f"Error querying profile for user {usuario_id}: {e}")
            return None

    def _process_profile_data(self, profile) -> dict:
        """Processa e estrutura os dados do perfil financeiro."""

        questionnaire_data = self._safe_json_parse(
            profile.questionnaire_data, "questionnaire_data"
        )
        
        objetivo_data = self._safe_json_parse(
            profile.objetivo, "objetivo"
        )
        
        # Estrutura resposta final
        result = {
            "ok": True,
            "timestamp": _now_iso(),
            "profile_id": profile.id,
            "usuario_id": profile.usuario_id,
            "questionnaire_data": questionnaire_data,
            "objetivo_data": objetivo_data,
            "data_criado": profile.data_criado.isoformat() if profile.data_criado else None,
            "metadata": {
                "has_questionnaire": bool(questionnaire_data),
                "has_objectives": bool(objetivo_data),
                "profile_completeness": self._calculate_completeness(questionnaire_data, objetivo_data)
            }
        }
        
        return result

    def _safe_json_parse(self, json_string: str, field_name: str) -> dict:
        """Parse seguro de JSON com tratamento de null bytes e erros."""
        
        if not json_string:
            return {}
            
        try:
            # Remove null bytes se presentes
            clean_string = json_string.replace('\x00', '')
            
            # Remove espaços em branco extras
            clean_string = clean_string.strip()
            
            if not clean_string:
                return {}
                
            # Parse do JSON
            parsed_data = json.loads(clean_string)
            
            # Validação básica
            if not isinstance(parsed_data, dict):
                print(f"Warning: {field_name} is not a dict, converting...")
                return {"raw_data": parsed_data}
                
            return parsed_data
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error in {field_name}: {e}")
            return {"parse_error": str(e), "raw_data": json_string[:100]}
        except Exception as e:
            print(f"Unexpected error parsing {field_name}: {e}")
            return {"error": str(e)}
        
    def _create_error_response(self, error_message: str) -> str:
        """
        Cria resposta de erro padronizada.
        
        Args:
            error_message (str): Mensagem de erro
            
        Returns:
            str: JSON string com erro
        """
        error_response = {
            "ok": False,
            "error": error_message,
            "timestamp": _now_iso()
        }
        return json.dumps(error_response, ensure_ascii=False)

# ----------------------------------------------------------------------------
# 1) UserProfileBuilderTool - usando banco de dados 
# ----------------------------------------------------------------------------

class UserProfileBuilderArgs(BaseModel):
    database_profile_json: str = Field(description="JSON string from DatabaseFinancialProfileTool with user data")

class UserProfileBuilderTool(BaseTool):
    name: str = "UserProfileBuilder"
    description: str = (
        "Constrói um perfil financeiro normalizado a partir dos dados do questionário e do questionário obtidos do banco de dados. "
    )

    def _run(self, database_profile_json: str) -> str:
        try:
            db_data = json.loads(database_profile_json)
            
            if not db_data.get("ok", False):
                return json.dumps({"ok": False, "error": "Invalid database profile data"})
            
            questionnaire = db_data.get("questionnaire_data", {})
            objetivo = db_data.get("objetivo_data", {})
            
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Invalid JSON input: {e}"})

        try:
            # Extrair dados do questionário (adaptado para estrutura React)
            idade = int(questionnaire.get("age", 0))
            renda = float(questionnaire.get("monthly_income", 0))
            dependentes = questionnaire.get("dependents", [])
            perfil_declarado = questionnaire.get("risk_profile", "")
            transporte = questionnaire.get("transportation_methods", "")
            info_dependentes = self._processar_dependentes(dependentes)
                       
            # Cálculos de indicadores financeiros
            # capacidade_poupanca = max(renda - gastos_mensais, 0)
            # debt_to_income = (dividas_totais / renda) if renda > 0 else 0
            # savings_rate = (capacidade_poupanca / renda * 100) if renda > 0 else 0
            
            # Análise de objetivos
            objetivo_detalhes = objetivo.get("financial_goal_details", {})
            objetivo_descricao = objetivo.get("financial_goal", "")
            objetivo_valor = float(objetivo_detalhes.get("target_amount", 0))
            objetivo_prazo = objetivo_detalhes.get("time_frame", "")
            
            
            # Perfil final estruturado
            perfil = {
                "ok": True,
                "timestamp": _now_iso(),
                "profile_id": db_data.get("profile_id"),
                "usuario_id": db_data.get("usuario_id"),
                
                # Informações pessoais
                "dados_pessoais": {
                    "idade": idade,
                    "renda_mensal": renda,
                    "total_dependentes": info_dependentes.get("total", 0),
                    "detalhes_dependentes": info_dependentes.get("detalhes", []),
                    "risk_profile": perfil_declarado,
                    "transportation_methods": transporte,
                },
                # Objetivos financeiros
                "objetivo": {
                    "descricao": objetivo_descricao,
                    "valor_objetivo": objetivo_valor,
                    "prazo": objetivo_prazo
                },
            }
            
            return json.dumps(perfil, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Profile financial error: {str(e)}"})
    
    def _processar_dependentes(self, data):
        """
        Processa a estrutura de dependentes e retorna informações organizadas
        """
        dependentes = data.get("dependents", [])
        
        resultado = {
            "total": 0,
            "por_tipo": {},
            "detalhes": []
        }
        
        for dep in dependentes:
            tipo = dep.get("type")
            qtd = dep.get("quantity", 0)
            
            resultado["total"] += qtd
            #resultado["por_tipo"][tipo] = resultado["por_tipo"].get(tipo, 0) + qtd
            resultado["detalhes"].append({"tipo": tipo, "quantidade": qtd})
        
        return resultado
# ----------------------------------------------------------------------------
# 2) BankStatementParserTool (CSV)
# ----------------------------------------------------------------------------

CATEGORY_MAP = {
    "mercado|supermerc|hiper|carrefour|pao de acucar|assai": "Mercado",
    "restaurante|pizza|lanchonete|ifood|ubereats": "Alimentação",
    "aluguel|condominio|iptu|imobiliaria": "Moradia",
    "energia|luz|copel|enel|eletrobras|cemig": "Moradia",
    "agua|sanepar|sabesp|corsan": "Moradia",
    "internet|vivo|claro|tim|oi|net": "Serviços",
    "uber|99|transporte|onibus|metrô|metro|estacionamento|combustivel|posto": "Transporte",
    "farmacia|drogaria|droga|saude|consulta|seguro saude": "Saúde",
    "netflix|spotify|disney|hbo|prime video": "Streaming",
    "salario|provento|pagto|pagamento|creditos": "Renda",
    "pix|ted|doc|transferencia": "Transferências",
    "educacao|curso|faculdade|escola": "Educação",
    "invest|tesouro|cdb|fundo|bolsa|corretora|clear|xp|rico": "Investimentos",
}

DEFAULT_COLUMNS_CANDIDATES = {
    "date": ["data", "date", "dt", "data_lancamento"],
    "desc": ["descricao", "Descrição","historico", "description", "detalhe", "descrição", "title"],
    "amount": ["valor", "amount", "vl", "montante"],
}

# ======== CACHE E CONFIGURAÇÕES PARA CATEGORIZAÇÃO AVANÇADA ========
CACHE_PATH = "categorias_cache.pkl"
BLOCO_TAMANHO = 10
OLLAMA_MODEL_DEFAULT = "gemma3"

def load_cache(path: str) -> dict:
    """Carrega cache de categorias do disco."""
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return pickle.load(f)
    return {}

def save_cache(cache: dict, path: str) -> None:
    """Salva cache de categorias no disco."""
    with open(path, 'wb') as f:
        pickle.dump(cache, f)

def clean_transaction_name(transaction_name: str) -> str:
    """Limpa o nome da transação para cache e comparação."""
    if not transaction_name:
        return ""
    parts = transaction_name.split(' - ')
    return ' - '.join(parts[:2]) if len(parts) > 2 else transaction_name

def generate_categorization_prompt(transactions: list) -> str:
    """Gera prompt para categorização em lote com LLM."""
    formatted = '\n'.join(f"{clean_transaction_name(t)}" for t in transactions)
    prompt = f"""Categorize cada transação financeira na categoria mais apropriada.

CATEGORIAS DISPONÍVEIS:
- Alimentação (restaurantes, delivery, lanches)
- Transporte (Uber, combustível, estacionamento)  
- Saúde (farmácias, consultas médicas)
- Mercado (supermercados, compras de alimentos)
- Educação (cursos, mensalidades escolares)
- Lazer (cinemas, jogos, entretenimento)
- Moradia (aluguel, condomínio, energia, água)
- Investimentos (CDB, ações, fundos)
- Streaming (Netflix, Spotify, Disney+)
- Transferências (PIX, TED, DOC)
- Renda (salários, freelances, dividendos)
- Serviços (internet, telefone, consultoria)
- Outros (quando nenhuma outra categoria se aplicar)

FORMATO DE RESPOSTA:
Para cada transação, responda EXATAMENTE no formato:
[NOME DA TRANSAÇÃO] - [CATEGORIA]

TRANSAÇÕES PARA CATEGORIZAR:
{formatted}

EXEMPLOS:
UBER TRIP 12345 - Transporte
NETFLIX.COM - Streaming  
SUPERMERCADO EXTRA - Mercado
PIX TRANSFERIDO - Transferências

RESPOSTA:"""
    return prompt.strip()

def parse_llm_categorization_response(response: str, original_transactions: list) -> list:
    """Faz parse da resposta do LLM para extrair categorizações."""
    if not response or not original_transactions:
        return []
        
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    parsed = []
    
    # Cria mapeamentos para busca mais eficiente
    trans_originais = {clean_transaction_name(t): t for t in original_transactions}
    trans_originais_lower = {k.lower(): v for k, v in trans_originais.items()}
    
    print(f"[DEBUG] Parsing LLM response. Lines: {len(lines)}")
    print(f"[DEBUG] Original transactions: {len(original_transactions)}")
    
    for line_idx, line in enumerate(lines):
        line_original = line
        
        # Remove numeração inicial se houver (ex: "1. ")
        line = re.sub(r'^\d+\.\s*', '', line)
        
        # Tenta diferentes separadores
        separators = [' - ', ':', ' -> ', ' | ', '\t']
        found_match = False
        
        for sep in separators:
            if sep in line:
                parts = line.split(sep)
                if len(parts) >= 2:
                    trans_part = parts[0].strip()
                    cat_part = parts[-1].strip()  # Pega a última parte como categoria
                    
                    # Remove pontuação extra da categoria
                    cat_clean = re.sub(r'[^\w\s]', '', cat_part).strip()
                    
                    # Busca exata primeiro
                    if trans_part in trans_originais:
                        parsed.append((trans_part, cat_clean))
                        found_match = True
                        print(f"[DEBUG] Exact match: '{trans_part}' -> '{cat_clean}'")
                        break
                    
                    # Busca case-insensitive
                    elif trans_part.lower() in trans_originais_lower:
                        original_key = trans_originais_lower[trans_part.lower()]
                        parsed.append((original_key, cat_clean))
                        found_match = True
                        print(f"[DEBUG] Case-insensitive match: '{trans_part}' -> '{cat_clean}'")
                        break
                    
                    # Busca por correspondência parcial
                    else:
                        for orig_clean in trans_originais.keys():
                            # Similaridade bidirecional mais flexível
                            if (trans_part.lower() in orig_clean.lower() or 
                                orig_clean.lower() in trans_part.lower() or
                                _calculate_similarity(trans_part.lower(), orig_clean.lower()) > 0.8):
                                parsed.append((orig_clean, cat_clean))
                                found_match = True
                                print(f"[DEBUG] Partial match: '{trans_part}' matched '{orig_clean}' -> '{cat_clean}'")
                                break
                        if found_match:
                            break
        
        if not found_match:
            print(f"[DEBUG] No match found for line {line_idx + 1}: '{line_original}'")
    
    print(f"[DEBUG] Successfully parsed {len(parsed)} transactions")
    return parsed

def _calculate_similarity(str1: str, str2: str) -> float:
    """Calcula similaridade simples entre duas strings."""
    if not str1 or not str2:
        return 0.0
    
    # Conta caracteres em comum
    set1 = set(str1.lower())
    set2 = set(str2.lower())
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0

class BankStatementParserToolSchema(BaseModel):
    file_path: str = Field(description="Path to the uploaded bank statement (csv)")
    llm_enhanced: bool = Field(default=False, description="If True, uses LLM to refine categorization when available")
    categorization_method: str = Field(default="regex", description="Método de categorização: 'regex' (padrão) ou 'ollama' (avançado com cache)")
    ollama_model: str = Field(default="gemma3", description="Modelo Ollama para categorização avançada")
    block_size: int = Field(default=10, description="Tamanho do bloco para processamento em lote no modo Ollama")

class BankStatementParserTool(BaseTool):
    name: str = "BankStatementParserTool"
    description: str = (
        "Parses a bank statement file (CSV) and outputs a JSON with normalized transactions and category totals."
    )
    args_schema = BankStatementParserToolSchema

    def _run(self, file_path: str, llm_enhanced: bool = False, categorization_method: str = "regex", 
             ollama_model: str = "gemma3", block_size: int = 10) -> str:
        try:
            ext = pathlib.Path(file_path).suffix.lower()
            if ext == ".csv":
                df = self._read_csv(file_path)
            else:
                return json.dumps({"ok": False, "error": f"Unsupported extension: {ext}"})

            if df is None or df.empty:
                return json.dumps({"ok": False, "error": "Empty or unreadable statement"})

            df = self._normalize_columns(df)
            
            # Escolha do método de categorização
            if categorization_method == "ollama":
                df = self._categorize_with_ollama(df, ollama_model, block_size)
            else:
                # Método padrão com regex
                df["categoria"] = df["descricao"].apply(self._categorize)
                
                if llm_enhanced:
                    try:
                        df = self._refine_categories_with_llm(df)
                    except Exception as e:
                        # proceed without failing the whole tool
                        pass

            # rollups
            totals = (
                df.groupby("categoria")["valor"].sum().reset_index().sort_values("valor")
            )
            summary = {
                "ok": True,
                "timestamp": _now_iso(),
                "method": categorization_method,
                "n_transacoes": int(len(df)),
                "totais_por_categoria": totals.to_dict(orient="records") if pd is not None else [],
                "transacoes": df.head(5000).to_dict(orient="records") if pd is not None else [],
            }
            return json.dumps(summary, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    # --- readers ---
    def _read_csv(self, path: str):
        if pd is None:
            raise JSONableError("pandas is required for CSV parsing")
        return pd.read_csv(path)

    def _normalize_columns(self, df):
        cols = {c.lower().strip(): c for c in df.columns}
        def find_col(cands):
            for alias in cands:
                if alias in cols:
                    return cols[alias]
            return None
        c_date = find_col(DEFAULT_COLUMNS_CANDIDATES["date"]) or list(df.columns)[0]
        c_desc = find_col(DEFAULT_COLUMNS_CANDIDATES["desc"]) or list(df.columns)[1]
        c_amt = find_col(DEFAULT_COLUMNS_CANDIDATES["amount"]) or list(df.columns)[2]
        out = df.rename(columns={c_date: "data", c_desc: "descricao", c_amt: "valor"}).copy()
        
        # Normalização inteligente de valores monetários
        def normalize_monetary_value(val):
            if pd.isna(val) or val == '':
                return 0.0
            
            # Converte para string e remove espaços
            str_val = str(val).strip()
            
            # Se já é um número, retorna como float
            try:
                return float(str_val)
            except:
                pass
            
            # Remove símbolos de moeda comuns (R$, $, etc.)
            str_val = re.sub(r'[R$\s]+', '', str_val)
            
            # Conta pontos e vírgulas para determinar o formato
            dot_count = str_val.count('.')
            comma_count = str_val.count(',')
            
            # Formato brasileiro: 1.234.567,89
            if comma_count == 1 and dot_count >= 1:
                # Remove pontos (separadores de milhares) e troca vírgula por ponto
                str_val = str_val.replace('.', '').replace(',', '.')
            # Formato brasileiro simples: 123,45 (sem separadores de milhares)
            elif comma_count == 1 and dot_count == 0:
                str_val = str_val.replace(',', '.')
            # Se tem apenas pontos, assume formato americano: 123.45
            # Se tem apenas vírgulas, assume separadores de milhares: 1,234 -> 1234
            elif comma_count >= 1 and dot_count == 0:
                # Se tem mais de uma vírgula ou valor > 999, assume separador de milhares
                if comma_count > 1 or len(str_val.replace(',', '')) > 3:
                    str_val = str_val.replace(',', '')
                else:
                    # Vírgula única em valor pequeno, assume decimal
                    str_val = str_val.replace(',', '.')
            try:
                return float(str_val)
            except:
                print(f"[WARNING] Não foi possível converter valor: '{val}' -> assumindo 0.0")
                return 0.0
        
        out["valor"] = out["valor"].apply(normalize_monetary_value)
        return out

    def _categorize(self, descricao: str) -> str:
        text = (descricao or "").lower()
        for pattern, cat in CATEGORY_MAP.items():
            if re.search(pattern, text):
                return cat
        return "Outros"

    def _categorize_with_ollama(self, df, model_name: str = "gemma3", block_size: int = 10):
        """Categoriza transações usando Ollama com cache inteligente e fallback para regex."""
        print(f"[INFO] Iniciando categorização com Ollama (modelo: {model_name})")

        # Verifica se ChatOllama está disponível
        if ChatOllama is None:
            print("[ERROR] ChatOllama não está disponível - problema na instalação do langchain_ollama")
            print("[INFO] Usando fallback para categorização regex")
            return self._categorize_with_regex_fallback(df)

        # Inicializa LLM
        try:
            llm = ChatOllama(model=model_name, temperature=0.1)
            print(f"[INFO] Modelo Ollama '{model_name}' inicializado com sucesso")

        except Exception as e:
            print(f"[ERROR] Falha ao inicializar Ollama: {e}")
            print("[INFO] Usando fallback para categorização regex")
            return self._categorize_with_regex_fallback(df)
        
        if pd is None:
            raise JSONableError("pandas is required for Ollama categorization")
        
        df_copy = df.copy()
        transacoes = df_copy["descricao"].fillna("").astype(str).tolist()
        
        print(f"[INFO] Total de transações: {len(transacoes)}")
        
        # Carrega cache existente
        cache_path = os.path.join(os.path.dirname(__file__), "..", CACHE_PATH)
        cache = load_cache(cache_path)
        print(f"[INFO] Cache carregado com {len(cache)} entradas")
        
        # Identifica transações que precisam de categorização
        transacoes_para_categorizar = []
        transacoes_no_cache = 0
        
        for t in transacoes:
            t_clean = clean_transaction_name(t)
            if t_clean and t_clean not in cache:
                transacoes_para_categorizar.append(t)
            elif t_clean in cache:
                transacoes_no_cache += 1
        
        print(f"[INFO] Transações no cache: {transacoes_no_cache}")
        print(f"[INFO] Transações para categorizar: {len(transacoes_para_categorizar)}")
        
        # Processa em blocos se há transações para categorizar
        if transacoes_para_categorizar:
            # Use tqdm se disponível, senão use range simples
            if tqdm is not None:
                iterator = tqdm(range(0, len(transacoes_para_categorizar), block_size), desc="Categorizando com Ollama")
            else:
                iterator = range(0, len(transacoes_para_categorizar), block_size)
                print(f"[INFO] Processando {len(transacoes_para_categorizar)} transações em blocos de {block_size}")
                
            ollama_success_count = 0
            ollama_error_count = 0
            
            for i in iterator:
                bloco = transacoes_para_categorizar[i:i+block_size]
                prompt = generate_categorization_prompt(bloco)
                
                print(f"[DEBUG] Processando bloco {i//block_size + 1} com {len(bloco)} transações")
                
                try:
                    resposta = llm.invoke([HumanMessage(content=prompt)])
                    print(f"[DEBUG] Resposta do LLM:\n{resposta.content[:500]}...")
                    
                    resultado = parse_llm_categorization_response(resposta.content, bloco)
                    
                    # Atualiza cache com resultados
                    for trans, cat in resultado:
                        t_clean = clean_transaction_name(trans)
                        if t_clean not in cache or cache[t_clean] == "Outros":
                            cache[t_clean] = cat
                            ollama_success_count += 1
                    
                    # Se algumas transações do bloco não foram categorizadas, use regex como fallback
                    transacoes_processadas = {clean_transaction_name(trans) for trans, _ in resultado}
                    
                    for trans in bloco:
                        t_clean = clean_transaction_name(trans)
                        if t_clean not in transacoes_processadas and t_clean not in cache:
                            # Fallback para regex
                            categoria_regex = self._categorize(trans)
                            cache[t_clean] = categoria_regex
                            print(f"[DEBUG] Fallback regex para '{trans}' -> '{categoria_regex}'")
                            
                except Exception as e:
                    print(f"[ERROR] Erro ao processar bloco: {e}")
                    ollama_error_count += len(bloco)
                    
                    # Em caso de erro, usa regex como fallback
                    for trans in bloco:
                        t_clean = clean_transaction_name(trans)
                        if t_clean not in cache:
                            categoria_regex = self._categorize(trans)
                            cache[t_clean] = categoria_regex
                            print(f"[DEBUG] Fallback regex (erro) para '{trans}' -> '{categoria_regex}'")
            
            print(f"[INFO] Categorização Ollama concluída: {ollama_success_count} sucessos, {ollama_error_count} erros")
            
            # Salva cache atualizado
            save_cache(cache, cache_path)
            print(f"[INFO] Cache salvo com {len(cache)} entradas")
        else:
            print("[INFO] Todas as transações já estão no cache")
        
        # Aplica categorizações do cache
        categorias_finais = []
        categorias_nao_encontradas = 0
        
        for t in transacoes:
            t_clean = clean_transaction_name(t)
            categoria = cache.get(t_clean)
            
            if categoria:
                categorias_finais.append(categoria)
            else:
                # Último recurso: categorização regex
                categoria_regex = self._categorize(t)
                categorias_finais.append(categoria_regex)
                categorias_nao_encontradas += 1
                print(f"[DEBUG] Transação não encontrada no cache, usando regex: '{t}' -> '{categoria_regex}'")
        
        print(f"[INFO] Finalizando: {categorias_nao_encontradas} transações não encontradas no cache")
        
        df_copy["categoria"] = categorias_finais
        return df_copy
    
    def _categorize_with_regex_fallback(self, df):
        """Fallback para categorização usando apenas regex."""
        print("[INFO] Usando categorização fallback com regex")
        df_copy = df.copy()
        df_copy["categoria"] = df_copy["descricao"].apply(self._categorize)
        return df_copy

    def _refine_categories_with_llm(self, df):
        client = LocalLLMClient()
        # Take a sample of unique descriptions to avoid long prompts
        uniq = df["descricao"].dropna().astype(str).str.slice(0, 80).unique().tolist()[:100]
        prompt = (
            "Você é um classificador de gastos. Mapeie cada descrição para UMA categoria entre: "
            "Alimentação, Moradia, Serviços, Transporte, Saúde, Lazer, Renda, Transferências, Educação, Outros.\n"
            "Responda em JSON no formato {\"mappings\": [{\"descricao\": \"...\", \"categoria\": \"...\"}]} sem comentários.\n\n"
            f"Descrições:\n- " + "\n- ".join(uniq)
        )
        try:
            raw = client.generate(prompt)
            data = json.loads(raw)
            mapping = {m.get("descricao", "").lower(): m.get("categoria", "Outros") for m in data.get("mappings", [])}
            df["categoria"] = df["descricao"].astype(str).str.lower().map(mapping).fillna(df["categoria"])  # type: ignore
        except Exception:
            pass
        return df

# ----------------------------------------------------------------------------
# 3) FinancialAdvisorTool (LLM plans based on profile + transactions)
# ----------------------------------------------------------------------------

from pydantic import BaseModel, Field
from typing import Optional

class FinancialAdvisorToolSchema(BaseModel):
    # Aceita string ou objeto já decodificado; validaremos dinamicamente
    profile_json: Any = Field(description="JSON (string ou objeto) do UserProfileBuilderTool")
    transactions_json: Any = Field(description="JSON (string, dict ou lista) do BankStatementParserTool com transações categorizadas. OBRIGATÓRIO.")
    model: Optional[str] = Field(default=None, description="Local model identifier to use")

class FinancialAdvisorTool(BaseTool):
    name: str = "FinancialAdvisor"
    description: str = (
        "Generates personalized financial advice using a local LLM, based on the user profile and categorized transactions. "
        "Returns a structured JSON plan with actions by horizon (now/30/90 days, 12 months)."
    )
    args_schema = FinancialAdvisorToolSchema

    SYSTEM_PROMPT: ClassVar[str] = (
        "Você é um planejador financeiro pessoal. Dado um perfil e o histórico de gastos categorizados, "
        "gere recomendações específicas, exequíveis e alinhadas ao objetivo do usuário. "
        "A saída DEVE ser JSON válido com o schema: {\n"
        "  \"resumo\": string,\n"
        "  \"alertas\": [string],\n"
        "  \"plano\": {\n"
        "    \"agora\": [string],\n"
        "    \"30_dias\": [string],\n"
        "  },\n"
        "  \"metas_mensuraveis\": [{\"meta\": string, \"kpi\": string, \"meta_num\": number, \"prazo_meses\": number}]\n"
        "}"
    )

    def _run(self, profile_json: Any, transactions_json: Any, model: Optional[str] = None) -> str:
        """Gera aconselhamento financeiro estruturado.

        Agora transactions_json é OBRIGATÓRIO. Se houver falha de parse, retorna erro explícito.
        Limita número de transações usadas no prompt para evitar prompt gigante.
        """
        # Parse do perfil
        # Normalização do profile
        try:
            if isinstance(profile_json, (dict, list)):
                profile = profile_json
            else:
                profile = json.loads(profile_json)
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Invalid profile_json: {e}"})

        # Parse das transações (obrigatório)
        # Normalização das transações
        try:
            if isinstance(transactions_json, (dict, list)):
                tx_raw = transactions_json
            else:
                tx_raw = json.loads(transactions_json)
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Invalid transactions_json: {e}"})

        # Permitir formato direto lista de transações (sem wrapper)
        if isinstance(tx_raw, list):
            tx = {"transacoes": tx_raw, "totais_por_categoria": []}
        else:
            tx = tx_raw

        if not isinstance(tx, dict) or not isinstance(tx.get("transacoes"), list):
            return json.dumps({"ok": False, "error": "transactions_json deve conter lista 'transacoes'"})

        # Limitar contexto
        tx_list = tx.get("transacoes", [])
        if not isinstance(tx_list, list):
            return json.dumps({"ok": False, "error": "Campo 'transacoes' não é lista"})
        tx_list_short = tx_list[:100]

        # Totais por categoria
        cat_totals = {}
        for row in tx.get("totais_por_categoria", []):
            if isinstance(row, dict):
                try:
                    cat_totals[row.get("categoria", "Desconhecido")] = float(row.get("valor", 0))
                except Exception:
                    pass

        context = {
            "perfil": profile,
            "resumo_gastos": cat_totals,
            "amostra_transacoes": tx_list_short,
            "n_transacoes_contexto": len(tx_list_short),
            "n_transacoes_total": len(tx_list)
        }

        prompt = self.SYSTEM_PROMPT + "\n\nDados de entrada (JSON):\n" + json.dumps(context, ensure_ascii=False)

        client = LocalLLMClient()
        try:
            raw = client.generate(prompt, model=model)
            data = json.loads(_extract_json(raw))
            return json.dumps({"ok": True, "timestamp": _now_iso(), "advice": data}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": f"LLM or parse error: {e}"})

# ----------------------------------------------------------------------------
# 4) ModelEvaluatorTool (LLM-as-a-judge + heuristics fallback)
# ----------------------------------------------------------------------------

EVAL_RUBRIC = {
    "clareza": "O texto é claro, objetivo e bem estruturado? (0-5)",
    "aplicabilidade": "As recomendações são práticas e exequíveis? (0-5)",
    "consistencia": "Há coerência com o perfil e objetivos? (0-5)",
    "completude": "Cobre curto, médio e longo prazo, riscos e métricas? (0-5)",
}

class ModelEvaluatorToolSchema(BaseModel):
    advices_json: str = Field(description="JSON list with entries: {model: str, advice_json: {..}} or {model, text}")
    profile_json: Optional[str] = Field(default=None, description="Profile JSON to provide context to the judge")
    use_llm_judge: bool = Field(default=True, description="If True, use LLM-as-a-judge; else use heuristics only")

class ModelEvaluatorTool(BaseTool):
    name: str = "ModelEvaluator"
    description: str = (
        "Compares multiple model advices and scores them using a rubric (clareza, aplicabilidade, consistencia, completude). "
        "Returns scores per model and picks a winner."
    )
    args_schema = ModelEvaluatorToolSchema

    def _run(self, advices_json: str, profile_json: Optional[str] = None, use_llm_judge: bool = True) -> str:
        try:
            items = json.loads(advices_json)
            profile = json.loads(profile_json) if profile_json else None
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Invalid JSON: {e}"})

        # Normalize to text for evaluation
        normalized: List[Tuple[str, str]] = []  # (model, text)
        for it in items:
            model = it.get("model", "unknown")
            if "advice_json" in it and isinstance(it["advice_json"], dict):
                text = json.dumps(it["advice_json"], ensure_ascii=False)
            else:
                text = it.get("text") or json.dumps(it, ensure_ascii=False)
            normalized.append((model, text))

        scores = []
        if use_llm_judge:
            try:
                scores = self._judge_with_llm(normalized, profile)
            except Exception:
                scores = self._heuristic_scores(normalized)
        else:
            scores = self._heuristic_scores(normalized)

        # pick best
        for sc in scores:
            sc["total"] = sum(sc.get(k, 0) for k in ["clareza", "aplicabilidade", "consistencia", "completude"])  # type: ignore
        winner = max(scores, key=lambda d: d["total"]) if scores else None
        out = {"ok": True, "timestamp": _now_iso(), "rubric": EVAL_RUBRIC, "scores": scores, "winner": winner}
        return json.dumps(out, ensure_ascii=False)

    def _judge_with_llm(self, pairs: List[Tuple[str, str]], profile: Optional[dict]) -> List[Dict[str, Any]]:
        client = LocalLLMClient()
        blocks = []
        for model, text in pairs:
            prompt = (
                "Você é um avaliador rigoroso. Avalie o conselho abaixo segundo a rubrica (0-5 por critério) e retorne JSON: "
                "{\"clareza\":int,\"aplicabilidade\":int,\"consistencia\":int,\"completude\":int,\"justificativa\":string}.\n\n"
                f"Perfil (se houver): {json.dumps(profile, ensure_ascii=False)}\n\n"
                f"Conselho do modelo {model}:\n{text}\n"
            )
            raw = client.generate(prompt)
            data = json.loads(_extract_json(raw))
            data["model"] = model
            blocks.append(data)
        return blocks

    def _heuristic_scores(self, pairs: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        out = []
        for model, text in pairs:
            word_count = len(re.findall(r"\w+", text))
            has_json_like = 1 if (text.strip().startswith("{") and text.strip().endswith("}")) else 0
            has_numbers = 1 if re.search(r"\d", text) else 0
            # crude heuristics
            clareza = min(5, 1 + word_count // 120)
            completude = min(5, 1 + (text.count("agora") + text.count("30") + text.count("90") + text.count("12")))
            aplicabilidade = min(5, 1 + has_numbers + has_json_like)
            consistencia = 3  # base
            out.append({
                "model": model,
                "clareza": int(clareza),
                "aplicabilidade": int(aplicabilidade),
                "consistencia": int(consistencia),
                "completude": int(completude),
                "justificativa": "Heurísticas estáticas de fallback.",
            })
        return out

# ----------------------------------------------------------------------------
# 5) ReportGeneratorTool (JSON for React dashboard)
# ----------------------------------------------------------------------------

class ReportGeneratorArgs(BaseModel):
    profile_json: str = Field(description="User profile JSON (from UserProfileBuilderTool)")
    statement_json: str = Field(description="Parsed statement JSON (from BankStatementParserTool)")
    evaluation_json: str = Field(description="Scores/winner JSON (from ModelEvaluatorTool)")
    best_advice_json: str = Field(description="Advice JSON (from FinancialAdvisorTool for the winner)")

class ReportGeneratorTool(BaseTool):
    name: str = "ReportGeneratorTool"
    description: str = (
        "Aggregates profile, spending, evaluation, and best advice into a single JSON payload "
        "ready for visualization in a React dashboard (charts/tables)."
    )

    def _run(self, profile_json: str, statement_json: str, evaluation_json: str, best_advice_json: str) -> str:
        try:
            profile = json.loads(profile_json)
            stmt = json.loads(statement_json)
            evalj = json.loads(evaluation_json)
            best = json.loads(best_advice_json)
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Invalid JSON inputs: {e}"})

        # Extract chart-friendly structures
        spend_by_cat = stmt.get("totais_por_categoria", [])
        monthly_saving = profile.get("capacidade_poupanca")
        risk = profile.get("classificacao_risco")
        scores = evalj.get("scores", [])
        winner = evalj.get("winner", {})
        advice = best.get("advice", {}) if isinstance(best, dict) else {}

        payload = {
            "ok": True,
            "timestamp": _now_iso(),
            "profile": {
                "renda_mensal": profile.get("renda_mensal"),
                "gastos_mensais": profile.get("gastos_mensais"),
                "capacidade_poupanca": monthly_saving,
                "debt_to_income": profile.get("debt_to_income"),
                "objetivo": profile.get("objetivo", {}),
                "classificacao_risco": risk,
            },
            "spending": {
                "by_category": spend_by_cat,
                "sample_transactions": stmt.get("transacoes", [])[:100],
            },
            "evaluation": {
                "rubric": evalj.get("rubric", {}),
                "scores": scores,
                "winner": winner,
            },
            "advice": advice,
            "widgets": {
                "kpis": [
                    {"label": "Poupança/Mês", "value": monthly_saving},
                    {"label": "Risco", "value": risk},
                    {"label": "Meta (meses)", "value": profile.get("objetivo", {}).get("meses_estimados_pelo_fluxo")},
                ],
                "radar_scores": [
                    {"model": s.get("model"),
                     "clareza": s.get("clareza", 0),
                     "aplicabilidade": s.get("aplicabilidade", 0),
                     "consistencia": s.get("consistencia", 0),
                     "completude": s.get("completude", 0)}
                    for s in scores
                ],
            }
        }
        return json.dumps(payload, ensure_ascii=False)

# ----------------------------------------------------------------------------
# Helper: JSON extraction (for LLMs that wrap JSON with text)
# ----------------------------------------------------------------------------

def _extract_json(text: str) -> str:
    """Extract first JSON object/array from a text block."""
    s = text.strip()
    start = s.find("{")
    start_arr = s.find("[")
    if start == -1 and start_arr != -1:
        start = start_arr
    if start == -1:
        raise JSONableError("No JSON object found in LLM output")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if ch == '"' and not esc:
            in_str = not in_str
        if not in_str:
            if ch in "[{":
                depth += 1
            elif ch in "]}":
                depth -= 1
                if depth == 0:
                    return s[start:i+1]
        esc = (ch == "\\" and not esc)
    raise JSONableError("Truncated JSON in LLM output")

# ----------------------------------------------------------------------------
# 6) DashboardDataCompilerTool (Estruturação para Frontend React)
# ----------------------------------------------------------------------------

class DashboardDataCompilerToolSchema(BaseModel):
    profile_json: str = Field(description="JSON do perfil financeiro (UserProfileBuilderTool)")
    transactions_json: str = Field(description="JSON das transações categorizadas (BankStatementParserTool)")
    advice_json: str = Field(description="JSON dos conselhos financeiros (FinancialAdvisorTool)")
    evaluation_json: str = Field(description="JSON da avaliação dos modelos (ModelEvaluatorTool)")
    ui_preferences: Optional[str] = Field(default=None, description="Preferências de UI (tema, layout, etc.)")

class DashboardDataCompilerTool(BaseTool):
    name: str = "DashboardDataCompiler"
    description: str = (
        "Compila e estrutura todos os dados financeiros em formato JSON otimizado para "
        "renderização no dashboard React. Gera datasets prontos para gráficos, KPIs calculados "
        "e configurações de UI responsivas."
    )
    args_schema = DashboardDataCompilerToolSchema

    def _run(
        self, 
        profile_json: str, 
        transactions_json: str, 
        advice_json: str, 
        evaluation_json: str,
        ui_preferences: Optional[str] = None
    ) -> str:
        try:
            # Parse dos dados de entrada
            profile = json.loads(profile_json)
            transactions = json.loads(transactions_json)  
            advice = json.loads(advice_json)
            evaluation = json.loads(evaluation_json)
            
            ui_prefs = json.loads(ui_preferences) if ui_preferences else {}
            
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Erro ao parsear JSONs de entrada: {e}"})
        
        try:
            # Gerar timestamp e metadados
            now = dt.datetime.now()
            
            # 1. PROFILE SUMMARY - KPIs e informações essenciais
            profile_summary = self._build_profile_summary(profile)
            
            # 2. TRANSACTIONS ANALYSIS - Dados categorizados otimizados para charts  
            transactions_analysis = self._build_transactions_analysis(transactions)
            
            # 3. FINANCIAL ADVICE - Conselhos estruturados por timeline
            financial_advice = self._build_financial_advice(advice, profile)
            
            # 4. VISUALIZATIONS - Datasets prontos para gráficos
            visualizations = self._build_visualizations(transactions, profile, advice)
            
            # 5. COMPARATIVE METRICS - Benchmarks e comparações
            comparative_metrics = self._build_comparative_metrics(profile, transactions)
            
            # 6. UI CONFIG - Configurações de tema e layout
            ui_config = self._build_ui_config(ui_prefs)
            
            # 7. ALERTS - Notificações importantes
            alerts = self._build_alerts(profile, transactions, advice)
            
            # Compilação final
            dashboard_data = {
                "metadata": {
                    "generated_at": now.isoformat(),
                    "compilation_time_ms": 0,  # Será calculado se necessário
                    "data_version": "v1.0",
                    "frontend_compatibility": "react_v18+",
                    "total_data_points": len(transactions.get("transacoes", [])),
                    "analysis_period": self._get_analysis_period(transactions)
                },
                "profile_summary": profile_summary,
                "transactions_analysis": transactions_analysis,  
                "financial_advice": financial_advice,
                "visualizations": visualizations,
                "comparative_metrics": comparative_metrics,
                "ui_config": ui_config,
                "alerts_and_notifications": alerts
            }
            
            return json.dumps({
                "ok": True,
                "timestamp": now.isoformat(),
                "dashboard_data": dashboard_data,
                "summary": {
                    "total_categories": len(transactions_analysis.get("categories_breakdown", [])),
                    "advice_items": len(financial_advice.get("recommendations_by_timeline", {}).get("immediate", [])),
                    "charts_configured": len(visualizations),
                    "alerts_count": len(alerts.get("urgent", []) + alerts.get("informational", []))
                }
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Erro na compilação do dashboard: {e}"})
    
    def _build_profile_summary(self, profile: dict) -> dict:
        """Constrói resumo otimizado do perfil financeiro"""
        return {
            "basic_info": {
                "risk_profile": profile.get("classificacao_risco", "desconhecido"),
                "financial_score": self._calculate_financial_score(profile)
            },
            "key_metrics": {
                "monthly_income": float(profile.get("renda_mensal", 0)),
                "monthly_expenses": float(profile.get("gastos_mensais", 0)), 
                "savings_capacity": float(profile.get("capacidade_poupanca", 0)),
                "debt_to_income_ratio": profile.get("debt_to_income") or 0,
                "emergency_fund_months": self._calculate_emergency_fund_months(profile)
            },
            "financial_goals": self._extract_goals(profile)
        }
    
    def _build_transactions_analysis(self, transactions: dict) -> dict:
        """Constrói análise de transações otimizada para visualização"""
        categories = transactions.get("totais_por_categoria", [])
        raw_transactions = transactions.get("transacoes", [])
        
        # Cores predefinidas para categorias
        category_colors = {
            "Alimentação": "#FF6B6B", "Moradia": "#4ECDC4", "Transporte": "#45B7D1",
            "Saúde": "#96CEB4", "Educação": "#FFEAA7", "Lazer": "#DDA0DD",
            "Serviços": "#98D8C8", "Renda": "#82E0AA", "Transferências": "#D5A6BD",
            "Mercado": "#FFB347", "Streaming": "#B19CD9", "Investimentos": "#A8E6CF",
            "Outros": "#95A5A6"
        }
        
        total_expenses = sum(abs(float(cat.get("valor", 0))) for cat in categories if float(cat.get("valor", 0)) < 0)
        total_income = sum(float(cat.get("valor", 0)) for cat in categories if float(cat.get("valor", 0)) > 0)
        
        categories_breakdown = []
        for cat in categories:
            valor = float(cat.get("valor", 0))
            categoria = cat.get("categoria", "Outros")
            
            # Contar transações desta categoria
            cat_transactions = [t for t in raw_transactions if t.get("categoria") == categoria]
            
            categories_breakdown.append({
                "category": categoria,
                "amount": valor,
                "percentage": (abs(valor) / total_expenses * 100) if total_expenses > 0 else 0,
                "transaction_count": len(cat_transactions),
                "color": category_colors.get(categoria, "#95A5A6"),
                "icon": self._get_category_icon(categoria),
                "trend": "stable",  # Pode ser calculado com dados históricos
                "benchmark_comparison": "normal"  # Placeholder
            })
        
        return {
            "summary": {
                "total_transactions": len(raw_transactions),
                "total_expenses": -total_expenses,
                "total_income": total_income,
                "net_flow": total_income - total_expenses,
                "analysis_period": transactions.get("timestamp", "")
            },
            "categories_breakdown": sorted(categories_breakdown, key=lambda x: abs(x["amount"]), reverse=True),
            "top_transactions": self._get_top_transactions(raw_transactions)
        }
    
    def _build_financial_advice(self, advice: dict, profile: dict) -> dict:
        """Estrutura conselhos financeiros por timeline"""
        advice_data = advice.get("advice", {})
        
        overall_assessment = {
            "health_score": self._calculate_financial_score(profile),
            "main_strengths": self._identify_strengths(profile),
            "main_concerns": self._identify_concerns(profile),
            "priority_level": "medium"  # Baseado na análise
        }
        
        # Organizar recomendações por timeline
        recommendations = {
            "immediate": self._extract_timeline_advice(advice_data.get("plano", {}).get("agora", [])),
            "short_term": self._extract_timeline_advice(advice_data.get("plano", {}).get("30_dias", [])),  
            "medium_term": self._extract_timeline_advice(advice_data.get("plano", {}).get("90_dias", [])),
            "long_term": self._extract_timeline_advice(advice_data.get("plano", {}).get("12_meses", []))
        }
        
        return {
            "overall_assessment": overall_assessment,
            "recommendations_by_timeline": recommendations,
            "measurable_goals": advice_data.get("metas_mensuraveis", [])
        }
    
    def _build_visualizations(self, transactions: dict, profile: dict, advice: dict) -> dict:
        """Gera configurações prontas para gráficos"""
        categories = transactions.get("totais_por_categoria", [])
        
        # Gráfico de pizza para despesas
        pie_data = []
        for cat in categories:
            valor = float(cat.get("valor", 0))
            if valor < 0:  # Apenas despesas
                pie_data.append({
                    "label": cat.get("categoria"),
                    "value": abs(valor),
                    "color": self._get_category_color(cat.get("categoria"))
                })
        
        # Gráfico de progresso para meta
        savings_progress = {
            "chart_type": "progress",
            "current_value": float(profile.get("ativos_liquidos", 0)),
            "target_value": float(profile.get("objetivo", {}).get("valor_objetivo", 100000)),
            "percentage": 0,  # Calcular baseado nos valores
            "color": "#96CEB4"
        }
        
        if savings_progress["target_value"] > 0:
            savings_progress["percentage"] = (savings_progress["current_value"] / savings_progress["target_value"]) * 100
        
        return {
            "expense_pie_chart": {
                "chart_type": "pie", 
                "data": pie_data[:8],  # Top 8 categorias
                "config": {"responsive": True, "legend_position": "bottom", "show_percentages": True}
            },
            "savings_progress_chart": savings_progress,
            "monthly_flow_chart": {
                "chart_type": "bar",
                "data": [
                    {"label": "Receitas", "value": float(profile.get("renda_mensal", 0)), "color": "#82E0AA"},
                    {"label": "Gastos", "value": -float(profile.get("gastos_mensais", 0)), "color": "#FF6B6B"},
                    {"label": "Poupança", "value": float(profile.get("capacidade_poupanca", 0)), "color": "#96CEB4"}
                ],
                "config": {"responsive": True, "scales": {"y": {"beginAtZero": True}}}
            }
        }
    
    def _build_comparative_metrics(self, profile: dict, transactions: dict) -> dict:
        """Gera métricas comparativas e benchmarks"""
        renda = float(profile.get("renda_mensal", 0))
        gastos = float(profile.get("gastos_mensais", 0))
        poupanca = float(profile.get("capacidade_poupanca", 0))
        
        savings_rate = (poupanca / renda * 100) if renda > 0 else 0
        debt_ratio = (profile.get("debt_to_income") or 0) * 100
        
        return {
            "benchmarks": {
                "savings_rate": {
                    "user_value": round(savings_rate, 1),
                    "average_similar_profile": 22.5,
                    "ideal_range": [20, 30],
                    "status": "good" if 20 <= savings_rate <= 30 else "needs_improvement"
                },
                "debt_ratio": {
                    "user_value": round(debt_ratio, 1),
                    "average_similar_profile": 25.8,
                    "ideal_range": [0, 20],
                    "status": "excellent" if debt_ratio <= 20 else "warning"
                }
            },
            "peer_comparison": {
                "income_bracket": self._get_income_bracket(renda),
                "percentile_ranking": self._calculate_percentile(profile)
            }
        }
    
    def _build_ui_config(self, ui_prefs: dict) -> dict:
        """Configurações de UI e tema"""
        return {
            "theme": {
                "primary_color": ui_prefs.get("primary_color", "#2C3E50"),
                "success_color": "#27AE60",
                "warning_color": "#F39C12",
                "danger_color": "#E74C3C"
            },
            "responsive_breakpoints": {
                "mobile": "768px",
                "tablet": "1024px", 
                "desktop": "1200px"
            },
            "chart_preferences": {
                "animation_duration": 800,
                "default_font_family": "Inter, sans-serif",
                "grid_color": "#ECF0F1"
            }
        }
    
    def _build_alerts(self, profile: dict, transactions: dict, advice: dict) -> dict:
        """Gera alertas e notificações importantes"""
        alerts = {"urgent": [], "informational": []}
        
        # Verificar reserva de emergência
        emergency_months = self._calculate_emergency_fund_months(profile)
        if emergency_months < 3:
            alerts["urgent"].append({
                "id": "low_emergency_fund",
                "type": "warning",
                "title": "Reserva de Emergência Baixa",
                "message": f"Sua reserva cobre apenas {emergency_months:.1f} meses. Recomendado: 6 meses.",
                "action_required": True,
                "priority": "high"
            })
        
        # Verificar debt-to-income alto
        debt_ratio = profile.get("debt_to_income", 0)
        if debt_ratio > 0.3:
            alerts["urgent"].append({
                "id": "high_debt_ratio", 
                "type": "danger",
                "title": "Endividamento Elevado",
                "message": f"Seu comprometimento de renda é {debt_ratio*100:.1f}%. Ideal: abaixo de 30%.",
                "action_required": True,
                "priority": "high"
            })
        
        return alerts
    
    # Métodos auxiliares
    def _calculate_financial_score(self, profile: dict) -> float:
        """Calcula score financeiro de 0-10"""
        score = 5.0  # Base
        
        # Capacidade de poupança (+2 pontos máximo)
        poupanca = float(profile.get("capacidade_poupanca", 0))
        renda = float(profile.get("renda_mensal", 0))
        if renda > 0:
            savings_rate = poupanca / renda
            score += min(2.0, savings_rate * 10)
        
        # Debt-to-income (-3 pontos máximo)
        debt_ratio = profile.get("debt_to_income", 0)
        score -= debt_ratio * 3
        
        # Reserva de emergência (+1 ponto máximo)
        emergency_months = self._calculate_emergency_fund_months(profile)
        score += min(1.0, emergency_months / 6)
        
        return max(0, min(10, round(score, 1)))
    
    def _calculate_emergency_fund_months(self, profile: dict) -> float:
        """Calcula quantos meses de gastos a reserva cobre"""
        liquidos = float(profile.get("ativos_liquidos", 0))
        gastos = float(profile.get("gastos_mensais", 0))
        
        return liquidos / gastos if gastos > 0 else 0
    
    def _get_category_color(self, category: str) -> str:
        """Retorna cor para categoria"""
        colors = {
            "Alimentação": "#FF6B6B", "Moradia": "#4ECDC4", "Transporte": "#45B7D1",
            "Saúde": "#96CEB4", "Educação": "#FFEAA7", "Lazer": "#DDA0DD",
            "Serviços": "#98D8C8", "Renda": "#82E0AA", "Transferências": "#D5A6BD",
            "Mercado": "#FFB347", "Streaming": "#B19CD9", "Investimentos": "#A8E6CF"
        }
        return colors.get(category, "#95A5A6")
    
    def _get_category_icon(self, category: str) -> str:
        """Retorna ícone FontAwesome para categoria"""
        icons = {
            "Alimentação": "utensils", "Moradia": "home", "Transporte": "car",
            "Saúde": "heartbeat", "Educação": "graduation-cap", "Lazer": "gamepad",
            "Serviços": "cog", "Renda": "dollar-sign", "Transferências": "exchange-alt",
            "Mercado": "shopping-cart", "Streaming": "play", "Investimentos": "chart-line"
        }
        return icons.get(category, "question")
    
    def _extract_goals(self, profile: dict) -> dict:
        """Extrai e formata objetivos financeiros"""
        objetivo = profile.get("objetivo", {})
        return {
            "primary_goal": objetivo.get("descricao", "Não definido"),
            "target_amount": float(objetivo.get("valor_objetivo", 0)),
            "target_date": objetivo.get("prazo", ""),
            "progress_percentage": 0  # Calcular baseado em dados reais
        }
    
    def _identify_strengths(self, profile: dict) -> list:
        """Identifica pontos fortes financeiros"""
        strengths = []
        
        if float(profile.get("capacidade_poupanca", 0)) > 0:
            strengths.append("Boa capacidade de poupança")
        
        debt_ratio = profile.get("debt_to_income", 0)
        if debt_ratio < 0.2:
            strengths.append("Baixo endividamento")
            
        return strengths
    
    def _identify_concerns(self, profile: dict) -> list:
        """Identifica preocupações financeiras"""
        concerns = []
        
        emergency_months = self._calculate_emergency_fund_months(profile)
        if emergency_months < 3:
            concerns.append("Reserva de emergência insuficiente")
            
        return concerns
    
    def _extract_timeline_advice(self, advice_list: list) -> list:
        """Converte lista de conselhos em formato estruturado"""
        structured_advice = []
        
        for i, advice in enumerate(advice_list[:5]):  # Máximo 5 por timeline
            structured_advice.append({
                "id": f"advice_{i+1}",
                "title": advice[:50] + "..." if len(advice) > 50 else advice,
                "description": advice,
                "impact": "medium",  # Placeholder
                "effort": "medium",  # Placeholder
                "estimated_savings": 0  # Placeholder
            })
        
        return structured_advice
    
    def _get_top_transactions(self, transactions: list) -> list:
        """Retorna top transações por valor"""
        sorted_tx = sorted(transactions, key=lambda x: abs(float(x.get("valor", 0))), reverse=True)
        
        top_transactions = []
        for tx in sorted_tx[:5]:
            valor = float(tx.get("valor", 0))
            top_transactions.append({
                "description": tx.get("descricao", ""),
                "amount": valor,
                "date": tx.get("data", ""),
                "category": tx.get("categoria", "Outros"),
                "impact_level": "high" if abs(valor) > 500 else "medium" if abs(valor) > 100 else "low"
            })
        
        return top_transactions
    
    def _get_analysis_period(self, transactions: dict) -> str:
        """Extrai período da análise"""
        return transactions.get("timestamp", "")[:7] if transactions.get("timestamp") else ""
    
    def _get_income_bracket(self, renda: float) -> str:
        """Determina faixa de renda"""
        if renda < 3000:
            return "0-3000"
        elif renda < 6000:
            return "3000-6000"
        elif renda < 10000:
            return "6000-10000"
        else:
            return "10000+"
    
    def _calculate_percentile(self, profile: dict) -> int:
        """Calcula percentil aproximado (placeholder)"""
        score = self._calculate_financial_score(profile)
        return int(score * 10)

# ----------------------------------------------------------------------------
# OPTIONAL: minimal registry that CrewAI can import
# ----------------------------------------------------------------------------

__all__ = [
    "DatabaseFinancialProfileTool",
    "UserProfileBuilderTool",
    "BankStatementParserTool", 
    "FinancialAdvisorTool",
    "ModelEvaluatorTool",
    "ReportGeneratorTool",
    "DashboardDataCompilerTool",
    "DatabaseFinancialProfileArgs",
    "UserProfileBuilderArgs",
    "BankStatementParserArgs",
    "FinancialAdvisorArgs",
    "ModelEvaluatorArgs",
    "ReportGeneratorArgs",
    "DashboardDataCompilerArgs",
    "LocalLLMClient",
]
