FROM python:3.6-alpine

COPY . /worker
WORKDIR /worker

RUN apk update \
    && apk add zlib-dev \
    && apk add jpeg-dev \
    && apk add --virtual build-deps gcc python3-dev musl-dev
    
RUN pip install --upgrade pip
RUN pip install -r requirements.txt