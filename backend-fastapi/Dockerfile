FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg2/asyncpg builds are covered by the wheels we use.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Apply migrations, then start the API. (docker-compose overrides this with
# a --reload variant for development.)
CMD ["sh", "entrypoint.sh"]
