# Stage 1: build
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
ARG VITE_API_URL
ARG VITE_LDAP_ENABLED
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_LDAP_ENABLED=$VITE_LDAP_ENABLED
RUN npm run build

# Stage 2: serve with nginx
FROM nginx:1.27-alpine
COPY --from=builder /app/dist/spa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
