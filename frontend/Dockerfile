# Stage 1: build
FROM node:22-alpine AS builder
RUN apk add --no-cache imagemagick

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Generate PWA icons from the SVG logo (fallback to a solid blue square if absent)
RUN mkdir -p public/icons && \
    if [ -f public/logo.svg ]; then SRC=public/logo.svg; else \
      printf '<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512"><rect width="512" height="512" rx="80" fill="#1565C0"/><text x="256" y="340" font-size="280" font-family="sans-serif" fill="white" text-anchor="middle">H</text></svg>' > /tmp/logo.svg && SRC=/tmp/logo.svg; fi && \
    for SIZE in 72 96 128 144 152 192 384 512; do \
      convert -background none "$SRC" -resize ${SIZE}x${SIZE} public/icons/icon-${SIZE}x${SIZE}.png; \
    done

ARG VITE_API_URL
ARG VITE_LDAP_ENABLED
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_LDAP_ENABLED=$VITE_LDAP_ENABLED
RUN npx quasar build -m pwa

# Stage 2: serve with nginx
FROM nginx:1.27-alpine
COPY --from=builder /app/dist/pwa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
