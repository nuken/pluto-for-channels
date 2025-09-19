FROM python:3.13-slim-bookworm

EXPOSE 7777/tcp

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --disable-pip-version-check --no-compile -r requirements.txt

COPY pywsgi.py ./
COPY pluto.py ./

CMD ["python3","pywsgi.py"]
