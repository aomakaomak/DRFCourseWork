FROM python:3.13-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV SECRET_KEY="django-insecure-ca)r=1*d&(c5f(xbh=3&+215ym96)sj1c_q-%fz%d+%1v=aoe0"
ENV CELERY_BROKER_URL="redis://redis:6379/0"
ENV CELERY_BACKEND="redis://redis:6379/0"

RUN mkdir -p /app/media

EXPOSE 8000

# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]