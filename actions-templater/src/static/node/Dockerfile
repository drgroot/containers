FROM node:${node_version} AS builder

COPY src /src
COPY tsconfig.json /
COPY package.json /
COPY package-lock.json /

# Install build tool chain
RUN npm install

# run build script
RUN npm run-script build \
  && npm ci --production \
  && npm cache clean --force \
  && find dist -name '*.d.ts' -type f -delete

FROM node:${node_version} AS app

WORKDIR /app

COPY --from=builder /node_modules node_modules
COPY --from=builder /dist dist
COPY package.json .
COPY package-lock.json .

ENV NODE_ENV production
USER node
CMD ["node","dist/index.js"]