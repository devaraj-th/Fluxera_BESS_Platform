FROM node:22.14.0-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22.14.0-alpine
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -S fluxera && adduser -S fluxera -G fluxera
COPY --from=build --chown=fluxera:fluxera /app/.next ./.next
COPY --from=build --chown=fluxera:fluxera /app/public ./public
COPY --from=build --chown=fluxera:fluxera /app/package*.json ./
RUN npm ci --omit=dev
USER fluxera
EXPOSE 3000
CMD ["npm", "run", "start"]
