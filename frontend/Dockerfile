# Stage 1: build
FROM node:22-alpine AS builder
RUN apk add --no-cache imagemagick

WORKDIR /app
COPY package.json ./
RUN npm install

COPY . .

# Generate PWA icons (magick = ImageMagick v7, no SVG needed)
RUN mkdir -p public/icons && \
    magick -size 512x512 xc:"#1565C0" \
           -fill white -font DejaVu-Sans-Bold -pointsize 300 \
           -gravity Center -annotate 0 "H" \
           /tmp/base-icon.png 2>/dev/null || \
    magick -size 512x512 xc:"#1565C0" /tmp/base-icon.png && \
    for SIZE in 72 96 128 144 152 192 384 512; do \
      magick /tmp/base-icon.png -resize ${SIZE}x${SIZE} public/icons/icon-${SIZE}x${SIZE}.png; \
    done

ARG VITE_API_URL
ARG VITE_LDAP_ENABLED
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_LDAP_ENABLED=$VITE_LDAP_ENABLED

# Build as standard SPA (avoids Quasar PWA build-system bugs with workbox)
RUN npx quasar build

# --- Add PWA files manually to the SPA output ---
# Web app manifest
RUN cp src-pwa/manifest.json dist/spa/manifest.json

# Service worker (push handler, plain ES5 — no bundling needed)
RUN cp public/push-handler.js dist/spa/sw.js

# Inject <link rel="manifest"> and SW registration into index.html
RUN sed -i 's|</head>|<link rel="manifest" href="/manifest.json"></head>|' dist/spa/index.html && \
    sed -i 's|</body>|<script src="/sw-register.js"></script></body>|' dist/spa/index.html

# Stage 2: serve with nginx
FROM nginx:1.27-alpine
COPY --from=builder /app/dist/spa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
