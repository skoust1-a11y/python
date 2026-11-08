import os
import asyncio
from typing import Literal
from crewai.flow.flow import Flow, start, listen, router
from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
from models import ResumeFlowState

load_dotenv()

def _build_azure_llm() -> "LLM":
    """
    Build and return a configured Azure OpenAI LLM instance.

    TODOs:
    1. Read required Azure OpenAI configuration from environment variables.
    2. Validate that required values are present and raise ValueError if any are missing.
    3. Construct and return a CrewAI LLM configured for the Azure OpenAI provider.
    """
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    if not api_key:
        raise ValueError("AZURE_OPENAI_API_KEY environment variable is not set")
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is not set")
    if not deployment_name:
        raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME environment variable is not set")
    
    return LLM(
        provider="azure_openai",
        model=deployment_name,
        api_key=api_key,
        base_url=endpoint
    )


class ResumeScreeningFlow(Flow[ResumeFlowState]):

    def __init__(self):
        super().__init__()
        # TODO: Initialize LLM
        # Hint: usage self.llm = _build_azure_llm()
        self.llm = _build_azure_llm()

    @start()
    def classify_resume(self):
        """
        Entry point: Classify the role based on resume content.
        
        TODOs:
        1. Access resume_text from self.state.
        2. Analyze keywords to determine the role (Data Analyst, HR Manager, Sales Executive, or General).
        3. Update self.state.classified_role.
        4. Return the track name for routing.
        """
        # Keywords are matched against a lowercased copy of the resume so that
        # casing in the source text (e.g. "SQL" vs "sql") doesn't cause misses.
        resume_txt = self.state.resume_text.lower()
        data_analyst_keywords = {
            'sql', 'python', 'tableau', 'power bi', 'excel', 'analytics',
            'data analysis', 'database', 'etl', 'pandas', 'numpy', 'r language',
            'business intelligence', 'lookalike', 'dashboarding', 'data warehouse'
        }

        hr_keywords = {
            'recruitment', 'hr', 'human resources', 'payroll', 'hris',
            'employee relations', 'talent acquisition', 'onboarding',
            'benefits administration', 'compensation', 'hr manager', 'recruiter'
        }

        sales_keywords = {
            'sales', 'crm', 'salesforce', 'revenue', 'pipeline', 'account manager',
            'sales executive', 'business development', 'client management',
            'lead generation', 'quota', 'territory', 'closing deals'
        }
        data_matches = sum(1 for kw in data_analyst_keywords if kw in resume_txt)
        hr_matches = sum(1 for kw in hr_keywords if kw in resume_txt)
        sales_matches = sum(1 for kw in sales_keywords if kw in resume_txt)

        # Classify by whichever category has the most keyword hits; fall back
        # to 'general' only when none of the categories matched anything.
        if data_matches == 0 and hr_matches == 0 and sales_matches == 0:
            classified_role = 'general'
        elif data_matches >= hr_matches and data_matches >= sales_matches:
            classified_role = 'data_analyst'
        elif sales_matches >= hr_matches:
            classified_role = 'sales'
        else:
            classified_role = 'hr'

        self.state.classified_role = classified_role

        # Return the track name for routing.
        return classified_role

    @router(classify_resume)
    def route_application(self, track: str)->Literal['sales_track','data_analyst_track','general_track','hr_track']:
        """
        Route to appropriate evaluator crew.
        
        TODOs:
        1. Validate the track.
        2. Return the track to trigger the correct @listen method.
        """
        # TODO: Return the track
        print(f"Routing {track} claim to specialist crew...")
        return f"{track}_track"

    def _run_evaluator(self, role_name: str, goal: str, criteria: str):
        """
        Helper to run a specialized evaluator crew.
        """
        # Step 1 - Create Agent
        agent = Agent(
            role=role_name,
            goal=goal,
            backstory=f"You are an experienced {role_name} responsible for evaluating "
                      f"job candidates for {self.state.applying_for or 'the role'}.",
            llm=self.llm,
        )

        # Step 2 - Create Task
        # Include the actual resume content so the agent has something to evaluate.
        task = Task(
            agent=agent,
            description=(
                f"Evaluate the following resume for candidate '{self.state.candidate_name}' "
                f"against these criteria: {criteria}.\n\nResume:\n{self.state.resume_text}"
            ),
            expected_output="Only detailed text justification (no JSON) against the criteria.",
        )

        # Step 3 - Run Crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=True
        )
        result = crew.kickoff()

        # Step 4 - Update State
        self.state.feedback = result.raw
        self.state.evaluator = role_name

    @listen("data_analyst_track")
    def run_data_analyst_crew(self):
        """
        Listener for Data Analyst track.
        """
        # TODO: Call _run_evaluator
        # Hint: Role='Lead Data Scientist', Criteria='SQL, Python, Tableau...'
        self._run_evaluator(
            role_name='Lead Data Scientist',
            criteria='SQL, Python, Tableau',
            goal='You are a Senior Data Analyst working on varos data analyst work'
        )

    @listen("hr_track")
    def run_hr_crew(self):
        """
        Listener for HR track.
        """
        # TODO: Call _run_evaluator
        # Hint: Role='HR Director', Criteria='Recruitment, Compliance...'
        self._run_evaluator(
                role_name='HR Director',
               criteria='Recruitment, Compliance',
            goal='You are a Senior HR hiring candidates'
                )

    @listen("sales_track")
    def run_sales_crew(self):
        """
        Listener for Sales track.
        """
        # TODO: Call _run_evaluator
        # Hint: Role='VP of Sales', Criteria='Quota, CRM...'
        self._run_evaluator(
                role_name='VP of Sales',
               criteria='Quota, CRM',
            goal='You are a Sales Executive'
                )
    
    @listen("general_track")
    def run_general_crew(self):
         """
         Listener for General track.
         """
         # TODO: Call _run_evaluator
         # Hint: Role='General Recruiter', Criteria='Employability...'
         self._run_evaluator(
                role_name='General Recruiter',
               criteria='Employability',
            goal='You are a GENERAL Executive')

async def process_resume(candidate_name: str, resume_text: str, applying_for: str):
    """
    Process a resume through the multi-crew flow.
    """
    try:
        # Validate request
        if not candidate_name or not resume_text or not applying_for:
            raise ValueError("Resume details should not be empty")

        # Step 1 - Initialize the flow
        flow = ResumeScreeningFlow()

        # Step 2 & 3 - Kick off the flow with the initial state, run it in a
        # thread executor since Flow.kickoff() is a blocking/sync call.
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: flow.kickoff(inputs={
                "candidate_name": candidate_name,
                "resume_text": resume_text,
                "applying_for": applying_for,
            })
        )

        # Step 4 - Return the flow instance (holds final state) and the result
        return flow, result

    except ValueError as e:
        raise ValueError(f'The Error is: {e}')
    except Exception as e:
        raise Exception(f'The Error is: {e}')
