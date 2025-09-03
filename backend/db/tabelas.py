from pydantic import BaseModel, EmailStr
from typing import Dict, List, Any, Optional
from datetime import datetime

class usuarioCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class usuarioResponse(BaseModel):
    id: int
    name: str
    email: str
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class FinancialProfileCreate(BaseModel):
    questionnaire_data: Dict[str, Any]
    financial_goals: Dict[str, Any]

class LLMResponse(BaseModel):
    llm_name: str
    advice: str
    confidence_score: float
    processing_time: float

class LLMComparisonResponse(BaseModel):
    responses: List[LLMResponse]
    best_response: LLMResponse
    metrics: Dict[str, Any]
    
class FinancialSummary(BaseModel):
    total_income: float
    total_expenses: float
    balance: float

class DashboardData(BaseModel):
    financial_summary: FinancialSummary
    expense_categories: Dict[str, float]
    recent_advice: List[Dict[str, Any]]