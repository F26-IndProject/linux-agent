# LISA - Legitimate Infrastructure Simulation Agent

**Complete Installation and Setup Guide**

## System Requirements

### Backend
- **Python**: 3.11+
- **PostgreSQL**: 15+
- **RAM**: 4GB (minimum)
- **Free disk space**: 50GB

### Frontend
- **Node.js**: 18+
- **Package manager**: npm/yarn/pnpm
- **RAM**: 2GB

## Setup Instructions

### Backend (FastAPI)

1. **Clone the repository and navigate to backend folder**
```bash
git clone https://github.com/LISA-SWP25/backend.git
cd lisa/backend 
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or for Windows:
# venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Setup PostgreSQL**
```bash
createdb lisa_dev
createuser lisa --pwprompt
# Password: pass
```

5. **Start the server**
```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend (Vue.js + Vuetify)

1. **Navigate to frontend folder**
```bash
cd frontend
```

2. **Install dependencies**
```bash
npm install
# or
yarn install
# or
pnpm install
```

3. **Start development server**
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

## Access Points

### Backend API
- **API Health**: http://localhost:8000/api/health
- **API Documentation (Swagger)**: http://localhost:8000/docs
- **System Stats**: http://localhost:8000/api/stats

### Frontend Application
- **Main Interface**: http://localhost:3000
- **About Page**: http://localhost:3000/
- **Agents Management**: http://localhost:3000/agents
- **Add Agent**: http://localhost:3000/addAgentRight


## Installation Verification

After startup, check the following URLs:

1. **Backend health check**: http://localhost:8000/api/health
2. **Frontend application**: http://localhost:3000
3. **API documentation**: http://localhost:8000/docs


## Versions

- **Backend**: v0.1.0
- **Frontend**: v0.0.0
- **Python**: 3.11+
- **FastAPI**: 0.104+
- **Vue**: 3.5+
- **Vuetify**: 3.8+
