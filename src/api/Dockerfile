FROM python:3.6-alpine

COPY . /api
WORKDIR /api

ENV PROMETHEUS_MULTIPROC_DIR=multiproc-tmp
RUN rm -rf multiproc-tmp
RUN mkdir multiproc-tmp

RUN pip install -r requirements.txt