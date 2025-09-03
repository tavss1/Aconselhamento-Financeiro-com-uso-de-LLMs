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

import io
import os
import re
import json
import csv
import math
import time
import glob
import uuid
import shlex
import pickle
import random
import string
import zipfile
import logging
import pathlib
import datetime as dt
import subprocess
from typing import Any, Dict, List, Optional, Tuple

# CrewAI BaseTool
try:
    from crewai_tools import BaseTool
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

# Optional: ofxparse for .ofx support
try:
    from ofxparse import OfxParser  # type: ignore
except Exception:
    OfxParser = None


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
        self.cmd_template = cmd_template or os.getenv("LLM_CMD", "ollama run {model} --prompt {prompt}")
        self.default_model = default_model or os.getenv("LLM_MODEL", "llama3:8b")
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
# 1) UserProfileBuilderTool
# ----------------------------------------------------------------------------

class UserProfileBuilderArgs(BaseModel):
    questionnaire_json: str = Field(description="JSON string with questionnaire answers")

class UserProfileBuilderTool(BaseTool):
    name = "UserProfileBuilderTool"
    description = (
        "Builds a normalized financial profile from a questionnaire JSON. "
        "Computes basic indicators like savings capacity, debt ratio, and time-to-goal."
    )

    def _run(self, questionnaire_json: str) -> str:
        try:
            data = json.loads(questionnaire_json)
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Invalid JSON: {e}"})

        renda = float(data.get("renda_mensal", 0) or 0)
        gastos = float(data.get("gastos_mensais", 0) or 0)
        dividas = float(data.get("dividas_totais", 0) or 0)
        taxa_juros_divida = float(data.get("taxa_juros_divida_aa", 0) or 0)
        liquidos = float(data.get("ativos_liquidos", 0) or 0)
        objetivo = data.get("objetivo_financeiro", {}).copy() if isinstance(data.get("objetivo_financeiro"), dict) else {}
        objetivo_valor = float(objetivo.get("valor_objetivo", 0) or 0)
        objetivo_prazo_meses = int(objetivo.get("prazo_meses", 0) or 0)

        capacidade_poupanca = max(renda - gastos, 0)
        debt_to_income = (dividas / renda) if renda > 0 else None
        meses_para_objetivo = None
        if capacidade_poupanca > 0 and objetivo_valor > 0:
            meses_para_objetivo = math.ceil(objetivo_valor / capacidade_poupanca)

        risco = "alto"
        if capacidade_poupanca >= 1000 and (debt_to_income is None or debt_to_income < 0.3):
            risco = "moderado"
        if capacidade_poupanca >= 2500 and (debt_to_income is None or debt_to_income < 0.2):
            risco = "baixo"

        perfil = {
            "ok": True,
            "timestamp": _now_iso(),
            "renda_mensal": renda,
            "gastos_mensais": gastos,
            "dividas_totais": dividas,
            "taxa_juros_divida_aa": taxa_juros_divida,
            "ativos_liquidos": liquidos,
            "capacidade_poupanca": capacidade_poupanca,
            "debt_to_income": debt_to_income,
            "objetivo": {
                "valor_objetivo": objetivo_valor,
                "prazo_meses": objetivo_prazo_meses,
                "meses_estimados_pelo_fluxo": meses_para_objetivo,
            },
            "classificacao_risco": risco,
        }
        return json.dumps(perfil, ensure_ascii=False)

# ----------------------------------------------------------------------------
# 2) BankStatementParserTool (CSV/XLSX/OFX)
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
    "desc": ["descricao", "historico", "description", "detalhe", "memo"],
    "amount": ["valor", "amount", "vl", "montante"],
}

class BankStatementParserArgs(BaseModel):
    file_path: str = Field(description="Path to the uploaded bank statement (csv/xlsx/ofx)")
    llm_enhanced: bool = Field(default=False, description="If True, uses LLM to refine categorization when available")

class BankStatementParserTool(BaseTool):
    name = "BankStatementParserTool"
    description = (
        "Parses a bank statement file (CSV/XLSX/OFX/PDF*) and outputs a JSON with "
        "normalized transactions and category totals. PDF parsing is best-effort (requires pdfplumber)."
    )

    def _run(self, file_path: str, llm_enhanced: bool = False) -> str:
        try:
            ext = pathlib.Path(file_path).suffix.lower()
            if ext == ".csv":
                df = self._read_csv(file_path)
            elif ext in (".xlsx", ".xls"):
                df = self._read_xlsx(file_path)
            elif ext == ".ofx":
                df = self._read_ofx(file_path)
            else:
                return json.dumps({"ok": False, "error": f"Unsupported extension: {ext}"})

            if df is None or df.empty:
                return json.dumps({"ok": False, "error": "Empty or unreadable statement"})

            df = self._normalize_columns(df)
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

    def _read_xlsx(self, path: str):
        if pd is None:
            raise JSONableError("pandas is required for Excel parsing")
        return pd.read_excel(path)

    def _read_ofx(self, path: str):
        if OfxParser is None:
            raise JSONableError("ofxparse is required for .ofx parsing")
        with open(path, 'rb') as f:
            ofx = OfxParser.parse(f)
        rows = []
        for acct in ofx.accounts:
            for txn in acct.statement.transactions:
                rows.append({
                    "data": txn.date.strftime('%Y-%m-%d') if txn.date else None,
                    "descricao": txn.memo or txn.payee or "",
                    "valor": float(txn.amount or 0),
                })
        if pd is None:
            raise JSONableError("pandas is required to normalize ofx rows")
        return pd.DataFrame(rows)

    def _read_pdf(self, path: str):
        if pdfplumber is None or pd is None:
            raise JSONableError("pdfplumber and pandas required for PDF parsing")
        rows = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                # Very naive fallback: try pattern DATE DESC AMOUNT per line
                for line in text.splitlines():
                    m = re.match(r"(\d{2}[/-]\d{2}[/-]\d{2,4})\s+(.*)\s+(-?\d+[\.,]\d{2})$", line.strip())
                    if m:
                        date_raw, desc, amt_raw = m.groups()
                        amt = float(amt_raw.replace(".", "").replace(",", "."))
                        # normalize date to YYYY-MM-DD when possible
                        try:
                            day, month, year = re.split(r"[/-]", date_raw)
                            year = f"20{year}" if len(year) == 2 else year
                            date_norm = f"{year}-{month}-{day}"
                        except Exception:
                            date_norm = None
                        rows.append({"data": date_norm, "descricao": desc, "valor": amt})
        return pd.DataFrame(rows)

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
        # coerce amount
        out["valor"] = (
            out["valor"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False).astype(float)
        )
        return out

    def _categorize(self, descricao: str) -> str:
        text = (descricao or "").lower()
        for pattern, cat in CATEGORY_MAP.items():
            if re.search(pattern, text):
                return cat
        return "Outros"

    def _refine_categories_with_llm(self, df):
        client = LocalLLMClient()
        # Take a sample of unique descriptions to avoid long prompts
        uniq = df["descricao"].dropna().astype(str).str.slice(0, 80).unique().tolist()[:100]
        prompt = (
            "Você é um classificador de gastos. Mapeie cada descrição para UMA categoria entre: "
            "Alimentação, Moradia, Serviços, Transporte, Saúde, Lazer, Renda, Transferências, Educação, Investimentos, Outros.\n"
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

class FinancialAdvisorArgs(BaseModel):
    profile_json: str = Field(description="JSON from UserProfileBuilderTool")
    transactions_json: str = Field(description="JSON from BankStatementParserTool or compatible")
    model: Optional[str] = Field(default=None, description="Local model identifier to use")

class FinancialAdvisorTool(BaseTool):
    name = "FinancialAdvisorTool"
    description = (
        "Generates personalized financial advice using a local LLM, based on the user profile and categorized transactions. "
        "Returns a structured JSON plan with actions by horizon (now/30/90 days, 12 months)."
    )

    SYSTEM_PROMPT = (
        "Você é um planejador financeiro pessoal. Dado um perfil e o histórico de gastos categorizados, "
        "gere recomendações específicas, exequíveis e alinhadas ao objetivo do usuário. "
        "A saída DEVE ser JSON válido com o schema: {\n"
        "  \"resumo\": string,\n"
        "  \"alertas\": [string],\n"
        "  \"plano\": {\n"
        "    \"agora\": [string],\n"
        "    \"30_dias\": [string],\n"
        "    \"90_dias\": [string],\n"
        "    \"12_meses\": [string]\n"
        "  },\n"
        "  \"metas_mensuraveis\": [{\"meta\": string, \"kpi\": string, \"meta_num\": number, \"prazo_meses\": number}]\n"
        "}"
    )

    def _run(self, profile_json: str, transactions_json: str, model: Optional[str] = None) -> str:
        try:
            profile = json.loads(profile_json)
            tx = json.loads(transactions_json)
        except Exception as e:
            return json.dumps({"ok": False, "error": f"Invalid JSON inputs: {e}"})

        # Create compact context (truncate long tx lists)
        tx_list = tx.get("transacoes", []) if isinstance(tx, dict) else tx
        # summarize spend per category for context brevity
        cat_totals = {}
        try:
            for row in tx.get("totais_por_categoria", []):
                cat_totals[row.get("categoria")] = float(row.get("valor", 0))
        except Exception:
            pass

        context = {
            "perfil": profile,
            "resumo_gastos": cat_totals,
            "amostra_transacoes": tx_list[:50],
        }
        prompt = (
            self.SYSTEM_PROMPT + "\n\n" +
            "Dados de entrada (JSON):\n" + json.dumps(context, ensure_ascii=False)
        )

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

class ModelEvaluatorArgs(BaseModel):
    advices_json: str = Field(description="JSON list with entries: {model: str, advice_json: {..}} or {model, text}")
    profile_json: Optional[str] = Field(default=None, description="Profile JSON to provide context to the judge")
    use_llm_judge: bool = Field(default=True, description="If True, use LLM-as-a-judge; else use heuristics only")

class ModelEvaluatorTool(BaseTool):
    name = "ModelEvaluatorTool"
    description = (
        "Compares multiple model advices and scores them using a rubric (clareza, aplicabilidade, consistencia, completude). "
        "Returns scores per model and picks a winner."
    )

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
    name = "ReportGeneratorTool"
    description = (
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
# OPTIONAL: minimal registry that CrewAI can import
# ----------------------------------------------------------------------------

__all__ = [
    "UserProfileBuilderTool",
    "BankStatementParserTool",
    "FinancialAdvisorTool",
    "ModelEvaluatorTool",
    "ReportGeneratorTool",
    "UserProfileBuilderArgs",
    "BankStatementParserArgs",
    "FinancialAdvisorArgs",
    "ModelEvaluatorArgs",
    "ReportGeneratorArgs",
    "LocalLLMClient",
]
