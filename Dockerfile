FROM ghcr.io/astral-sh/uv:latest

WORKDIR /app

# Copy project files (copying pyproject first could be used for better layer caching)
COPY . /app

# Configure runtime
ENV HOST=0.0.0.0 PORT=8501 APP_MODULE=app:app
ENV UV_NO_DEV=1

RUN uv sync --locked

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Start the app with uvicorn; override APP_MODULE, HOST or PORT at runtime if needed
CMD ["sh", "-c", "streamlit run 🏠_Dashboard.py --server.port ${PORT} --server.address ${HOST}"]
