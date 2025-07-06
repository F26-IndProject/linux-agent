# Database-Driven Linux Agent System

## Linked Issue
**This PR addresses:** Closes #15

## Description
Complete rewrite of Linux agent system to use PostgreSQL database for 
configuration, monitoring, and management.

### What changed?
- Added `agent_builder.py` - automatic agent compilation from DB templates
- Enhanced `database_agent.py` - full database integration
- Implemented real-time activity logging
- Added support for custom applications via DB templates
- Integrated Nuitka compilation for standalone ELF binaries

### Why was this change necessary?
Static configuration files don't scale and lack centralized management. 
This change enables:
- Dynamic agent configuration
- Real-time monitoring
- Centralized management
- Automated deployment

##  Type of Change
- [x]  New feature (non-breaking change that adds functionality)
- [x]  Breaking change (architectural change)

##  Testing
- [x] I have tested these changes locally
- [x] Database connection and queries work
- [x] Agent compilation succeeds
- [x] Activity logging verified

### Test Environment:
- OS: Ubuntu 22.04
- Python version: 3.11
- Database: PostgreSQL 15

### How to test:
1. Setup PostgreSQL with LISA schema
2. Run `python agent_builder.py 1` to build agent from template ID 1
3. Execute compiled agent: `./agent_template_1_*.bin`
4. Verify activity logs in database

##  Checklist
- [x] My code follows the project's style guidelines
- [x] I have performed a self-review of my code
- [x] I have commented my code, particularly in hard-to-understand areas
- [x] Database schema supports new features
- [x] Error handling for database failures
- [x] Logging system properly configured

##  Code Review Notes
Please pay special attention to:
- Database connection handling and error recovery
- Nuitka compilation parameters
- Security of database credentials
- Memory usage during agent compilation

