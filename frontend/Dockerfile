# Stage 1: build
FROM node:22-alpine AS builder
RUN apk add --no-cache imagemagick

WORKDIR /app
COPY package.json ./
RUN npm install

COPY . .

# Generate PWA icons using ImageMagick v7 (magick cmd, no SVG/librsvg needed)
# Creates a blue square with a white "H" using a built-in font, falls back to plain square
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
RUN npx quasar build -m pwa

# Stage 2: serve with nginx
FROM nginx:1.27-alpine
COPY --from=builder /app/dist/pwa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
