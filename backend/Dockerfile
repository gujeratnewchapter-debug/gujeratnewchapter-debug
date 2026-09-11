FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=False \
    DJANGO_MEDIA_ROOT=/app/media

WORKDIR /app

RUN addgroup --system django && adduser --system --ingroup django django

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/media /app/staticfiles
RUN chmod +x /app/docker-entrypoint.sh

RUN chown -R django:django /app
USER django

EXPOSE 8000

CMD ["./docker-entrypoint.sh"]