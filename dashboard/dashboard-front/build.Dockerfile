FROM node:16.20 AS frontend-builder

WORKDIR /build
COPY package.json \
    package-lock.json \
    tsconfig.json \
    /build/
RUN npm install

COPY public /build/public
COPY src /build/src

RUN npm install && npm run build
