import os

from crewai import LLM
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import (
	ScrapeWebsiteTool
)





@CrewBase
class DefenseNewsKoreanDailyDigestCrew:
    """DefenseNewsKoreanDailyDigest crew"""

    
    @agent
    def defense_news_web_scraper(self) -> Agent:
        
        return Agent(
            config=self.agents_config["defense_news_web_scraper"],
            
            
            tools=[				ScrapeWebsiteTool()],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            
            max_execution_time=None,
            llm=LLM(
                model="openai/gpt-4o-mini",
                temperature=0.7,
            ),
            
        )
    
    @agent
    def defense_news_analyst(self) -> Agent:
        
        return Agent(
            config=self.agents_config["defense_news_analyst"],
            
            
            tools=[],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            
            max_execution_time=None,
            llm=LLM(
                model="openai/gpt-4o-mini",
                temperature=0.7,
            ),
            
        )
    
    @agent
    def korean_defense_content_writer(self) -> Agent:
        
        return Agent(
            config=self.agents_config["korean_defense_content_writer"],
            
            
            tools=[],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            
            max_execution_time=None,
            llm=LLM(
                model="openai/gpt-4.1",
                temperature=0.7,
            ),
            
        )
    

    
    @task
    def scrape_defense_news_articles(self) -> Task:
        return Task(
            config=self.tasks_config["scrape_defense_news_articles"],
            markdown=False,
            
            
        )
    
    @task
    def analyze_and_prioritize_top_7_articles(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_and_prioritize_top_7_articles"],
            markdown=False,
            
            
        )
    
    @task
    def rewrite_articles_in_korean(self) -> Task:
        return Task(
            config=self.tasks_config["rewrite_articles_in_korean"],
            markdown=False,
            
            
        )
    

    @crew
    def crew(self) -> Crew:
        """Creates the DefenseNewsKoreanDailyDigest crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            chat_llm=LLM(model="openai/gpt-4o-mini"),
        )


