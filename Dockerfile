FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable
COPY . .
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
EXPOSE 18090 8080
CMD ["python", "-m", "gap2sku.workbench", "--host", "0.0.0.0", "--port", "8080"]
