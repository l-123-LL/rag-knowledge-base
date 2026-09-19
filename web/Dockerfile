FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# 默认不传：镜像里的前端就是用户视图（不含管理员 Key）。
# 需要管理员视图时显式传：docker compose build --build-arg VITE_ADMIN_API_KEY=xxx web
ARG VITE_ADMIN_API_KEY=""
ENV VITE_ADMIN_API_KEY=$VITE_ADMIN_API_KEY

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
