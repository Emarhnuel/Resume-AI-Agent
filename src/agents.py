"""
Agent configurations for AI CV Agent.

This module defines the supervisor agent and sub-agents for job applications,
CV reviewing, ATS scanning, and application drafting using the Deep Agents framework.
"""

import os
from pathlib import Path
from langchain_aws import ChatBedrockConverse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend, CompositeBackend, StoreBackend
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure LangSmith tracing (reads from env vars automatically)
# Set LANGSMITH_TRACING=true and LANGSMITH_API_KEY in .env to enable
if os.getenv("LANGSMITH_TRACING", "").lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if os.getenv("LANGSMITH_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT")
    print(f"[INFO] LangSmith tracing enabled for project: {os.getenv('LANGSMITH_PROJECT', 'default')}")

# Assuming these exist in src.tools and src.prompts
from src.tools import (
    search_jobs_tool,
    apply_to_job_tool,
    save_cv_to_pdf_tool,
    tavily_search_tool
)
from src.prompts import (
    JOB_SEARCHER_SYSTEM_PROMPT,
    CV_REVIEWER_SYSTEM_PROMPT,
    ATS_SCANNER_SYSTEM_PROMPT,
    APPLICATION_WRITER_SYSTEM_PROMPT,
    JOB_APPLIER_SYSTEM_PROMPT,
    SUPERVISOR_SYSTEM_PROMPT
)

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

# Main models based on AWS Bedrock limits/preferences
model_primary = ChatBedrockConverse( 
    model_id="us.amazon.nova-pro-v1:0",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    temperature=0.0,
    max_tokens=40960,
)

model_secondary = ChatBedrockConverse( 
    model_id="us.amazon.nova-lite-v1:0",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    temperature=0.0,
    max_tokens=10000,
)

model_claude = ChatBedrockConverse( 
    model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name=os.getenv("AWS_REGION", "us-east-1"), 
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    temperature=0.0,
    max_tokens=10000,
)

# =============================================================================
# BACKEND CONFIGURATION
# =============================================================================

checkpointer = MemorySaver()

# Agent data directory - all sub-agent files land here
AGENT_DATA_DIR = Path("agent_data")
AGENT_DATA_DIR.mkdir(exist_ok=True)

_fs_backend = FilesystemBackend(root_dir=str(AGENT_DATA_DIR), virtual_mode=True)

def make_backend(runtime):
    return CompositeBackend(
        default=_fs_backend,
        routes={
            "/memories/": StoreBackend(runtime),
        }
    )

# =============================================================================
# AGENT FACTORY
# =============================================================================

# 1. Job Searcher Sub-Agent
job_searcher_agent = {
    "name": "job_searcher",
    "description": (
        "Searches the web for job openings based on the user's criteria (e.g. Remote, AI Engineering). "
        "Returns a structured list of relevant job URLs and summaries."
    ),
    "system_prompt": JOB_SEARCHER_SYSTEM_PROMPT,
    "tools": [search_jobs_tool],
    "model": model_secondary,
    "middleware": [
        ToolCallLimitMiddleware(tool_name="search_jobs_tool", run_limit=3, exit_behavior="end"),
    ],
}

# 2. CV Reviewer Sub-Agent
cv_reviewer_agent = {
    "name": "cv_reviewer",
    "description": (
        "Analyzes the target job description against the user's original CV. "
        "Identifies gaps, strengths, and areas to highlight."
    ),
    "system_prompt": CV_REVIEWER_SYSTEM_PROMPT,
    "tools": [tavily_search_tool],
    "model": model_claude,
    "middleware": [
        ModelCallLimitMiddleware(run_limit=5, exit_behavior="end"),
        ToolCallLimitMiddleware(tool_name="tavily_search", run_limit=3, exit_behavior="end"),
    ],
}

# 3. ATS Scanner Sub-Agent
ats_scanner_agent = {
    "name": "ats_scanner",
    "description": (
        "Extracts ATS keywords from the job listing and scores "
        "the CV against those keywords. Suggests specific keyword additions."
    ),
    "system_prompt": ATS_SCANNER_SYSTEM_PROMPT,
    "tools": [],
    "model": model_claude,
    "middleware": [
        ModelCallLimitMiddleware(run_limit=5, exit_behavior="end"),
    ],
}

# 4. Application Writer Sub-Agent
application_writer_agent = {
    "name": "application_writer",
    "description": (
        "Drafts a tailored cover letter and customizes the CV bullet points "
        "based on the job description and feedback from the CV Reviewer and ATS Scanner. "
        "Generates a final PDF."
    ),
    "system_prompt": APPLICATION_WRITER_SYSTEM_PROMPT,
    "tools": [save_cv_to_pdf_tool],
    "skills": ["skills/humanizer/"],
    "model": model_primary,
    "middleware": [
        ModelCallLimitMiddleware(run_limit=10, exit_behavior="end"),
        ToolCallLimitMiddleware(tool_name="save_cv_to_pdf_tool", run_limit=5, exit_behavior="end"),
    ],
}

# 5. Job Applier Sub-Agent
job_applier_agent = {
    "name": "job_applier",
    "description": (
        "Physically submits job applications on job platforms. "
        "Takes the tailored CV and cover letter and fills out + submits the application form via Browser Use."
    ),
    "system_prompt": JOB_APPLIER_SYSTEM_PROMPT,
    "tools": [apply_to_job_tool],
    "model": model_secondary,
    "middleware": [
        ToolCallLimitMiddleware(tool_name="apply_to_job_tool", run_limit=5, exit_behavior="end"),
    ],
}

# Create the supervisor agent
supervisor = create_deep_agent(
    name="cv_application_orchestrator",
    model=model_primary,
    system_prompt=SUPERVISOR_SYSTEM_PROMPT,
    subagents=[
        job_searcher_agent,
        cv_reviewer_agent,
        ats_scanner_agent,
        application_writer_agent,
        job_applier_agent
    ],
    tools=[],
    middleware=[
        ModelCallLimitMiddleware(run_limit=30, exit_behavior="end"),
    ],
    checkpointer=checkpointer,
    backend=make_backend,
    store=InMemoryStore(),
)

print("[INFO] Supervisor agent created successfully")
