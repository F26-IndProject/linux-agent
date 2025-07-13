
# LISA-SWP25 Feature Roadmap
*Living Infrastructure Simulator Agent - Development Roadmap*

---

## Project Overview

![Progress](https://img.shields.io/badge/Progress-80%25-green)
![Version](https://img.shields.io/badge/Version-v1.0-blue)
![Status](https://img.shields.io/badge/Status-Active%20Development-yellow)

**LISA-SWP25** is a realistic user behavior simulation platform designed for cybersecurity training and infrastructure testing. It emulates human-like activity in isolated environments (cyber ranges) to create lifelike background operations.

###  Architecture Components
- **Linux Agent** - Linux activity emulation with auto-updates
- **Windows Agent** - Windows behavior simulation 
- **Backend** - PostgreSQL-based API and configuration management
- **Frontend** - Vue.js web interface for management
- **Droppers** - Stealthy payload delivery systems

---

##  Implemented Features
*What is already functional and deployed*

###  Linux Agent (complete_updatable_agent.py)
- [x] **User Activity Emulation**
  - [x] Multi-application simulation (VS Code, Terminal, Firefox)
  - [x] Realistic user interactions (typing, clicking, commands)
  - [x] Custom application support via database configuration
  - [x] Configurable activity templates

- [x] **System Management**
  - [x] Mutex-based agent isolation (AgentMutexManager)
  - [x] Single instance enforcement per user/template
  - [x] Graceful termination of conflicting processes

- [x] **Auto-Update System**
  - [x] Self-updating mechanism (AgentUpdateManager)
  - [x] Database-driven version checking
  - [x] Seamless binary replacement and restart

- [x] **Database Integration**
  - [x] PostgreSQL connectivity (DatabaseManager)
  - [x] Activity and error logging
  - [x] Dynamic template loading
  - [x] Configuration synchronization

- [x] **Monitoring & Reporting**
  - [x] Heartbeat system (HeartbeatManager)
  - [x] System statistics reporting
  - [x] Uptime and activity metrics
  - [x] Backend status synchronization

###  Windows Agent
- [x] **Application Control**
  - [x] Windows application launching (apps.py)
  - [x] Browser URL opening
  - [x] Terminal command execution
  - [x] System settings access
  - [x] Active Directory tools integration

- [x] **File Operations**
  - [x] File editing with default applications
  - [x] Document handling (.txt, .docx)

- [x] **GUI Automation**
  - [x] Keyboard simulation (pyautogui)
  - [x] Form filling capabilities

- [x] **Network Simulation**
  - [x] HTTP request generation
  - [x] Web browsing simulation

- [x] **Configuration System**
  - [x] YAML-based workflow definitions
  - [x] Role-based task execution
  - [x] Weighted random action selection
  - [x] Work hours scheduling

### Backend API
- [x] **Database Management**
  - [x] PostgreSQL integration with SQLAlchemy ORM
  - [x] Pydantic schema validation
  - [x] CRUD operations for roles, templates, agents, builds

- [x] **Configuration Management**
  - [x] Environment-based configuration (dev/prod)
  - [x] Dynamic directory creation

- [x] **Agent Communication**
  - [x] Heartbeat status tracking
  - [x] Last-seen timestamp updates
  - [x] API key validation for security

- [x] **CI/CD Integration**
  - [x] Build trigger and status tracking
  - [x] MVP pipeline simulation

- [x] **Data Management**
  - [x] Soft delete functionality
  - [x] CORS configuration for frontend
  - [x] Activity logging system

### Frontend Interface
- [x] **Framework Setup**
  - [x] Vue 3 + Vuetify integration
  - [x] Pinia state management
  - [x] Router configuration placeholder

- [x] **Theme System**
  - [x] Dark/light mode toggle store
  - [x] Custom font integration (unfonts.css)

### Linux Dropper
- [x] **Payload Delivery**
  - [x] Embedded ELF binary storage (hex-encoded)
  - [x] Agent payload embedding system

- [x] **Stealth Execution**
  - [x] Memory-only execution (memfd_create)
  - [x] Process masquerading (gnome-keyring-daemon)
  - [x] Temp file fallback mechanism

- [x] **Advanced Features**
  - [x] Process injection targeting (bash, gnome-terminal)
  - [x] ptrace-based code injection
  - [x] Self-cleanup and trace removal

- [x] **Security Features**
  - [x] Hidden log files (/var/log/.agent_exec.log)
  - [x] Existing agent termination
  - [x] Anti-persistence mechanisms

---

## Planned Features
*What will be implemented in upcoming releases*

### High Priority
*Critical features for immediate development*

- [ ] **Windows Dropper Development**
  - [ ] Windows payload embedding system
  - [ ] PowerShell-based stealth execution
  - [ ] Process hollowing techniques
  - [ ] Windows Defender evasion
  - [ ] Registry-based persistence options
  - [ ] Self-cleanup mechanisms

- [ ] **Linux Agent Enhancement**
  - [ ] Extended system activity simulation
    - [ ] System service interactions
    - [ ] Log file generation
    - [ ] Package management simulation

- [ ] **Windows Agent Improvements**
  - [ ] Mutex system implementation
    - [ ] Single instance enforcement
    - [ ] Resource conflict prevention
    - [ ] Graceful shutdown handling


### Medium Priority
*Important system enhancements*

- [ ] **Frontend JSON Configuration Generator**

---


## Contributing

### Current Development Focus
- **Immediate**: Windows Dropper implementation
- **Next**: Linux Agent system activity enhancement
- **Following**: Windows Agent mutex system
