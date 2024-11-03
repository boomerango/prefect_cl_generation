# Automated Cover Letter Generator

An intelligent automation tool that generates personalized cover letters for job applications using LLM and Prefect orchestration.

## Features

- 🤖 Automated cover letter generation using LLM (GPT-4-mini)
- 📝 CV-based personalization
- 🔄 Multi-URL processing
- 🌐 Job description scraping (currently supports Djinni)
- ☁️ Cloud orchestration with Prefect
- 💰 100% Free to run (with your OpenAI API key)

## Prerequisites

- Python 3.8+
- OpenAI API key
- Free Prefect Cloud account
- Local storage for CV file

## Installation

1. Clone the repository
2. Paste CV in root folder
3. Provide OpenAI API key
4. Run deployment build:
```bash
prefect deployment build cv_parser.py:cover_letter_workflow \
    --name "Cover Letter Generator Deployment" \
    --tag "cover-letter" \
    --work-queue "default" \
    --storage-block local-file-system/code-storage \
    --output cover_letter_deployment.yaml
```
5. Deploy to Prefect:
```bash
prefect deployment apply cover_letter_deployment.yaml      
```
6. Start agent pool:
```bash
prefect agent start --pool "default-agent-pool" --work-queue "default"
```
7. Go to Prefect UI and paste job listing links. Modify the parser CSS selector and regexp if you want to use another website.