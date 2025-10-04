from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew

from .tools import (
    DatabaseFinancialProfileTool,
    FinancialAdvisorTool, 
    BankStatementParserTool, 
    DashboardDataCompilerTool, 
    UserProfileBuilderTool, 
    ModelEvaluatorTool
)

# Configuração do LLM - usando import mais compatível
try:
    from langchain_ollama import ChatOllama
    llm = ChatOllama(model="gemma3")
except ImportError:
    # Fallback para versão antiga
    from langchain.llms import Ollama
    llm = Ollama(model="gemma3")

@CrewBase
class FinancialAdvisorCrew():
    """Crew para aconselhamento financeiro."""

    agents_config = 'agents.yaml'
    tasks_config = 'tasks.yaml'

    @agent
    def data_extractor(self) -> Agent:
        """Agente para extrair dados financeiros do extrato bancário."""
        return Agent(
            config=self.agents_config['data_extractor'],
            verbose=True,
            llm=llm, 
            tools=[
                DatabaseFinancialProfileTool(),
                BankStatementParserTool()]
        )
    
    @task
    def extractor_financial_data(self) -> Task:
        """Tarefa para extrair dados financeiros do extrato bancário e categorizar as transações."""
        return Task(
            config = self.tasks_config['extractor_financial_data'],
            agent=self.data_extractor()
        )

    @agent
    def data_analyst(self) -> Agent:
        """Agente para analisar e compilar os dados financeiros extraídos."""
        return Agent(
            config = self.agents_config['data_analyst'],
            verbose=True,
            llm=llm, 
            tools=[
                DatabaseFinancialProfileTool(),
                UserProfileBuilderTool()
            ]
        )
    
    @task
    def analyze_financial_data(self) -> Task:
        """Tarefa para compilar os dados financeiros extraídos."""
        return Task(
            config = self.tasks_config['analyze_financial_data'],
            agent=self.data_analyst()
        )

    @agent
    def financial_advisor(self) -> Agent:
        """Agente para gerar conselhos financeiros personalizados."""
        return Agent(
            config = self.agents_config['financial_advisor'],
            verbose=True,
            llm=llm, 
            tools=[FinancialAdvisorTool()]
        )
    
    @task
    def generate_financial_advice(self) -> Task:
        """Tarefa para gerar conselhos financeiros personalizados."""
        return Task(
            agent=self.financial_advisor(),
            config=self.tasks_config['generate_financial_advice']
        )

    @agent 
    def dashboard_data_compiler(self) -> Agent:
        """Agente para compilar e estruturar os dados para o dashboard."""
        return Agent(
            config = self.agents_config['dashboard_data_compiler'],
            verbose=True,
            llm=llm, 
            tools=[DashboardDataCompilerTool()]
        )
    
    @task
    def compile_dashboard_data(self) -> Task:
        """Tarefa para compilar e estruturar os dados para o dashboard."""
        return Task(
            agent=self.dashboard_data_compiler(),
            config=self.tasks_config['compile_dashboard_data']
        )
    
    @agent
    def model_evaluator(self) -> Agent:
        """Agente para avaliar e comparar modelos LLM."""
        return Agent(
            config = self.agents_config['model_evaluator'],
            verbose=True,
            llm=llm, 
            tools=[ModelEvaluatorTool()]
        )
    
    @task
    def evaluate_llm_responses(self) -> Task:
        """Tarefa para avaliar e comparar modelos LLM."""
        return Task(
            agent=self.model_evaluator(),
            config=self.tasks_config['evaluate_llm_responses']
        )
    
    @crew
    def crew(self) -> Crew:
        '''Crew principal para orquestrar o fluxo de funcionamento.'''
        return Crew(
            agents=[
                self.data_extractor(),
                self.data_analyst(),
                self.financial_advisor(),
                self.dashboard_data_compiler(),
                self.model_evaluator()
            ],
            tasks=[
                self.extractor_financial_data(),
                self.analyze_financial_data(),
                self.generate_financial_advice(),
                self.compile_dashboard_data(),
                self.evaluate_llm_responses()
            ],
            verbose=True
        )