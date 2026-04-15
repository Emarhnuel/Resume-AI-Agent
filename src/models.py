from pydantic import BaseModel, Field
from typing import Optional, List

# ==========================================
# BROWSER USE EXTRACTION SCHEMAS
# ==========================================

class Job(BaseModel):
    title: str = Field(description="The job title")
    company_name: str = Field(description="Name of the company hiring")
    job_url: str = Field(description="The direct URL to the actual job posting")
    summary_of_requirements: str = Field(description="A brief 2-3 sentence summary of the key requirements (skills, tech stack)")
    estimated_salary: Optional[str] = Field(description="The estimated salary or range, if visible", default=None)

class JobList(BaseModel):
    jobs: List[Job] = Field(description="List of extracted jobs matching the criteria")

# ==========================================
# SUPERVISOR INPUT SCHEMA (USER FORM)
# ==========================================

class JobApplicationForm(BaseModel):
    """The initial form data filled by the user to kick off the AI CV Agent"""
    full_name: str
    current_cv_text: str
    job_location: str
    github_portfolio_url: Optional[str] = None
    max_jobs_to_target: int = 3
    minimum_salary: Optional[str] = None
    email_address: str
    preferred_job_board: str = "linkedin"
    target_job_title: str
    years_of_experience: Optional[str] = None
    cover_letter_tone: Optional[str] = "Professional"
    additional_requirements: Optional[str] = None
