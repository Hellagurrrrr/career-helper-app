from __future__ import annotations

from typing import Any

# Public goal catalog (api-design 4.1 CatalogGoal). Mock seed data.
GOAL_CATALOG: list[dict[str, Any]] = [
    {
        "id": "1",
        "title": "Full-Stack Developer",
        "description": "Build end-to-end web applications across frontend and backend.",
        "color": "#6366f1",
        "matchSignals": ["React", "Node.js", "SQL", "Computer Science"],
        "defaultStatus": "active",
        "coreSkills": [
            {
                "id": "skill-react",
                "name": "React & Frontend",
                "description": "Build responsive UIs with React and modern tooling.",
                "defaultStatus": "in_progress",
                "whatToDo": [
                    "Build a small app with React + hooks",
                    "Learn component state and props",
                    "Add client-side routing",
                ],
                "resources": [
                    {"title": "React Docs", "type": "doc", "url": "https://react.dev"},
                    {"title": "Frontend Roadmap", "type": "article", "url": "https://roadmap.sh/frontend"},
                ],
                "jobSkillKeywords": ["React", "TypeScript", "CSS"],
            },
            {
                "id": "skill-node",
                "name": "Node.js & APIs",
                "description": "Design and build REST APIs with Node.js.",
                "defaultStatus": "not_started",
                "whatToDo": [
                    "Build a REST API with Express",
                    "Add input validation",
                    "Connect to a database",
                ],
                "resources": [
                    {"title": "Node.js Guide", "type": "doc", "url": "https://nodejs.org/en/learn"},
                ],
                "jobSkillKeywords": ["Node.js", "Express", "REST"],
            },
            {
                "id": "skill-sql",
                "name": "Databases & SQL",
                "description": "Model data and write efficient SQL queries.",
                "defaultStatus": "not_started",
                "whatToDo": [
                    "Practice SELECT/JOIN queries",
                    "Design a normalized schema",
                ],
                "resources": [
                    {"title": "SQLBolt", "type": "interactive", "url": "https://sqlbolt.com"},
                ],
                "jobSkillKeywords": ["SQL", "PostgreSQL", "Databases"],
            },
        ],
    },
    {
        "id": "2",
        "title": "Data Scientist",
        "description": "Turn data into insight using statistics and machine learning.",
        "color": "#10b981",
        "matchSignals": ["Python", "Statistics", "Machine Learning"],
        "defaultStatus": "exploring",
        "coreSkills": [
            {
                "id": "skill-python",
                "name": "Python for Data",
                "description": "Use pandas and numpy for data analysis.",
                "defaultStatus": "in_progress",
                "whatToDo": [
                    "Clean a dataset with pandas",
                    "Plot distributions with matplotlib",
                ],
                "resources": [
                    {"title": "pandas Docs", "type": "doc", "url": "https://pandas.pydata.org/docs"},
                ],
                "jobSkillKeywords": ["Python", "pandas", "numpy"],
            },
            {
                "id": "skill-ml",
                "name": "Machine Learning",
                "description": "Train and evaluate ML models.",
                "defaultStatus": "not_started",
                "whatToDo": [
                    "Train a regression model",
                    "Evaluate with cross-validation",
                ],
                "resources": [
                    {"title": "scikit-learn", "type": "doc", "url": "https://scikit-learn.org"},
                ],
                "jobSkillKeywords": ["Machine Learning", "scikit-learn", "Statistics"],
            },
        ],
    },
    {
        "id": "3",
        "title": "Product Manager",
        "description": "Define product strategy and ship features users love.",
        "color": "#f59e0b",
        "matchSignals": ["Communication", "Analytics", "Leadership"],
        "defaultStatus": "exploring",
        "coreSkills": [
            {
                "id": "skill-discovery",
                "name": "Product Discovery",
                "description": "Run user interviews and synthesize needs.",
                "defaultStatus": "not_started",
                "whatToDo": [
                    "Write a problem statement",
                    "Conduct 3 user interviews",
                ],
                "resources": [
                    {"title": "Continuous Discovery", "type": "book", "url": "https://www.producttalk.org"},
                ],
                "jobSkillKeywords": ["User Research", "Roadmapping"],
            },
            {
                "id": "skill-analytics",
                "name": "Product Analytics",
                "description": "Define metrics and analyze product data.",
                "defaultStatus": "not_started",
                "whatToDo": [
                    "Define a North Star metric",
                    "Build a simple funnel analysis",
                ],
                "resources": [
                    {"title": "Amplitude Academy", "type": "course", "url": "https://amplitude.com/academy"},
                ],
                "jobSkillKeywords": ["Analytics", "SQL", "A/B Testing"],
            },
        ],
    },
]
