"""
actions/templates/office.py — Content templates for LibreOffice documents
"""

import random
from datetime import datetime


DOCUMENT_TITLES = [
    "Project Status Report",
    "Meeting Minutes",
    "Technical Specification",
    "Weekly Summary",
    "Requirements Document",
    "Design Review Notes",
    "Release Plan",
    "Team Performance Overview",
    "Infrastructure Audit",
    "Process Improvement Proposal",
]

DOCUMENT_PARAGRAPHS = [
    "This document provides an overview of the current project status and key milestones achieved during the reporting period.",
    "The team has made significant progress on the core deliverables. All critical path items are on schedule.",
    "Several risks were identified during the review. Mitigation strategies have been put in place for each.",
    "Stakeholder feedback has been largely positive. The next review is scheduled for the end of the month.",
    "Resource allocation remains within budget. No additional headcount is required at this time.",
    "Testing coverage has improved by 15% compared to the previous sprint. The regression suite now covers all critical flows.",
    "The deployment pipeline has been streamlined, reducing release cycle time by approximately 30%.",
    "Cross-team collaboration continues to improve. The shared documentation hub has seen increased engagement.",
    "Security review findings have been addressed. All high-priority items are resolved.",
    "Next steps include finalizing the architecture review and beginning the integration testing phase.",
]

SPREADSHEET_HEADERS = [
    ["Month", "Revenue", "Expenses", "Profit", "Growth %"],
    ["Department", "Headcount", "Budget", "Actual", "Variance"],
    ["Task", "Assigned To", "Status", "Priority", "Due Date"],
    ["Server", "CPU %", "Memory %", "Disk %", "Status"],
    ["Metric", "Q1", "Q2", "Q3", "Q4"],
]

SPREADSHEET_DATA_GENERATORS = {
    "financial": lambda: [
        round(random.uniform(10000, 50000), 2),
        round(random.uniform(5000, 30000), 2),
        round(random.uniform(1000, 20000), 2),
        round(random.uniform(-5, 25), 1),
    ],
    "status": lambda: [
        random.choice(["Active", "Completed", "In Progress", "Blocked"]),
        random.choice(["High", "Medium", "Low"]),
        datetime.now().strftime("%Y-%m-%d"),
    ],
}


def random_document_content():
    title = random.choice(DOCUMENT_TITLES)
    date = datetime.now().strftime("%B %d, %Y")
    paragraphs = random.sample(DOCUMENT_PARAGRAPHS, k=random.randint(3, 6))
    body = "\n\n".join(paragraphs)
    return f"{title}\n{'=' * len(title)}\nDate: {date}\n\n{body}\n"


def random_spreadsheet_data():
    headers = random.choice(SPREADSHEET_HEADERS)
    rows = []
    for i in range(random.randint(5, 15)):
        row = [f"Item {i+1}"]
        for _ in range(len(headers) - 1):
            row.append(str(round(random.uniform(1, 100), 2)))
        rows.append(row)
    return headers, rows
