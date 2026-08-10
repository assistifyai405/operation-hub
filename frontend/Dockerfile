# Multi-stage frontend build → nginx
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json yarn.lock* package-lock.json* ./
RUN if [ -f yarn.lock ]; then yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; \
    else yarn install; fi
COPY . ./
ARG REACT_APP_BACKEND_URL=http://localhost:8000
ARG REACT_APP_BILLING_ENABLED=false
ARG REACT_APP_ENABLE_DEMO_LOGIN=false
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
ENV REACT_APP_BILLING_ENABLED=$REACT_APP_BILLING_ENABLED
ENV REACT_APP_ENABLE_DEMO_LOGIN=$REACT_APP_ENABLE_DEMO_LOGIN
RUN yarn build || npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/health || exit 1
CMD ["nginx", "-g", "daemon off;"]
