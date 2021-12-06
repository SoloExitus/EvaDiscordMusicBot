FROM python:3.9-slim

RUN apt update && \
    apt install --no-install-recommends -y build-essential gcc && \
    apt install -y curl &&\
    apt clean && rm -rf /var/lib/apt/lists/*

WORKDIR /eva

COPY ./entrypoint.sh /home/entrypoint.sh
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN ["chmod", "+x", "/home/entrypoint.sh"]
ENTRYPOINT ["/home/entrypoint.sh"]

CMD ["python", "-u", "bot.py"]