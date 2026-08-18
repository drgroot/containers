FROM node:lts AS builder

COPY src /src
COPY tsconfig.json /
COPY package.json /
COPY package-lock.json /

# Install build tool chain
RUN npm install

# run build script
RUN npm run-script build \
  && npm ci --production \
  && npm cache clean --force

FROM node:lts AS app

WORKDIR /app

COPY --from=builder /node_modules node_modules
COPY --from=builder /dist dist
COPY package.json .
COPY package-lock.json .

RUN apt-get update && apt-get install -y sqlite3
RUN mkdir -p /backup
RUN chmod 777 /backup

ENV NODE_ENV production
USER node
CMD ["node","dist/index.js"]