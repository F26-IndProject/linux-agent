"""
actions/templates/email.py — Email subject and body templates
"""

import random

SUBJECTS = [
    "Quick question about the project",
    "Meeting follow-up",
    "Status update",
    "Can you review this?",
    "Re: Weekly sync",
    "FYI — schedule change",
    "Action items from today",
    "Reminder: deadline approaching",
    "Sharing some notes",
    "Availability this week?",
    "Update on the deployment",
    "Bug report summary",
    "New documentation ready",
    "Team lunch plans",
    "Re: Server maintenance window",
]

BODIES = [
    "Hi,\n\nJust wanted to follow up on our earlier discussion. Let me know if you have any questions.\n\nBest regards",
    "Hello,\n\nPlease find the attached document for your review. I've highlighted the key changes in section 3.\n\nThanks",
    "Hi team,\n\nHere's a quick update on the current sprint progress. We're on track for the Friday deadline.\n\nCheers",
    "Good morning,\n\nCould you take a look at the latest pull request when you get a chance? No rush.\n\nThanks",
    "Hi,\n\nI've updated the shared drive with the latest reports. The Q2 numbers look solid.\n\nBest",
    "Hello,\n\nJust a reminder that we have a team meeting tomorrow at 10 AM. Please come prepared with your updates.\n\nSee you there",
    "Hi,\n\nI've been looking into the performance issue we discussed. It seems to be related to the database queries. I'll have a fix ready by end of day.\n\nRegards",
    "Hello,\n\nThe new documentation is now live on the wiki. Please review and let me know if anything needs to be updated.\n\nThanks",
]

REPLY_BODIES = [
    "Thanks for the update. I'll review it shortly.",
    "Got it, looks good to me.",
    "Thanks for letting me know. I'll take a look.",
    "Acknowledged. Will follow up after the meeting.",
    "Great work on this. A few minor comments inline.",
]


def random_subject():
    return random.choice(SUBJECTS)


def random_body():
    return random.choice(BODIES)


def random_reply():
    return random.choice(REPLY_BODIES)
