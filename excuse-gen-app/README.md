# Excuse Email Draft Tool

A professional web application that helps generate contextual excuse emails using Databricks Model Serving LLM. Built with FastAPI and React, deployable to Databricks Apps.

## Features

- Modern, responsive UI with React and Tailwind CSS
- Real-time email generation using Databricks Model Serving
- Multiple excuse categories and tone options
- Adjustable seriousness level
- Copy to clipboard functionality
- Comprehensive error handling and loading states
- Prometheus metrics for monitoring
- Health check endpoints for deployment

## Project Structure

```
excuse-gen-app/
├── app.yaml              # Databricks Apps configuration
├── requirements.txt      # Python dependencies
├── src/
│   └── app.py           # FastAPI backend entry point
├── public/
│   └── index.html       # Single-page React + Tailwind CSS frontend
├── README.md            # This file
└── .gitignore           # Git ignore configuration
```

## Prerequisites

- Python 3.7+
- Databricks workspace with Apps enabled
- Databricks Model Serving endpoint
- Databricks Personal Access Token

## Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd excuse-gen-app
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your Databricks credentials
   ```

5. Run the development server:
   ```bash
   python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
   ```

6. Visit http://localhost:8000 in your browser

## Deployment to Databricks Apps

1. Ensure you have the Databricks CLI installed and configured

2. Configure the App secret:
   ```bash
   databricks secrets create-scope --scope excuse-gen-app
   databricks secrets put --scope excuse-gen-app --key databricks_token
   ```

3. Deploy the app:
   ```bash
   databricks apps deploy excuse-gen-app --source-code-path /path/to/app
   ```

## API Endpoints

- `POST /api/generate-excuse`: Generate excuse email
- `GET /health`, `/healthz`, `/ready`, `/ping`: Health check endpoints
- `GET /metrics`: Prometheus metrics
- `GET /debug`: Environment debugging information

## Environment Variables

- `DATABRICKS_API_TOKEN`: Your Databricks Personal Access Token
- `DATABRICKS_ENDPOINT_URL`: URL of your Databricks Model Serving endpoint
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details
