FROM ghcr.io/astral-sh/uv:python3.13-trixie

WORKDIR /app

# Copy project files (copying pyproject first could be used for better layer caching)
COPY . /app



RUN uv sync --locked

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Start the app with uvicorn; override APP_MODULE, HOST or PORT at runtime if needed
CMD ["uv", "run", "streamlit", "run", "🏠_Dashboard.py"]
