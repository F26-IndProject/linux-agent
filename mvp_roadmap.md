# LISA MVP Roadmap

This document outlines the development roadmap for the LISA project, summarizing the features and goals of each MVP version, and providing a plan for future development. As of now, the project has reached **MVP V2**.

---

## MVP V0 — System Architecture and Framework

### Goal:
Establish the system architecture and foundational layout for future development.

### Features Implemented:
- Basic web management interface (no business logic):
  - Page for creating roles
  - Page for behavior templates
  - Page for viewing agents
- Text descriptions of roles and templates (not yet functional)
- Demonstration page: "How it will work"
- README / onboarding documentation

### Goal for the Client:
Show the system architecture and how it will be expanded in future versions.

---

## MVP V1 — First Working Prototype

### Goal:
Demonstrate the main working functionality of LISA.

### Features Implemented:
- Create a role via the web interface
- Link roles to activity templates (JSON/YAML format)
- Generate agent configuration files (downloadable JSON/YAML)
- Stub agent for Linux/Windows:
  - Outputs to console or log: `"emulating behavior {role}"`
- Agent status monitoring (stub: “online”/“offline”)

### Goal for the Client:
Show that LISA can create templates and emulate behavior on agents.

---

## MVP V2 — Full Minimal Simulation (NOW)

### Goal:
Support feedback and begin live simulation.

### Features Implemented:
- Real agent for **one OS** (e.g., Linux):
  - Random selection of activity from the template (e.g., opening browser, terminal, etc.)
- Web interface:
  - Role selection from a list
- UX improvements:
  - Input validation
  - Error notifications

### Goal for the Client:
Demonstrate realistic behavior and the start of live activity.


---

##  MVP V3 — Completed Demonstration Product (Next Step)

### Goal:
Deliver a full-featured demonstration version of LISA ready for integration into a cyberpolygon.

### Planned Features:
- Full-featured agent for one OS (e.g., Linux):
  - Activity scheduler by timetable
  - Implementation of behavior by role (dev/admin/user)
- Agent installation on a remote VM via generated installer
- CI/CD agent updates
- Web interface:
  - Panel for creating and editing roles and templates
  - Agent statuses: online, actions, logs
  - "Update agent" button
- Client instructions (PDF/video):
  - How to deploy
  - How to view logs
  - How to create a role

### Goal for the Client:
Provide a demonstration infrastructure simulating peaceful activity, ready for integration into a cyberpolygon.

---

## Current Status

-  **Milestone:** MVP V2 completed
-  **Next Target:** MVP V3 — Completed Demonstration Product
-  **Estimated Timeline:** 1–2 weeks
