# TSI Studio

TSI Studio is an AI-powered customer support workspace that helps service agents analyze customer email conversations and generate professional response drafts. The platform organizes email threads, allows agents to provide custom AI instructions, and creates clean, editable replies based on the full conversation history.

Built with a frontend-first architecture using React, FastAPI, and OpenAI integration, TSI Studio streamlines the customer support workflow by making email handling faster, more organized, and more efficient.

---

## Features

- Paste and process complete customer email threads
- Automatically organize emails in chronological order
- AI-powered response generation
- Editable AI-generated drafts
- Regenerate and copy response functionality
- Custom prompt/instruction support
- Frontend-first scalable architecture
- FastAPI backend integration
- OpenAI API support

---

## Workflow

1. Paste the complete customer email thread into the input area.
2. The backend separates and organizes emails chronologically.
3. Customer email history is displayed in a structured format.
4. Agents provide custom AI instructions/prompts.
5. The AI analyzes the conversation history.
6. A professional response draft is generated.
7. Agents can edit, regenerate, or copy the response.

---

## Tech Stack

### Frontend
- React
- TypeScript
- Tailwind CSS
- Vite

### Backend
- FastAPI
- Python
- OpenAI API

### Deployment
- Vercel (Frontend)
- Render (Backend)

---

## Project Structure

```bash
TSI-Studio/
│
├── frontend/        # React frontend application
├── backend/         # FastAPI backend application
├── README.md
└── .gitignore
