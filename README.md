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
