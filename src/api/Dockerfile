FROM python:3.9-alpine

COPY . /api
WORKDIR /api

RUN apk add python3-dev build-base linux-headers pcre-dev
RUN pip install -r requirements.txt