"""Shared mock data for the real-AI test suite.

These are deliberately small so the model calls stay cheap and fast.
"""

from __future__ import annotations

# A short plain-text resume used for CV extraction tests.
MOCK_CV_TEXT = """
Jane Doe
Email: jane.doe@example.com | San Francisco, CA

EDUCATION
State University - BSc in Computer Science (2021-09 to 2025-06), GPA 3.8

SKILLS
Python, FastAPI, SQL, React, Docker, Machine Learning

RELEVANT COURSEWORK
Data Structures, Databases, Operating Systems, Machine Learning

INTERNSHIPS
Software Engineering Intern, Acme Corp (2024-06 to 2024-09)
- Built internal data pipelines in Python and reduced job runtime by 30%.

PROJECTS
Course Scheduler (2024-01 to 2024-05)
- A React + FastAPI web app that recommends optimal class schedules.
""".strip()


# A profile dict shaped like app/schemas/profile.py ProfileInput.
MOCK_PROFILE: dict = {
    "name": "Jane Doe",
    "education": [
        {
            "degree": "BSc",
            "school": "State University",
            "major": "Computer Science",
            "grade": 3.8,
            "start": "2021-09",
            "end": "2025-06",
        }
    ],
    "internships": [
        {
            "title": "Software Engineering Intern",
            "company": "Acme Corp",
            "start": "2024-06",
            "end": "2024-09",
            "description": "Built data pipelines in Python.",
        }
    ],
    "projects": [
        {
            "title": "Course Scheduler",
            "start": "2024-01",
            "end": "2024-05",
            "description": "React + FastAPI scheduling web app.",
        }
    ],
    "skills": ["Python", "FastAPI", "SQL", "React", "Docker"],
    "coursework": ["Data Structures", "Databases", "Machine Learning"],
}


# A job dict shaped like the entries in app/data/jobs.py.
MOCK_JOB: dict = {
    "id": "j_mock",
    "title": "Backend Engineer (New Grad)",
    "company": "Globex",
    "skills": ["Python", "FastAPI", "SQL", "Docker", "Kubernetes"],
    "description": (
        "We are hiring a new-grad backend engineer to build and scale our API "
        "platform. You will work with Python, FastAPI, PostgreSQL and Docker."
    ),
}


# A short interview transcript for scoring tests.
MOCK_TRANSCRIPT = """
coach: Tell me about a project where you used Python.
user: I built a course scheduler with FastAPI and React. I designed the REST API,
      modeled the data in PostgreSQL, and wrote a small optimizer that suggests
      conflict-free schedules. The hardest part was handling overlapping time slots.
coach: How did you validate that the optimizer worked?
user: I wrote unit tests with synthetic timetables and compared the output against
      hand-computed expected schedules, then added a few real student datasets.
""".strip()


# A single spoken "answer" used to round-trip TTS -> STT in voice tests.
MOCK_SPOKEN_ANSWER = (
    "I led the backend for a course scheduling app built with FastAPI and "
    "PostgreSQL, and I focused on reliability and clear API design."
)
