FROM python:3.9-slim

RUN apt update && \
    apt install --no-install-recommends -y build-essential gcc && \
    apt clean && rm -rf /var/lib/apt/lists/*

WORKDIR /eva

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "./bot.py"]