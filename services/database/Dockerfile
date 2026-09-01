FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Create the database if needed, apply migrations, then serve.
CMD ["sh", "entrypoint.sh"]
