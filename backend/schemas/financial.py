from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class FinancialGoalDetails(BaseModel):
    target_amount: Optional[str] = None
    time_frame: Optional[str] = None

class ObjectiveData(BaseModel):
    financial_goal: str
    financial_goal_details: FinancialGoalDetails

class Dependent(BaseModel):
    type: str
    quantity: int

class QuestionnaireData(BaseModel):
    age: str
    monthly_income: str
    risk_profile: str
    transportation_methods: str
    dependents: List[Dependent]  # Lista de dependentes
    mensalidade_faculdade: str  # "sim" ou "nao"
    valor_mensalidade: Optional[str] = None  # Valor da mensalidade (se mensalidade_faculdade for "sim")


class FinancialProfileCreate(BaseModel):
    questionnaire_data: QuestionnaireData
    objective_data: ObjectiveData

class FinancialProfileResponse(BaseModel):
    id: int
    usuario_id: int
    questionnaire_data: Dict[str, Any]  # JSON do questionário
    objetivo: Optional[Dict[str, Any]] = None  # JSON do objetivo
    extrato: Optional[Dict[str, Any]] = None
    data_criado: str
    
    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    message: str
    file_info: Dict[str, Any]
    profile_updated: bool = False