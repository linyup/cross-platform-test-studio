FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples
RUN pip install --no-cache-dir .
EXPOSE 4174
CMD ["test-studio", "serve", "--flow", "examples/create-note.flow.json", "--host", "0.0.0.0", "--port", "4174"]
