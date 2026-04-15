import os
import asyncio
import json
from langchain_core.tools import tool
from browser_use_sdk.v3 import AsyncBrowserUse
from src.models import JobList

# We inject the exact profile that we authenticated with login.py
# This bypasses LinkedIn/Glassdoor's bot detection because they see the exact same 
# browser cookies, canvas fingerprints, and WebGL signatures as your human login.
PROFILE_ID = "1c9c2845-8083-4d15-9c66-9f73f09affe2" 

@tool
async def search_jobs_tool(
    target_job_title: str, 
    job_location: str, 
    max_jobs_to_target: int = 3,
    preferred_job_board: str = "linkedin",
    minimum_salary: str = "",
    years_of_experience: str = "",
    additional_requirements: str = ""
) -> str:
    """
    Searches for job openings on platforms using Browser Use Cloud with deep stealth.
    
    Args:
        target_job_title: The role to search for (e.g., 'Senior AI Engineer').
        job_location: The location to search for (e.g., 'Remote', 'Lagos', 'London').
        max_jobs_to_target: Maximum number of job listings to extract.
        preferred_job_board: Job board to search (e.g., 'linkedin').
        minimum_salary: Optional salary filter (e.g., '$100k').
        years_of_experience: Optional filter (e.g., '5+ years' or 'Entry-level').
        additional_requirements: Optional (e.g., 'Visa sponsorship', '4-day week').
    """
    print(f"\n[Browser Use] Starting highly-stealth job search on {preferred_job_board} for {target_job_title}...")
    
    client = AsyncBrowserUse(api_key=os.getenv("BROWSER_USE_API_KEY"))
    
    # We create a session explicitly loading the Human profile for stealth
    session = await client.sessions.create(profile_id=PROFILE_ID)
    
    # Following Prompting Guide: Explicit, numbered step-by-step instructions
    task_prompt = f"""
1. Go to {preferred_job_board}.com.
2. Use the search bar to find '{target_job_title}' jobs in '{job_location}'.
3. Scroll down the page multiple times to load more job listings.
4. If a popup or login screen blocks you, look for a 'close' or 'X' button to dismiss it.
5. NEVER click on the 'Apply' button during extraction.
6. Extract the top {max_jobs_to_target} most relevant job listings.
"""
    
    # Dynamically add the optional fields if they are provided as extra steps
    current_step = 7
    if minimum_salary:
        task_prompt += f"{current_step}. Filter or look for jobs mentioning a minimum salary around {minimum_salary}.\n"
        current_step += 1
    if years_of_experience:
        task_prompt += f"{current_step}. Prioritize jobs matching {years_of_experience} experience.\n"
        current_step += 1
    if additional_requirements:
        task_prompt += f"{current_step}. Keep in mind these additional requirements: {additional_requirements}.\n"
        
    try:
        # We explicitly enforce the JobList Pydantic schema!
        result = await client.run(
            task=task_prompt,
            session_id=session.id,
            output_schema=JobList
        )
        
        # If output matches the schema, we return the strict JSON dump back to our CV AI
        if hasattr(result, "output") and result.output:
            return result.output.model_dump_json()
        return str(result)
        
    except Exception as e:
        return f"Browser Agent failed to extract jobs: {str(e)}"
    finally:
        # Gracefully shut down the remote browser
        await client.sessions.stop(session.id)

# =================================================================
# JOB APPLICATION TOOL (Browser Use - Auto Submit)
# =================================================================

@tool
async def apply_to_job_tool(
    job_url: str,
    full_name: str,
    email_address: str,
    cv_text: str,
    cover_letter_text: str,
    job_platform: str = "linkedin"
) -> str:
    """
    Physically applies to a job by navigating to the job URL and submitting the application
    using Browser Use Cloud with deep stealth.
    
    Args:
        job_url: The direct URL to the job posting.
        full_name: The applicant's full name.
        email_address: The applicant's email address.
        cv_text: The full tailored CV text to paste or upload.
        cover_letter_text: The full cover letter text to paste.
        job_platform: The platform (linkedin, glassdoor, indeed) to adjust behavior.
    """
    print(f"\n[Browser Use] Applying to job at {job_url}...")
    
    client = AsyncBrowserUse(api_key=os.getenv("BROWSER_USE_API_KEY"))
    session = await client.sessions.create(profile_id=PROFILE_ID)
    
    task_prompt = f"""
1. Go to this exact job URL: {job_url}
2. Look for an 'Apply', 'Easy Apply', or 'Apply Now' button and click it.
3. If a popup or modal form appears, fill in the following fields:
   - Full Name: {full_name}
   - Email: {email_address}
4. If there is a cover letter text box, paste this cover letter:
   ---
   {cover_letter_text}
   ---
5. If there is a field to paste or type a resume/CV, paste this CV:
   ---
   {cv_text}
   ---
6. If there is a file upload button for a resume/CV, skip the upload (we will handle PDF uploads separately).
7. If there are additional required fields (phone number, location, etc.), fill them with reasonable defaults or leave optional fields blank.
8. Review the form one final time, then click 'Submit', 'Send Application', or the equivalent submit button.
9. If the submission succeeds, confirm by reading the success message on screen.
10. If a CAPTCHA or verification appears, attempt to solve it. If it cannot be solved, report the failure.
11. IMPORTANT: Do NOT apply twice. Submit only once.
"""

    try:
        result = await client.run(
            task=task_prompt,
            session_id=session.id
        )
        
        final = str(result.final_answer) if hasattr(result, "final_answer") else str(result)
        return f"Application submission result for {job_url}: {final}"
        
    except Exception as e:
        return f"Application submission FAILED for {job_url}: {str(e)}"
    finally:
        await client.sessions.stop(session.id)

# =================================================================
# GITHUB SEARCH / WEB CRAWLER TOOL
# =================================================================

from langchain_tavily import TavilySearch

# We use Tavily Search to act as a crawler/search engine to look up the provided GitHub repo URLs.
tavily_search_tool = TavilySearch(
    max_results=3,
    topic="general"
)

# =================================================================
# CV TO PDF TOOL (ReportLab)
# =================================================================

import re
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
)

# Color palette for the CV
_PRIMARY = HexColor("#1a1a2e")     # Deep navy for headings
_ACCENT = HexColor("#0f3460")      # Accent blue for lines
_TEXT = HexColor("#2d2d2d")         # Dark grey for body text
_LIGHT = HexColor("#666666")       # Lighter grey for secondary info

def _build_cv_styles():
    """Build a professional set of paragraph styles for the CV."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="CVName",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=_PRIMARY,
        spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="CVContact",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=_LIGHT,
        spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        name="CVSectionHeading",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=_PRIMARY,
        spaceBefore=6 * mm,
        spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="CVBody",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=_TEXT,
        spaceAfter=1.5 * mm,
    ))
    styles.add(ParagraphStyle(
        name="CVBullet",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=_TEXT,
        leftIndent=10 * mm,
        spaceAfter=1 * mm,
    ))
    return styles


def _markdown_inline(text: str) -> str:
    """Convert basic markdown inline formatting to ReportLab XML tags."""
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    # Italic: *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<i>\1</i>', text)
    # Links: [text](url) -> just the text
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    return text


def _parse_cv_markdown(cv_text: str, styles) -> list:
    """
    Parse a markdown-formatted CV into ReportLab flowables.
    
    Supports:
      - # Heading 1 (treated as the name)
      - ## Heading 2 (section headings like "Experience", "Education")
      - Lines starting with - or * (bullet points)
      - **bold** and *italic* inline formatting
      - Horizontal rules (--- or ***)
      - Regular paragraphs
    """
    flowables = []
    lines = cv_text.strip().split("\n")
    i = 0
    name_set = False

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^(-{3,}|\*{3,}|_{3,})$', line):
            flowables.append(Spacer(1, 2 * mm))
            flowables.append(HRFlowable(
                width="100%", thickness=0.5, color=_ACCENT,
                spaceBefore=1 * mm, spaceAfter=3 * mm
            ))
            i += 1
            continue

        # H1: Name / Title (first one only)
        if line.startswith("# ") and not line.startswith("## "):
            heading_text = _markdown_inline(line[2:].strip())
            if not name_set:
                flowables.append(Paragraph(heading_text, styles["CVName"]))
                name_set = True
            else:
                flowables.append(Paragraph(heading_text, styles["CVSectionHeading"]))
            i += 1
            continue

        # H2: Section heading
        if line.startswith("## "):
            heading_text = _markdown_inline(line[3:].strip())
            flowables.append(Spacer(1, 2 * mm))
            flowables.append(HRFlowable(
                width="100%", thickness=0.75, color=_ACCENT,
                spaceBefore=1 * mm, spaceAfter=1 * mm
            ))
            flowables.append(Paragraph(heading_text.upper(), styles["CVSectionHeading"]))
            i += 1
            continue

        # H3: Sub-heading (job title, school, etc.)
        if line.startswith("### "):
            heading_text = _markdown_inline(line[4:].strip())
            flowables.append(Paragraph(f"<b>{heading_text}</b>", styles["CVBody"]))
            i += 1
            continue

        # Bullet point
        if line.startswith(("- ", "* ", "• ")):
            bullet_text = _markdown_inline(line[2:].strip())
            flowables.append(Paragraph(f"•  {bullet_text}", styles["CVBullet"]))
            i += 1
            continue

        # Contact line (if it contains | separators, treat as centered contact info)
        if "|" in line and not name_set:
            contact_text = _markdown_inline(line)
            flowables.append(Paragraph(contact_text, styles["CVContact"]))
            i += 1
            continue

        # Regular paragraph
        para_text = _markdown_inline(line)
        flowables.append(Paragraph(para_text, styles["CVBody"]))
        i += 1

    return flowables


@tool
def save_cv_to_pdf_tool(cv_markdown: str, output_filename: str = "cv_output.pdf") -> str:
    """
    Converts a markdown-formatted CV into a professionally styled PDF file.
    
    The tool parses headings (# Name, ## Section), bullet points (- item),
    bold (**text**), italic (*text*), and horizontal rules (---), then
    renders them as a clean, ATS-friendly PDF using ReportLab.
    
    Args:
        cv_markdown: The full CV content in markdown format.
        output_filename: The output PDF filename (e.g., 'job_001_cv.pdf'). 
                         Will be saved inside the agent_data/applications/ directory.
    
    Returns:
        The absolute path to the generated PDF file.
    """
    # Ensure the output directory exists
    output_dir = Path("agent_data") / "applications"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize the filename
    if not output_filename.endswith(".pdf"):
        output_filename += ".pdf"
    output_path = output_dir / output_filename

    styles = _build_cv_styles()
    flowables = _parse_cv_markdown(cv_markdown, styles)

    # Build the PDF
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title="CV",
        author="AI CV Agent",
    )
    doc.build(flowables)

    abs_path = str(output_path.resolve())
    print(f"[PDF] CV saved to: {abs_path}")
    return f"PDF generated successfully at: {abs_path}"

