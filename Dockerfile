FROM python:3.12-slim-bullseye

RUN apt-get update 

WORKDIR /app

COPY ./requirements.txt /app

RUN pip install --requirement /app/requirements.txt --timeout=5000

COPY . .

EXPOSE 8080
EXPOSE 8000

CMD ./init.sh
