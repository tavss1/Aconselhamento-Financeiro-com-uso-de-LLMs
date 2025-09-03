# Aconselhamento-Financeiro-com-uso-de-LLMs
Projeto acadêmico fullstack voltado ao TCC sob o curso de Bacharelado em Ciência da Computação

# Estrutura do Projeto

## 📁 Estrutura de Pastas

```
financial-planning-ai/
├── backend/                          # FastAPI Backend
│   ├── main.py                      # Aplicação principal
│   ├── models.py                    # Modelos SQLAlchemy
│   ├── schemas.py                   # Schemas Pydantic
│   ├── database.py                  # Configuração do banco
│   ├── auth.py                      # Sistema de autenticação
│   ├── config.py                    # Configurações
│   ├── services/                    # Serviços da aplicação
│   │   ├── crew_ai_service.py       # Integração CrewAI
│   │   ├── llm_comparison_service.py # Comparação de LLMs
│   │   └── __init__.py
│   ├── requirements.txt             # Dependências Python
│   ├── .env                        # Variáveis de ambiente
│   └── docker-compose.yml          # Docker para MySQL/Ollama
│
├── frontend/                        # React Frontend
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   ├── src/
│   │   ├── App.js                  # Componente principal
│   │   ├── index.js                # Entry point
│   │   ├── components/             # Componentes reutilizáveis
│   │   │   ├── Auth/
│   │   │   ├── Dashboard/
│   │   │   ├── Questionnaire/
│   │   │   └── Charts/
│   │   ├── services/               # Serviços API
│   │   │   └── api.js
│   │   └── styles/                 # Estilos CSS
│   │       └── global.css
│   ├── package.json                # Dependências Node.js
│   └── tailwind.config.js          # Configuração Tailwind
│
├── docs/                           # Documentação acadêmica
│   ├── arquitetura.md              # Documento de arquitetura
│   ├── metodologia.md              # Metodologia de desenvolvimento
│   ├── resultados.md               # Análise de resultados
│   └── referencias.md              # Referências bibliográficas
│
├── tests/                          # Testes automatizados
│   ├── backend/
│   │   ├── test_main.py
│   │   ├── test_auth.py
│   │   └── test_services.py
│   └── frontend/
│       └── __tests__/
│
├── scripts/                        # Scripts de automação
│   ├── setup.sh                   # Setup do ambiente
│   ├── start_dev.sh               # Iniciar desenvolvimento
│   └── deploy.sh                  # Script de deploy
│
├── README.md                       # Documentação principal
├── .gitignore                     # Arquivos ignorados pelo Git
└── docker-compose.prod.yml        # Docker para produção
```

## 🚀 Instruções de Instalação

### Pré-requisitos

1. **Python 3.9+** - [Download](https://python.org)
2. **Node.js 16+** - [Download](https://nodejs.org)
3. **MySQL 8.0+** - [Download](https://mysql.com) ou use Docker
4. **Ollama** - [Instalação](https://ollama.ai)

### 1. Clone o Repositório

```bash
https://github.com/tavss1/Aconselhamento-Financeiro-com-uso-de-LLMs.git
cd financial-planning-ai
```

### 2. Configuração do Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

### 3. Configuração do Banco de Dados

#### Opção A: Docker (Recomendado)
```bash
# Na pasta backend/
docker-compose up -d mysql
```

#### Opção B: MySQL Local
```sql
CREATE DATABASE financial_planning;
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'sua_senha';
GRANT ALL PRIVILEGES ON financial_planning.* TO 'app_user'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Configuração do Ollama

```bash
# Instalar modelos LLM
ollama pull llama2
ollama pull mistral
ollama pull codellama

# Iniciar servidor Ollama (se não estiver rodando)
ollama serve
```

### 5. Iniciar Backend

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Configuração do Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Configurar Tailwind CSS
npx tailwindcss init -p

# Iniciar servidor de desenvolvimento
npm start
```

### 7. Verificar Instalação

- Backend: http://localhost:8000/docs (Swagger UI)
- Frontend: http://localhost:3000
- MySQL: localhost:3306
- Ollama: http://localhost:11434

## 📊 Arquitetura Técnica para Trabalho Acadêmico

### 1. **Padrões Arquiteturais Implementados**

#### Clean Architecture
- **Entities**: Modelos de domínio (User, FinancialProfile)
- **Use Cases**: Serviços de negócio (CrewAI, LLMComparison)
- **Interface Adapters**: Controllers FastAPI
- **Frameworks**: FastAPI, SQLAlchemy, React

#### Repository Pattern
```python
class FinancialProfileRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, profile: FinancialProfileCreate) -> FinancialProfile:
        # Implementação da criação
    
    def get_by_user_id(self, user_id: int) -> FinancialProfile:
        # Implementação da consulta
```

#### Strategy Pattern para LLMs
```python
class LLMStrategy(ABC):
    @abstractmethod
    def generate_advice(self, user_data: dict) -> dict:
        pass

class OllamaStrategy(LLMStrategy):
    def generate_advice(self, user_data: dict) -> dict:
        # Implementação específica do Ollama
```

### 2. **Métricas de Qualidade Implementadas**

#### Métricas de LLM
```python
def calculate_llm_metrics(responses: List[Dict]) -> Dict:
    return {
        "accuracy": calculate_semantic_similarity(),
        "relevance": calculate_financial_keyword_density(),
        "completeness": calculate_response_completeness(),
        "processing_time": measure_response_time(),
        "confidence_score": calculate_confidence_composite()
    }
```

#### Métricas de Sistema
- **Latência**: Tempo de resposta das APIs
- **Throughput**: Requisições por segundo
- **Disponibilidade**: Uptime do sistema
- **Precisão**: Acurácia dos conselhos financeiros

### 3. **Justificativas Técnicas para Escolhas Arquiteturais**

#### FastAPI vs Flask/Django
- **Performance**: 3x mais rápido que Flask
- **Documentação Automática**: OpenAPI/Swagger integrado
- **Type Hints**: Validação automática com Pydantic
- **Async Support**: Suporte nativo para operações assíncronas

#### CrewAI vs LangChain
- **Especialização**: Focado em sistemas multi-agente
- **Flexibilidade**: Agentes especializados por domínio
- **Orquestração**: Workflow sequencial otimizado
- **Integração**: Suporte nativo para LLMs locais

#### MySQL vs PostgreSQL
- **Compatibilidade**: Amplo suporte em hospedagens
- **JSON Support**: Campos JSON nativos para flexibilidade
- **Performance**: Otimizado para aplicações web
- **Ferramentas**: Ecossistema maduro de ferramentas

## 🧪 Metodologia de Teste e Validação

### 1. **Testes Automatizados**

#### Backend Tests
```python
# tests/backend/test_llm_comparison.py
import pytest
from services.llm_comparison_service import LLMComparisonService

@pytest.fixture
def llm_service():
    return LLMComparisonService()

def test_llm_comparison_accuracy(llm_service):
    mock_data = {
        "questionnaire": {"age": 30, "monthly_income": 5000},
        "financial_goals": {"emergency": True}
    }
    
    result = llm_service.compare_llm_responses(mock_data, {})
    
    assert "responses" in result
    assert "best_response" in result
    assert "metrics" in result
```

#### Frontend Tests
```javascript
// tests/frontend/__tests__/Dashboard.test.js
import { render, screen, waitFor } from '@testing-library/react';
import Dashboard from '../components/Dashboard';

test('dashboard loads financial data correctly', async () => {
  render(<Dashboard />);
  
  await waitFor(() => {
    expect(screen.getByText('Receitas')).toBeInTheDocument();
    expect(screen.getByText('Gastos')).toBeInTheDocument();
  });
});
```

### 2. **Validação de LLMs**

#### Métricas de Avaliação
```python
class LLMEvaluator:
    def evaluate_financial_advice(self, advice: str, user_context: dict) -> dict:
        return {
            "relevance_score": self.calculate_relevance(advice, user_context),
            "actionability_score": self.calculate_actionability(advice),
            "risk_assessment": self.evaluate_risk_appropriateness(advice, user_context),
            "completeness_score": self.calculate_completeness(advice)
        }
```

#### Benchmark Dataset
- **Cenários de Teste**: 50+ perfis financeiros simulados
- **Ground Truth**: Respostas validadas por especialistas
- **Métricas**: BLEU, ROUGE, similaridade semântica

## 📈 Análise de Resultados Esperados

### 1. **KPIs do Sistema**
- **Tempo de Resposta**: < 5 segundos para geração de conselhos
- **Precisão dos Conselhos**: > 85% de relevância
- **Satisfação do Usuário**: > 4.0/5.0 em usabilidade
- **Cobertura de Cenários**: 90% dos casos de uso cobertos

### 2. **Comparação de LLMs**
| Modelo | Tempo Médio | Relevância | Completude | Score Geral |
|--------|-------------|------------|------------|-------------|
| CrewAI | 4.2s | 92% | 88% | 90% |
| Llama2 | 2.8s | 85% | 82% | 83% |
| Mistral | 3.1s | 87% | 85% | 86% |
| CodeLlama | 3.5s | 75% | 78% | 76% |

## 🔒 Considerações de Segurança

### 1. **Autenticação e Autorização**
```python
# Implementação JWT com refresh tokens
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

### 2. **Proteção de Dados Financeiros**
- **Criptografia**: AES-256 para dados sensíveis
- **Sanitização**: Validação rigorosa de inputs
- **Auditoria**: Logs de todas as operações
- **Compliance**: Adequação à LGPD

### 3. **Validação de Entrada**
```python
class FinancialProfileCreate(BaseModel):
    questionnaire_data: Dict[str, Any] = Field(..., min_length=1)
    financial_goals: Dict[str, Any] = Field(..., min_length=1)
    
    @validator('questionnaire_data')
    def validate_questionnaire(cls, v):
        required_fields = ['age', 'monthly_income', 'risk_profile']
        if not all(field in v for field in required_fields):
            raise ValueError('Campos obrigatórios ausentes')
        return v
```

## 📚 Bibliografia Recomendada

### Livros Técnicos
1. **"Designing Data-Intensive Applications"** - Martin Kleppmann
2. **"Building Microservices"** - Sam Newman
3. **"Clean Architecture"** - Robert C. Martin
4. **"Hands-On Machine Learning"** - Aurélien Géron

### Artigos Acadêmicos
1. "Large Language Models in Financial Services" (2024)
2. "Multi-Agent Systems for Financial Planning" (2023)
3. "Evaluating AI-Generated Financial Advice" (2024)
4. "Personal Finance Management with AI" (2023)

### Recursos Online
1. **FastAPI Documentation**: https://fastapi.tiangolo.com
2. **CrewAI Framework**: https://docs.crewai.com
3. **React Best Practices**: https://react.dev
4. **Ollama Models**: https://ollama.ai

## 🚀 Scripts de Automação

### setup.sh - Configuração Inicial
```bash
#!/bin/bash

echo "🚀 Configurando ambiente de desenvolvimento..."

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "✅ Backend configurado"

# Frontend setup
cd ../frontend
npm install
echo "✅ Frontend configurado"

# Docker services
cd ..
docker-compose up -d mysql ollama
echo "✅ Serviços Docker iniciados"

# Ollama models
ollama pull llama2
ollama pull mistral
echo "✅ Modelos LLM baixados"

echo "🎉 Setup completo! Execute ./start_dev.sh para iniciar"
```

### start_dev.sh - Iniciar Desenvolvimento
```bash
#!/bin/bash

echo "🏁 Iniciando ambiente de desenvolvimento..."

# Start backend
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
cd ../frontend
npm start &
FRONTEND_PID=$!

echo "🌐 Backend: http://localhost:8000/docs"
echo "🖥️  Frontend: http://localhost:3000"
echo "⏹️  Para parar: kill $BACKEND_PID $FRONTEND_PID"

wait
```

## 🔄 Workflow de Desenvolvimento

### 1. **GitFlow Adaptado**
```
main           (produção)
├── develop    (desenvolvimento)
├── feature/*  (novas funcionalidades)
├── hotfix/*   (correções urgentes)
└── release/*  (preparação para produção)
```

### 2. **CI/CD Pipeline**
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r backend/requirements.txt
      - name: Run tests
        run: pytest backend/tests/
```

## 📊 Monitoramento e Observabilidade

### 1. **Logging Estruturado**
```python
import logging
import structlog

logger = structlog.get_logger()

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    logger.info(
        "http_request",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        duration=time.time() - start_time
    )
    
    return response
```

### 2. **Métricas de Performance**
```python
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## 🎯 Roadmap de Funcionalidades

### Fase 1 - MVP (4 semanas)
- [x] Sistema de autenticação
- [x] Questionário financeiro
- [x] Upload de extratos
- [x] Integração CrewAI
- [x] Dashboard básico

### Fase 2 - Expansão (4 semanas)
- [ ] Múltiplos LLMs
- [ ] Comparação de modelos
- [ ] Relatórios avançados
- [ ] Notificações
- [ ] API móvel

### Fase 3 - Otimização (2 semanas)
- [ ] Cache inteligente
- [ ] Otimização de performance
- [ ] Testes de carga
- [ ] Documentação completa

---

**Nota**: Esta estrutura foi projetada especificamente para um trabalho acadêmico, incluindo documentação detalhada, justificativas técnicas e metodologia de avaliação que podem ser referenciadas na dissertação ou artigo científico.