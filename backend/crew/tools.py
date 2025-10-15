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
from typing import Any, Dict, List, Optional, Tuple, ClassVar, Union

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
    def __init__(self,
                 cmd_template: Optional[str] = None,
                 default_model: Optional[str] = None,
                 timeout: Optional[int] = None):
        #self.cmd_template = cmd_template or os.getenv("LLM_CMD", "ollama run {model} --prompt {prompt}")
        self.cmd_template = os.getenv("LLM_CMD", "ollama run {model} {prompt}")
        self.default_model = default_model or os.getenv("LLM_MODEL", "gemma3")
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", "120"))

    def generate(self, prompt: str, model: Optional[str] = None) -> str:
        model = model or self.default_model
        if "{prompt}" not in self.cmd_template:
            raise JSONableError("cmd_template deve conter {prompt}")

        #cmd = self.cmd_template.format(prompt=shlex.quote(prompt), model=model)
        cmd = self.cmd_template.format(prompt=f'"{prompt}"', model=model)
        print(f"\n[DEBUG] Executando comando LLM:\n{cmd}\n")

        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            raise JSONableError("Local LLM timed out")

        if proc.returncode != 0:
            raise JSONableError(f"Local LLM failed: {proc.stderr.strip()}")

        print(f"[DEBUG] Saída bruta do modelo (primeiros 300 chars):\n{proc.stdout[:300]}\n")
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
# 1) BankStatementParserTool (CSV)
# ----------------------------------------------------------------------------

CATEGORY_MAP = {
    "mercado|supermerc|hiper|carrefour|pao de acucar|assai": "Mercado",
    "restaurante|pizza|lanchonete|ifood|ubereats": "Alimentação",
    "aluguel|condominio|iptu|imobiliaria": "Moradia",
    "energia|luz|copel|enel|eletrobras|cemig": "Moradia",
    "agua|sanepar|sabesp|corsan": "Moradia",
    "internet|vivo|claro|tim|oi|net": "Serviços",
    "uber|99|transporte|onibus|metrô|metro|estacionamento|combustivel|posto|autopass": "Transporte",
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

            if "categoria" in df.columns and df["categoria"].notnull().any():
                print("[INFO] Transações já categorizadas detectadas — pulando categorização.")
                already_categorized = True
            else:
                already_categorized = False
            
            # NOVO: Limpar descrições antes de categorizar
            df["descricao_original"] = df["descricao"]  # Backup da descrição original
            df["descricao"] = df["descricao"].apply(self._clean_description)
            
            # NOVO: Filtrar apenas despesas para categorização (valores negativos)
            df_expenses = df[df["valor"] < 0].copy()
            df_non_expenses = df[df["valor"] >= 0].copy()
            
            if already_categorized == False:
                # Categorizar apenas despesas
                if categorization_method == "ollama":
                    df_expenses = self._categorize_with_ollama(df_expenses, ollama_model, block_size)
                else:
                    df_expenses["categoria"] = df_expenses["descricao"].apply(self._categorize)
                    
                    if llm_enhanced:
                        try:
                            df_expenses = self._refine_categories_with_llm(df_expenses)
                        except Exception:
                            pass
            
                # Categorizar não-despesas como "Renda" (receitas/transferências recebidas)
                df_non_expenses["categoria"] = "Renda"
            
            # Recombinar DataFrames (sempre executar)
            df_categorized = pd.concat([df_expenses, df_non_expenses], ignore_index=True)
            df_categorized = df_categorized.sort_values("data").reset_index(drop=True)
            
            # Remover coluna "descricao_original" se existir antes de gerar output
            if "descricao_original" in df_categorized.columns:
                df_categorized = df_categorized.drop(columns=["descricao_original"])
            
            # NOVO: Remover coluna "Identificador" se existir
            if "identificador" in df_categorized.columns:
                df_categorized = df_categorized.drop(columns=["identificador"])
            if "Identificador" in df_categorized.columns:
                df_categorized = df_categorized.drop(columns=["Identificador"])
            
            # Rollups apenas para despesas (categoria != "Renda")
            df_for_totals = df_categorized[df_categorized["categoria"] != "Renda"]
            totals = (
                df_for_totals.groupby("categoria")["valor"]
                .sum()
                .reset_index()
                .sort_values("valor")
            )
            
            # Adicionar total de receitas separadamente
            total_renda = df_categorized[df_categorized["categoria"] == "Renda"]["valor"].sum()
            if total_renda > 0:
                totals = pd.concat([
                    totals,
                    pd.DataFrame([{"categoria": "Renda", "valor": total_renda}])
                ], ignore_index=True)
        
            summary = {
                "ok": True,
                "timestamp": _now_iso(),
                "method": categorization_method,
                "n_transacoes": int(len(df_categorized)),
                "n_despesas": int(len(df_expenses)),
                "n_receitas": int(len(df_non_expenses)),
                "totais_por_categoria": totals.to_dict(orient="records") if pd is not None else [],
                "transacoes": df_categorized.to_dict(orient="records") if pd is not None else [],
            }
            return json.dumps(summary, ensure_ascii=False)
        except Exception as e:
            import traceback
            return json.dumps({
                "ok": False, 
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def _clean_description(self, descricao: str) -> str:
        """
        Limpa descrição removendo conteúdo após segundo hífen.
        
        Exemplo:
        "Transferência enviada pelo Pix - COMPANHIA PIRATININGA - 04.172.213/0001-51"
        → "Transferência enviada pelo Pix - COMPANHIA PIRATININGA"
        """
        if not descricao or pd.isna(descricao):
            return ""
        
        descricao_str = str(descricao).strip()
        
        # Contar hífens
        hyphen_count = descricao_str.count(' - ')
        
        if hyphen_count >= 2:
            # Encontrar posição do segundo hífen
            parts = descricao_str.split(' - ')
            # Manter apenas as duas primeiras partes
            cleaned = ' - '.join(parts[:2])
            return cleaned.strip()
        
        return descricao_str

    def _read_csv(self, path: str):
        if pd is None:
            raise JSONableError("pandas is required for CSV parsing")
        return pd.read_csv(path)

    def _normalize_columns(self, df):
        """Normaliza nomes de colunas e valores monetários."""
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
        
        # Normalização de valores monetários
        def normalize_monetary_value(val):
            if pd.isna(val) or val == '':
                return 0.0
            
            str_val = str(val).strip()
            
            try:
                return float(str_val)
            except:
                pass
            
            # Remove símbolos de moeda
            str_val = re.sub(r'[R$\s]+', '', str_val)
            
            dot_count = str_val.count('.')
            comma_count = str_val.count(',')
            
            # Formato brasileiro: 1.234.567,89
            if comma_count == 1 and dot_count >= 1:
                str_val = str_val.replace('.', '').replace(',', '.')
            # Formato brasileiro simples: 123,45
            elif comma_count == 1 and dot_count == 0:
                str_val = str_val.replace(',', '.')
            # Separadores de milhares com vírgulas
            elif comma_count >= 1 and dot_count == 0:
                if comma_count > 1 or len(str_val.replace(',', '')) > 3:
                    str_val = str_val.replace(',', '')
                else:
                    str_val = str_val.replace(',', '.')
            
            try:
                return float(str_val)
            except:
                print(f"[WARNING] Não foi possível converter valor: '{val}' -> assumindo 0.0")
                return 0.0
        
        out["valor"] = out["valor"].apply(normalize_monetary_value)
        
        # Remover coluna Identificador se existir
        for id_col in ["identificador", "Identificador", "id", "ID"]:
            if id_col in out.columns:
                out = out.drop(columns=[id_col])
        
        return out

    def _categorize(self, descricao: str) -> str:
        """Categoriza usando regex - apenas para despesas."""
        text = (descricao or "").lower()
        for pattern, cat in CATEGORY_MAP.items():
            if re.search(pattern, text):
                return cat
        return "Outros"

    def _categorize_with_ollama(self, df, model_name: str = "gemma3", block_size: int = 10):
        """Categoriza transações usando Ollama - apenas despesas."""
        print(f"[INFO] Iniciando categorização com Ollama (modelo: {model_name})")

        if ChatOllama is None:
            print("[ERROR] ChatOllama não está disponível")
            print("[INFO] Usando fallback para categorização regex")
            return self._categorize_with_regex_fallback(df)

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
        
        print(f"[INFO] Total de transações (despesas): {len(transacoes)}")
        
        # Carrega cache
        cache_path = os.path.join(os.path.dirname(__file__), "..", CACHE_PATH)
        cache = load_cache(cache_path)
        print(f"[INFO] Cache carregado com {len(cache)} entradas")
        
        # Identifica transações que precisam categorização
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
        
        # Processa em blocos
        if transacoes_para_categorizar:
            if tqdm is not None:
                iterator = tqdm(range(0, len(transacoes_para_categorizar), block_size), desc="Categorizando")
            else:
                iterator = range(0, len(transacoes_para_categorizar), block_size)
                print(f"[INFO] Processando {len(transacoes_para_categorizar)} transações em blocos de {block_size}")
                
            for i in iterator:
                bloco = transacoes_para_categorizar[i:i+block_size]
                prompt = generate_categorization_prompt(bloco)
                
                try:
                    resposta = llm.invoke([HumanMessage(content=prompt)])
                    resultado = parse_llm_categorization_response(resposta.content, bloco)
                    
                    for trans, cat in resultado:
                        t_clean = clean_transaction_name(trans)
                        if t_clean not in cache or cache[t_clean] == "Outros":
                            cache[t_clean] = cat
                    
                    # Fallback regex para não categorizadas
                    transacoes_processadas = {clean_transaction_name(trans) for trans, _ in resultado}
                    for trans in bloco:
                        t_clean = clean_transaction_name(trans)
                        if t_clean not in transacoes_processadas and t_clean not in cache:
                            categoria_regex = self._categorize(trans)
                            cache[t_clean] = categoria_regex
                            
                except Exception as e:
                    print(f"[ERROR] Erro ao processar bloco: {e}")
                    for trans in bloco:
                        t_clean = clean_transaction_name(trans)
                        if t_clean not in cache:
                            categoria_regex = self._categorize(trans)
                            cache[t_clean] = categoria_regex
            
            save_cache(cache, cache_path)
            print(f"[INFO] Cache salvo com {len(cache)} entradas")
        
        # Aplica categorizações do cache
        categorias_finais = []
        for t in transacoes:
            t_clean = clean_transaction_name(t)
            categoria = cache.get(t_clean)
            
            if categoria:
                categorias_finais.append(categoria)
            else:
                categoria_regex = self._categorize(t)
                categorias_finais.append(categoria_regex)
        
        df_copy["categoria"] = categorias_finais
        return df_copy
    
    def _categorize_with_regex_fallback(self, df):
        """Fallback para categorização usando apenas regex."""
        print("[INFO] Usando categorização fallback com regex")
        df_copy = df.copy()
        df_copy["categoria"] = df_copy["descricao"].apply(self._categorize)
        return df_copy

    def _refine_categories_with_llm(self, df):
        """Refina categorias com LLM local."""
        client = LocalLLMClient()
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
            df["categoria"] = df["descricao"].astype(str).str.lower().map(mapping).fillna(df["categoria"])
        except Exception:
            pass
        return df

# ----------------------------------------------------------------------------
# 2) FinancialAdvisorTool (LLM plans based on profile + transactions)
# ----------------------------------------------------------------------------

from pydantic import BaseModel, Field
from typing import Optional, ClassVar

class FinancialAdvisorToolSchema(BaseModel):
    # Usar Union para aceitar múltiplos tipos explicitamente
    profile_json: Union[str, dict, list] = Field(description="JSON (string ou objeto) do UserProfileBuilderTool")
    transactions_json: Union[str, dict, list] = Field(description="JSON (string, dict ou lista) do BankStatementParserTool com transações categorizadas. OBRIGATÓRIO.")
    model: Optional[str] = Field(default="gemma3", description="Local model identifier to use")

# Rebuild do modelo para resolver referências
FinancialAdvisorToolSchema.model_rebuild()

class FinancialAdvisorTool(BaseTool):
    """Gera aconselhamento financeiro estruturado com LLM local."""
    name: str = "FinancialAdvisorTool"
    description: str = (
        "Gera aconselhamento financeiro PERSONALIZADO em JSON usando LLM local."
    )

    args_schema = FinancialAdvisorToolSchema

    SYSTEM_PROMPT: ClassVar[str] = (
        "RETORNE APENAS JSON NO FORMATO EXATO ABAIXO. NÃO ADICIONE TEXTO EXTRA.\n"
        "{\n"
        '  "resumo": "Texto analisando situação financeira",\n'
        '  "alertas": ["Texto alerta 1", "Texto alerta 2"],\n'
        '  "plano": {\n'
        '    "agora": ["Ação 1", "Ação 2", "Ação 3"],\n'
        '    "30_dias": ["Meta 1", "Meta 2", "Meta 3"],\n'
        '    "12_meses": ["Objetivo 1", "Objetivo 2", "Objetivo 3"]\n'
        '  },\n'
        '  "metas_mensuraveis": [{"meta": "Descrição", "kpi": "Indicador", "meta_num": 1000, "prazo_meses": 12}]\n'
        "}\n"
        "ANÁLISE OS DADOS FINANCEIROS E RESPONDA APENAS JSON:"
    )

    def _run(self, profile_json: Any, transactions_json: Any, model: Optional[str] = None) -> str:
        """Executa o plano de aconselhamento financeiro com perfil e transações completos."""
        from datetime import datetime
        import json

        client = LocalLLMClient()
        model = model or "gemma3"

        # --- Parse seguro do perfil ---
        try:
            profile = json.loads(profile_json) if isinstance(profile_json, str) else profile_json
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Invalid profile_json: {e}"}, ensure_ascii=False)

        # --- Parse seguro das transações ---
        try:
            tx = json.loads(transactions_json) if isinstance(transactions_json, str) else transactions_json
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Invalid transactions_json: {e}"}, ensure_ascii=False)

        # Garante formato padrão para transações
        if isinstance(tx, list):
            tx = {"transacoes": tx, "totais_por_categoria": []}

        transacoes = tx.get("transacoes", [])
        totais_por_categoria = tx.get("totais_por_categoria", [])

        # --- Filtrar apenas top 5 transações que mais movimentaram (por valor absoluto) ---
        top_5_transacoes = sorted(
            transacoes, 
            key=lambda t: abs(float(t.get("valor", 0))), 
            reverse=True
        )[:5]

        # --- Cálculo de totais financeiros ---
        total_despesas = sum(
            abs(float(t.get("valor", 0))) for t in transacoes if float(t.get("valor", 0)) < 0
        )
        total_receitas = sum(
            float(t.get("valor", 0)) for t in transacoes if float(t.get("valor", 0)) > 0
        )

        # --- Preparar dados do perfil consolidado ---
        perfil_financeiro = {
            "usuario_id": profile.get("usuario_id"),
            "dados_pessoais": profile.get("dados_pessoais", {}),
            "objetivo": profile.get("objetivo", {}),
            "renda_mensal": profile.get("dados_pessoais", {}).get("renda_mensal", total_receitas),
            "total_despesas_calculado": round(total_despesas, 2),
            "total_receitas_calculado": round(total_receitas, 2),
        }

        print(f"🔍 DEBUG FinancialAdvisorTool - Perfil consolidado: {json.dumps(perfil_financeiro, ensure_ascii=False, indent=2)}")
        print(f"🔍 DEBUG FinancialAdvisorTool - Total transações: {len(transacoes)}")
        print(f"🔍 DEBUG FinancialAdvisorTool - Top 5 transações: {len(top_5_transacoes)}")
        print(f"🔍 DEBUG FinancialAdvisorTool - Total categorias: {len(totais_por_categoria)}")

        # --- Montar contexto limpo e otimizado para LLM ---
        context = {
            "perfil": perfil_financeiro,
            "resumo_gastos_por_categoria": totais_por_categoria,  # TODAS as categorias e valores
            "top_5_transacoes_maiores": [  # APENAS top 5 transações
                {
                    "data": t.get("data"),
                    "descricao": t.get("descricao"),
                    "valor": t.get("valor"),
                    "categoria": t.get("categoria")
                }
                for t in top_5_transacoes
            ]
        }

        # --- Gerar prompt simplificado ---
        prompt = (
            self.SYSTEM_PROMPT
            + "\n\nDADOS:\n"
            + f"Renda: R$ {perfil_financeiro.get('renda_mensal', 0)}\n"
            + f"Despesas: R$ {perfil_financeiro.get('total_despesas_calculado', 0)}\n"
            + f"Objetivo: {perfil_financeiro.get('objetivo', {}).get('descricao', 'N/A')}\n"
            + f"Meta: R$ {perfil_financeiro.get('objetivo', {}).get('valor_objetivo', 0)}\n"
            + f"Categorias: {json.dumps(totais_por_categoria[:3], ensure_ascii=False)}\n"
        )

        print(f"🔍 DEBUG FinancialAdvisorTool - Contexto enviado: {json.dumps(context, ensure_ascii=False, indent=2)}")

        try:
            raw = client.generate(prompt, model=model).strip()
            print(f"🔍 DEBUG FinancialAdvisorTool - Resposta raw do LLM: {raw}")

            if not raw or raw.strip() == "":
                raise JSONableError("Empty or whitespace-only response from LLM")
            
            # Tentar extrair JSON da resposta
            if not raw.lstrip().startswith("{"):
                print(f"🔍 DEBUG - Resposta não começa com '{{', tentando extrair JSON...")
                raw_json = _extract_json(raw)
            else:
                raw_json = raw

            print(f"🔍 DEBUG FinancialAdvisorTool - JSON extraído: {raw_json}")

            if not raw_json or raw_json.strip() == "":
                raise JSONableError("JSON extraction resulted in empty string")

            json_data = json.loads(raw_json)

            return json.dumps({
                "ok": True,
                "timestamp": datetime.now().isoformat(),
                "advice": json_data
            }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "ok": False,
                "error": f"Erro ao gerar conselho: {e}",
                "traceback": str(raw)[:400] if 'raw' in locals() and raw is not None else "No raw response",
                "prompt_usado": prompt[:500] if 'prompt' in locals() else "No prompt"  # útil para debug
            }, ensure_ascii=False)
        
# from typing import Any, Optional, Union
# from pydantic import BaseModel, Field
# import json, re
# from datetime import datetime

# class FinancialAdvisorToolSchema(BaseModel):
#     profile_json: Union[str, dict] = Field(
#         description="JSON (string ou objeto) do perfil do usuário contendo idade, renda e objetivos."
#     )
#     categories_json: Union[str, dict, list] = Field(
#         description="Resumo das categorias e seus valores, no formato [{'categoria': 'Moradia', 'valor': -1200.0}, ...]"
#     )
#     model: Optional[str] = Field(default="gemma3", description="Identificador do modelo Ollama a ser usado")

# FinancialAdvisorToolSchema.model_rebuild()


# class FinancialAdvisorTool(BaseTool):
#     name: str = "FinancialAdvisorTool"
#     description: str = (
#         "Gera aconselhamento financeiro PERSONALIZADO em JSON. "
#         "Usa o perfil e os totais por categoria para criar plano de ação."
#     )
#     args_schema = FinancialAdvisorToolSchema

#     SYSTEM_PROMPT: ClassVar[str] = (
#         "⚠️ MODO ESTRITO: RESPOSTA APENAS JSON ⚠️\n"
#         "Você é um consultor financeiro automatizado. Não cumprimente, não explique, não use markdown.\n"
#         "Formato obrigatório:\n"
#         "{\n"
#         "  \"resumo\": \"...\",\n"
#         "  \"alertas\": [\"...\"],\n"
#         "  \"plano\": {\"agora\": [\"...\"], \"30_dias\": [\"...\"], \"12_meses\": [\"...\"]},\n"
#         "  \"metas_mensuraveis\": [{\"meta\": \"...\", \"kpi\": \"...\", \"meta_num\": 0, \"prazo_meses\": 12}]\n"
#         "}\n"
#         "Não adicione nada fora das chaves."
#     )

#     def _run(self, profile_json: Any, categories_json: Any, model: Optional[str] = None) -> str:

#         client = LocalLLMClient()
#         model = model or "gemma3"

#         try:
#             profile = json.loads(profile_json) if isinstance(profile_json, str) else profile_json
#             categories = json.loads(categories_json) if isinstance(categories_json, str) else categories_json
#         except Exception as e:
#             return json.dumps({"ok": False, "error": f"Erro ao parsear JSON de entrada: {e}"}, ensure_ascii=False)

#         # Prompt minimalista e claro
#         prompt = (
#             self.SYSTEM_PROMPT
#             + "\n\nPerfil financeiro:\n"
#             + json.dumps(profile, ensure_ascii=False, indent=2)
#             + "\n\nResumo de gastos por categoria:\n"
#             + json.dumps(categories, ensure_ascii=False, indent=2)
#             + "\n\n⚠️ Responda agora APENAS COM JSON válido ⚠️"
#         )

#         try:
#             raw = client.generate(prompt, model=model)
#             raw = re.sub(r"^[`']{3,}\s*json\s*|[`']{3,}\s*$", "", raw.strip(), flags=re.IGNORECASE)
#             match = re.search(r'\{(?:[^{}]|(?R))*\}', raw, re.DOTALL)
#             json_str = match.group(0) if match else "{}"
#             advice = json.loads(json_str)

#             return json.dumps({
#                 "ok": True,
#                 "timestamp": datetime.now().isoformat(),
#                 "advice": advice
#             }, ensure_ascii=False, indent=2)
#         except Exception as e:
#             return json.dumps({
#                 "ok": False,
#                 "error": f"Erro ao gerar conselho: {str(e)}",
#                 "resposta_bruta": raw[:300] if 'raw' in locals() else None
#             }, ensure_ascii=False)

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
    """Extrai o primeiro bloco JSON válido de uma string, sem usar regex recursivo (compatível com Python)."""
    import json
    
    if not text or text.strip() == "":
        raise ValueError("Texto vazio fornecido para extração de JSON.")

    stack = []
    start = None

    for i, c in enumerate(text):
        if c == '{':
            if not stack:
                start = i
            stack.append(c)
        elif c == '}':
            if stack:
                stack.pop()
                if not stack and start is not None:
                    candidate = text[start:i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except Exception:
                        # continua procurando o próximo bloco
                        pass

    # Se chegar aqui, nenhum JSON válido foi encontrado
    raise ValueError(f"Não foi possível extrair JSON da resposta do modelo. Texto recebido: {text[:200]}...")

# ============================================================================
# 6) DashboardDataCompilerTool (Estruturação para Frontend React)
# ============================================================================

class DashboardDataCompilerToolSchema(BaseModel):
    transactions_json: Union[str, dict, list] = Field(description="[OBRIGATÓRIO] JSON das transações categorizadas (BankStatementParserTool) com array 'transacoes' e 'totais_por_categoria'")
    advice_json: Union[str, dict, list] = Field(description="[OBRIGATÓRIO] JSON dos conselhos financeiros (FinancialAdvisorTool) contendo plano de ação e recomendações")
    evaluation_json: Optional[Any] = Field(default=None, description="[OPCIONAL] JSON da avaliação dos modelos - Se None, usa objeto fixo padrão")
    ui_preferences: Optional[str] = Field(default=None, description="[OPCIONAL] Preferências de UI (tema, layout, etc.)")

class DashboardDataCompilerTool(BaseTool):
    name: str = "DashboardDataCompiler"
    description: str = (
        "Compila dados financeiros (transações categorizadas e conselhos) em formato JSON otimizado "
        "para renderização no dashboard React. REQUER: transactions_json e advice_json. "
        "OPCIONAL: evaluation_json."
    )
    args_schema = DashboardDataCompilerToolSchema

    def _run(
        self, 
        transactions_json: Union[str, dict, list],
        advice_json: Union[str, dict, list],
        evaluation_json: Optional[Any] = None,
        ui_preferences: Optional[str] = None
    ) -> str:
        try:
            # Normalizar dados de entrada com validação adicional
            def normalize_json_input(data, field_name: str):
                if data is None:
                    return None
                
                # Se já é dict, retorna direto
                if isinstance(data, dict):
                    return data
                
                # Se é string
                if isinstance(data, str):
                    # Ignorar placeholders comuns
                    if data.strip() in ["<transactions JSON>", "<advice JSON>", "transactions JSON", "advice JSON", "None", ""]:
                        print(f"[ERROR] {field_name} contém placeholder inválido: '{data}'")
                        return None
                    
                    # Tentar fazer parse do JSON
                    try:
                        return json.loads(data)
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] Falha ao parsear {field_name}: {e}")
                        print(f"[DEBUG] Conteúdo recebido: {data[:200]}...")
                        return None
                
                # Tipo não suportado
                print(f"[ERROR] {field_name} tem tipo não suportado: {type(data)}")
                return None
            
            # Parse dos dados OBRIGATÓRIOS com validação
            print("[INFO] Parseando transactions_json...")
            transactions = normalize_json_input(transactions_json, "transactions_json")
            
            print("[INFO] Parseando advice_json...")
            advice = normalize_json_input(advice_json, "advice_json")
            
            # Validação crítica com mensagens detalhadas
            if transactions is None:
                error_msg = (
                    "transactions_json é obrigatório mas está inválido ou ausente. "
                    "Certifique-se de passar o JSON completo retornado pela extract_task."
                )
                return json.dumps({"ok": False, "error": error_msg})
            
            if advice is None:
                error_msg = (
                    "advice_json é obrigatório mas está inválido ou ausente. "
                    "Certifique-se de passar o JSON completo retornado pela advice_task."
                )
                return json.dumps({"ok": False, "error": error_msg})
            
            # Validação de estrutura mínima
            if not isinstance(transactions.get("transacoes"), list):
                return json.dumps({
                    "ok": False, 
                    "error": "transactions_json deve conter array 'transacoes'"
                })
            
            if not isinstance(advice.get("advice"), dict):
                return json.dumps({
                    "ok": False,
                    "error": "advice_json deve conter objeto 'advice'"
                })
            
            print("[INFO] Dados obrigatórios validados com sucesso")
            
            # Parse dos dados OPCIONAIS
            if evaluation_json is None or (isinstance(evaluation_json, str) and evaluation_json.strip() == "None"):
                evaluation = {
                    "ok": True,
                    "message": "Model evaluation disabled",
                    "model_used": "ollama/gemma3",
                    "scores": [],
                    "winner": {"model": "gemma3", "total": 0}
                }
                print("[INFO] evaluation_json não fornecido, usando objeto fixo padrão")
            else:
                evaluation = normalize_json_input(evaluation_json, "evaluation_json")
                if evaluation is None:
                    evaluation = {
                        "ok": True,
                        "message": "Model evaluation disabled",
                        "model_used": "ollama/gemma3",
                        "scores": [],
                        "winner": {"model": "gemma3", "total": 0}
                    }
            
            ui_prefs = json.loads(ui_preferences) if ui_preferences else {}
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[ERROR] Exception durante parse: {error_details}")
            return json.dumps({
                "ok": False, 
                "error": f"Erro ao parsear JSONs de entrada: {str(e)}",
                "details": error_details
            })
        
        try:
            # Gerar timestamp e metadados
            now = dt.datetime.now()
            
            # 1. TRANSACTIONS ANALYSIS - Dados categorizados otimizados para charts
            transactions_analysis = self._build_transactions_analysis(transactions)
            
            # 2. FINANCIAL ADVICE - Conselhos estruturados por timeline
            financial_advice = self._build_financial_advice(advice, transactions)
            
            # 3. VISUALIZATIONS - Datasets prontos para gráficos
            visualizations = self._build_visualizations(transactions, advice)
            
            # 4. COMPARATIVE METRICS - Benchmarks baseados apenas em transações
            comparative_metrics = self._build_comparative_metrics(transactions)
            
            # 5. UI CONFIG - Configurações de tema e layout
            ui_config = self._build_ui_config(ui_prefs)
            
            # 6. ALERTS - Notificações importantes baseadas em transações
            alerts = self._build_alerts(transactions, advice)
            
            # Compilação final
            dashboard_data = {
                "metadata": {
                    "generated_at": now.isoformat(),
                    "data_version": "v1.0",
                    "frontend_compatibility": "react_v18+",
                    "total_data_points": len(transactions.get("transacoes", [])),
                    "analysis_period": self._get_analysis_period(transactions)
                },
                "transactions_analysis": transactions_analysis,
                "financial_advice": financial_advice,
                "visualizations": visualizations,
                "comparative_metrics": comparative_metrics,
                "ui_config": ui_config,
                "alerts_and_notifications": alerts,
                "model_info": {
                    "llm_used": evaluation.get("model_used", "ollama/gemma3"),
                    "evaluation_enabled": evaluation.get("ok", False)
                }
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
                "trend": "stable",
                "benchmark_comparison": "normal"
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
    
    def _build_financial_advice(self, advice: dict, transactions: dict) -> dict:
        """Estrutura conselhos financeiros por timeline"""
        advice_data = advice.get("advice", {})
        
        # Calcular métricas básicas das transações
        categories = transactions.get("totais_por_categoria", [])
        total_expenses = sum(abs(float(cat.get("valor", 0))) for cat in categories if float(cat.get("valor", 0)) < 0)
        total_income = sum(float(cat.get("valor", 0)) for cat in categories if float(cat.get("valor", 0)) > 0)
        net_flow = total_income - total_expenses
        
        overall_assessment = {
            "health_score": self._calculate_health_score_from_transactions(transactions),
            "main_strengths": self._identify_strengths_from_transactions(transactions),
            "main_concerns": self._identify_concerns_from_transactions(transactions),
            "priority_level": "high" if net_flow < 0 else "medium" if net_flow < total_income * 0.2 else "low"
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
            "measurable_goals": advice_data.get("metas_mensuraveis", []),
            "summary": advice_data.get("resumo", ""),
            "alerts": advice_data.get("alertas", [])
        }
    
    def _build_visualizations(self, transactions: dict, advice: dict) -> dict:
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
        
        # Gráfico de fluxo mensal
        total_income = sum(float(cat.get("valor", 0)) for cat in categories if float(cat.get("valor", 0)) > 0)
        total_expenses = sum(abs(float(cat.get("valor", 0))) for cat in categories if float(cat.get("valor", 0)) < 0)
        net_savings = total_income - total_expenses
        
        return {
            "expense_pie_chart": {
                "chart_type": "pie",
                "data": pie_data[:8],  # Top 8 categorias
                "config": {"responsive": True, "legend_position": "bottom", "show_percentages": True}
            },
            "monthly_flow_chart": {
                "chart_type": "bar",
                "data": [
                    {"label": "Receitas", "value": total_income, "color": "#82E0AA"},
                    {"label": "Gastos", "value": -total_expenses, "color": "#FF6B6B"},
                    {"label": "Saldo", "value": net_savings, "color": "#96CEB4"}
                ],
                "config": {"responsive": True, "scales": {"y": {"beginAtZero": True}}}
            },
            "category_trend_chart": {
                "chart_type": "horizontal_bar",
                "data": sorted(pie_data, key=lambda x: x["value"], reverse=True)[:5],
                "config": {"responsive": True}
            }
        }
    
    def _build_comparative_metrics(self, transactions: dict) -> dict:
        """Gera métricas comparativas baseadas em transações"""
        categories = transactions.get("totais_por_categoria", [])
        total_income = sum(float(cat.get("valor", 0)) for cat in categories if float(cat.get("valor", 0)) > 0)
        total_expenses = sum(abs(float(cat.get("valor", 0))) for cat in categories if float(cat.get("valor", 0)) < 0)
        
        savings_amount = total_income - total_expenses
        savings_rate = (savings_amount / total_income * 100) if total_income > 0 else 0
        
        return {
            "benchmarks": {
                "savings_rate": {
                    "user_value": round(savings_rate, 1),
                    "average_similar_profile": 22.5,
                    "ideal_range": [20, 30],
                    "status": "good" if 20 <= savings_rate <= 30 else "needs_improvement"
                }
            },
            "spending_patterns": {
                "monthly_income": total_income,
                "monthly_expenses": total_expenses,
                "net_savings": savings_amount,
                "savings_rate_percentage": round(savings_rate, 1)
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
            "chart_preferences": {
                "animation_duration": 800,
                "default_font_family": "Inter, sans-serif"
            }
        }
    
    def _build_alerts(self, transactions: dict, advice: dict) -> dict:
        """Gera alertas baseados em transações e conselhos"""
        alerts = {"urgent": [], "informational": []}
        
        categories = transactions.get("totais_por_categoria", [])
        total_income = sum(float(cat.get("valor", 0)) for cat in categories if float(cat.get("valor", 0)) > 0)
        total_expenses = sum(abs(float(cat.get("valor", 0))) for cat in categories if float(cat.get("valor", 0)) < 0)
        
        # Alerta de gastos maiores que renda
        if total_expenses > total_income:
            alerts["urgent"].append({
                "id": "negative_balance",
                "type": "danger",
                "title": "Gastos Superiores à Renda",
                "message": f"Seus gastos (R$ {total_expenses:.2f}) superam sua renda (R$ {total_income:.2f}).",
                "action_required": True,
                "priority": "critical"
            })
        
        # Alerta de baixa taxa de poupança
        savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0
        if 0 < savings_rate < 10:
            alerts["urgent"].append({
                "id": "low_savings_rate",
                "type": "warning",
                "title": "Taxa de Poupança Baixa",
                "message": f"Você está poupando apenas {savings_rate:.1f}% da sua renda. Ideal: 20-30%.",
                "action_required": True,
                "priority": "high"
            })
        
        # Alertas dos conselhos LLM
        advice_alerts = advice.get("advice", {}).get("alertas", [])
        for i, alert_text in enumerate(advice_alerts[:3]):  # Máximo 3 alertas
            alerts["informational"].append({
                "id": f"llm_alert_{i}",
                "type": "info",
                "title": "Recomendação do Consultor",
                "message": alert_text,
                "action_required": False,
                "priority": "medium"
            })
        
        return alerts
    
    # Métodos auxiliares simplificados
    def _calculate_health_score_from_transactions(self, transactions: dict) -> float:
        """Calcula score de saúde financeira baseado apenas em transações"""
        categories = transactions.get("totais_por_categoria", [])
        total_income = sum(float(cat.get("valor", 0)) for cat in categories if float(cat.get("valor", 0)) > 0)
        total_expenses = sum(abs(float(cat.get("valor", 0))) for cat in categories if float(cat.get("valor", 0)) < 0)
        
        if total_income == 0:
            return 3.0
        
        savings_rate = (total_income - total_expenses) / total_income
        score = 5.0 + (savings_rate * 5)  # Base 5, até 10 com 100% de poupança
        
        return max(0, min(10, round(score, 1)))
    
    def _identify_strengths_from_transactions(self, transactions: dict) -> list:
        """Identifica pontos fortes baseados em transações"""
        strengths = []
        
        categories = transactions.get("totais_por_categoria", [])
        total_income = sum(float(cat.get("valor", 0)) for cat in categories if float(cat.get("valor", 0)) > 0)
        total_expenses = sum(abs(float(cat.get("valor", 0))) for cat in categories if float(cat.get("valor", 0)) < 0)
        
        if total_income > total_expenses:
            savings = total_income - total_expenses
            strengths.append(f"Saldo positivo de R$ {savings:.2f}")
        
        if total_income > 0:
            savings_rate = (total_income - total_expenses) / total_income * 100
            if savings_rate > 20:
                strengths.append(f"Boa taxa de poupança ({savings_rate:.1f}%)")
        
        return strengths
    
    def _identify_concerns_from_transactions(self, transactions: dict) -> list:
        """Identifica preocupações baseadas em transações"""
        concerns = []
        
        categories = transactions.get("totais_por_categoria", [])
        total_income = sum(float(cat.get("valor", 0)) for cat in categories if float(cat.get("valor", 0)) > 0)
        total_expenses = sum(abs(float(cat.get("valor", 0))) for cat in categories if float(cat.get("valor", 0)) < 0)
        
        if total_expenses > total_income:
            concerns.append("Gastos superiores à renda")
        
        if total_income > 0:
            savings_rate = (total_income - total_expenses) / total_income * 100
            if savings_rate < 10:
                concerns.append(f"Taxa de poupança muito baixa ({savings_rate:.1f}%)")
        
        return concerns
    
    # Métodos auxiliares mantidos do código original
    def _get_category_color(self, category: str) -> str:
        colors = {
            "Alimentação": "#FF6B6B", "Moradia": "#4ECDC4", "Transporte": "#45B7D1",
            "Saúde": "#96CEB4", "Educação": "#FFEAA7", "Lazer": "#DDA0DD",
            "Serviços": "#98D8C8", "Renda": "#82E0AA", "Transferências": "#D5A6BD",
            "Mercado": "#FFB347", "Streaming": "#B19CD9", "Investimentos": "#A8E6CF"
        }
        return colors.get(category, "#95A5A6")
    
    def _get_category_icon(self, category: str) -> str:
        icons = {
            "Alimentação": "utensils", "Moradia": "home", "Transporte": "car",
            "Saúde": "heartbeat", "Educação": "graduation-cap", "Lazer": "gamepad",
            "Serviços": "cog", "Renda": "dollar-sign", "Transferências": "exchange-alt",
            "Mercado": "shopping-cart", "Streaming": "play", "Investimentos": "chart-line"
        }
        return icons.get(category, "question")
    
    def _extract_timeline_advice(self, advice_list: list) -> list:
        structured_advice = []
        for i, advice in enumerate(advice_list[:5]):
            structured_advice.append({
                "id": f"advice_{i+1}",
                "title": advice[:50] + "..." if len(advice) > 50 else advice,
                "description": advice,
                "impact": "medium",
                "effort": "medium"
            })
        return structured_advice
    
    def _get_top_transactions(self, transactions: list) -> list:
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
        return transactions.get("timestamp", "")[:7] if transactions.get("timestamp") else ""

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
