from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain_community.llms import Ollama
import yaml
from typing import Dict, Any
import asyncio

class FinancialAdvisorCrew:
    def __init__(self):
        # Carregar configurações
        with open('./crewai/agents.yaml', 'r', encoding='utf-8') as f:
            self.agents_config = yaml.safe_load(f)
        
        with open('./crewai/tasks.yaml', 'r', encoding='utf-8') as f:
            self.tasks_config = yaml.safe_load(f)
        
        # Configurar LLMs locais
        self.llms = {
            'llama2': Ollama(model="llama2:7b"),
            'mistral': Ollama(model="mistral:7b"),
            'codellama': Ollama(model="codellama:7b")
        }
        
        # Inicializar ferramentas
        self.tools = self._initialize_tools()
        
        # Criar agentes
        self.agents = self._create_agents()
        
        # Criar tarefas
        self.tasks = self._create_tasks()
        
        # Criar crew
        self.crew = Crew(
            agents=list(self.agents.values()),
            tasks=list(self.tasks.values()),
            process=Process.sequential,
            verbose=True
        )
    
    def _create_agents(self) -> Dict[str, Agent]:
        agents = {}
        
        for agent_name, config in self.agents_config.items():
            # Selecionar LLM baseado no agente
            llm = self._select_llm_for_agent(agent_name)
            
            agents[agent_name] = Agent(
                role=config['role'],
                goal=config['goal'],
                backstory=config['backstory'],
                verbose=config.get('verbose', True),
                allow_delegation=config.get('allow_delegation', False),
                tools=[self.tools[tool] for tool in config.get('tools', [])],
                llm=llm
            )
        
        return agents
    
    def _select_llm_for_agent(self, agent_name: str):
        """Seleciona LLM específico para cada agente"""
        llm_mapping = {
            'data_analyst': self.llms['codellama'],      # Melhor para análise de dados
            'financial_advisor': self.llms['llama2'],    # Melhor para conselhos
            'risk_assessor': self.llms['mistral'],       # Melhor para avaliação
            'report_generator': self.llms['codellama'],  # Melhor para estruturação
            'model_evaluator': self.llms['mistral'],     # Melhor para avaliação
            'quality_control': self.llms['llama2']       # Melhor para revisão
        }
        return llm_mapping.get(agent_name, self.llms['llama2'])
    
    def _create_tasks(self) -> Dict[str, Task]:
        tasks = {}
        
        for task_name, config in self.tasks_config.items():
            # Encontrar contexto (dependências)
            context_tasks = []
            if 'context' in config:
                context_tasks = [tasks[ctx] for ctx in config['context'] if ctx in tasks]
            
            tasks[task_name] = Task(
                description=config['description'],
                expected_output=config['expected_output'],
                agent=self.agents[config['agent']],
                context=context_tasks
            )
        
        return tasks
    
    async def process_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa dados do usuário através do sistema multi-agente"""
        
        # Adicionar dados do usuário ao contexto global
        self.crew.context = user_data
        
        # Executar o crew
        result = await asyncio.to_thread(self.crew.kickoff)
        
        return {
            'recommendations': result,
            'agent_outputs': self._extract_agent_outputs(),
            'metrics': self._calculate_system_metrics()
        }
    
    def _extract_agent_outputs(self) -> Dict[str, Any]:
        """Extrai saídas específicas de cada agente"""
        return {
            'data_analysis': self.tasks['analyze_financial_data'].output,
            'financial_advice': self.tasks['generate_financial_advice'].output,
            'risk_assessment': self.tasks['assess_financial_risks'].output,
            'model_comparison': self.tasks['evaluate_llm_responses'].output,
            'visual_reports': self.tasks['generate_visual_reports'].output,
            'quality_report': self.tasks['final_quality_check'].output
        }
    
    def _calculate_system_metrics(self) -> Dict[str, float]:
        """Calcula métricas do sistema multi-agente"""
        return {
            'total_processing_time': 0.0,  # Implementar cronometragem
            'agent_collaboration_score': 0.0,  # Avaliar colaboração
            'output_quality_score': 0.0,  # Avaliar qualidade final
            'user_satisfaction_prediction': 0.0  # Predizer satisfação
        }