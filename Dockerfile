FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY warehouse_fleet ./warehouse_fleet
RUN pip install --no-cache-dir -e ".[postgres]"
EXPOSE 9108
CMD ["python", "-m", "warehouse_fleet.server", "--host", "0.0.0.0", "--port", "9108"]
