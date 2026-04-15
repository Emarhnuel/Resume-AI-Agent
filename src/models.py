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

# ==========================================
# SUBAGENT STRUCTURED OUTPUT SCHEMAS
# ==========================================

class CVReviewResult(BaseModel):
    """Structured output from the CV Reviewer subagent."""
    job_id: str = Field(description="The job ID being reviewed (e.g. 'job_001')")
    match_reasoning: str = Field(description="Why the candidate is or isn't a strong fit for this role")
    strengths_to_highlight: List[str] = Field(description="Skills and experiences from the CV that match the job requirements")
    gaps_to_address: List[str] = Field(description="Missing qualifications or experience gaps relative to the job description")
    reframing_suggestions: List[str] = Field(description="Specific suggestions to reword existing CV bullet points for better alignment")
    github_projects_to_include: List[str] = Field(
        description="GitHub projects worth adding to the CV, with reasons why they are relevant",
        default_factory=list
    )

class ATSScanResult(BaseModel):
    """Structured output from the ATS Scanner subagent."""
    job_id: str = Field(description="The job ID being scanned (e.g. 'job_001')")
    score: int = Field(description="ATS match score out of 100", ge=0, le=100)
    matched_keywords: List[str] = Field(description="Keywords from the job description that already appear in the CV")
    missing_keywords: List[str] = Field(description="Keywords from the job description that are missing from the CV")
    incorporation_suggestions: List[str] = Field(description="Specific suggestions for where and how to add each missing keyword naturally")
