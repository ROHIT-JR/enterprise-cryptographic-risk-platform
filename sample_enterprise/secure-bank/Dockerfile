FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install --no-install-recommends -y openssl libssl-dev libsodium-dev \
    && apt-get clean

COPY api-gateway/nginx.conf /etc/nginx/conf.d/secure-bank.conf
