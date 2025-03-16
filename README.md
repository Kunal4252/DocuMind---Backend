
# DocuMind - Backend

A powerful document management and AI-powered chat system using RAG (Retrieval-Augmented Generation) built with FastAPI, LangChain, and Qdrant.

## 📑 Overview

DocuMind allows users to upload and manage documents (PDF, DOCX), then interact with them through an intelligent chat interface. The system uses state-of-the-art language models to provide accurate answers based on document content.

## ✨ Features

- **Document Management**: Upload, list, and retrieve documents
- **Multi-format Support**: Process both PDF and DOCX files
- **AI-powered Chat**: Interact with documents using natural language
- **Semantic Search**: Find relevant information across large documents
- **User Authentication**: Secure Firebase-based authentication
- **Cloud Storage**: Cloudinary integration for document storage
- **Vector Database**: Qdrant for efficient similarity search

## 🔧 Technology Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL (document metadata and chat history)
- **Vector Database**: Qdrant (document embeddings)
- **AI/ML**: LangChain, Hugging Face models
- **Authentication**: Firebase Auth
- **Storage**: Cloudinary
- **Embeddings**: Hugging Face models

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- Qdrant (local or cloud)
- Firebase project
- Cloudinary account
- Hugging Face account with API access

### Installation

1. Clone the repository
```bash
git clone https://github.com/your-username/documind-backend.git
cd documind-backend
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root (see Environment Variables section)

5. Initialize the database
```bash
python -m app.db.init_db
```

6. Start the application
```bash
uvicorn app.main:app --reload
```

7. Access the API documentation at `http://localhost:8000/docs`

## 📝 API Documentation

### Authentication Endpoints

- `POST /users/signup`: Register a new user
- `POST /users/google-signup`: Register with Google
- `GET /users/profile`: Get user profile
- `PUT /users/profile`: Update user profile
- `POST /users/profile/upload-image`: Upload profile image

### Document Endpoints

- `POST /documents/upload`: Upload a new document
- `GET /documents/list`: List all user documents
- `GET /documents/{document_id}`: Get document details
- `POST /documents/chat/{document_id}`: Chat with a document
- `GET /documents/chat/{document_id}/history`: Get chat history for a document

## ⚙️ Environment Variables

Create a `.env` file in the project root with the following variables:

```
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/documind

# Qdrant Vector Database Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key_if_needed

# Hugging Face AI Configuration
HUGGINGFACE_API_KEY=your_huggingface_api_key
MISTRAL_MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.2

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret

# Firebase Configuration
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_PRIVATE_KEY_ID=your_firebase_private_key_id
FIREBASE_PRIVATE_KEY="your_firebase_private_key"
FIREBASE_CLIENT_EMAIL=your_firebase_client_email
FIREBASE_CLIENT_ID=your_firebase_client_id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_X509_CERT_URL=your_firebase_client_cert_url

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG_MODE=True
```

## 🏛️ Architecture

### Directory Structure

```
app/
├── __init__.py
├── main.py
├── dependencies.py
├── config/           # Configuration files
├── db/               # Database initialization
├── models/           # Database models
├── routes/           # API endpoints
├── schemas/          # Pydantic models
├── services/         # Business logic
└── utils/            # Utility functions
```

### Core Components

1. **Document Processing Pipeline**:
   - Document uploaded to Cloudinary
   - Metadata stored in PostgreSQL
   - Document chunked and embedded
   - Vectors stored in Qdrant

2. **RAG Query Process**:
   - User query converted to embedding
   - Similar chunks retrieved from Qdrant
   - Context-enhanced prompt sent to LLM
   - Response returned to user

## 🔍 Troubleshooting

### Common Issues

1. **Qdrant Connection**:
   - Ensure Qdrant is running and accessible
   - Check URL and API key in .env file
   
2. **HuggingFace Authentication**:
   - Verify API key is correct and has necessary permissions
   - Check model availability and rate limits

3. **Vector Search Issues**:
   - Verify document chunks are properly stored in Qdrant
   - Check metadata structure matches filter conditions
   - Database fallback is implemented for handling search failures


## 🙌 Acknowledgements

- [LangChain](https://www.langchain.com/) for the RAG framework
- [FastAPI](https://fastapi.tiangolo.com/) for the efficient API framework
- [Qdrant](https://qdrant.tech/) for vector similarity search
- [Hugging Face](https://huggingface.co/) for AI models

