# Build stage: compile Vue app
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

# Production stage: serve static files via Nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
