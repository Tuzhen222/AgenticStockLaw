FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

# Stage 2: Build ứng dụng (Next.js + Tailwind)
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Lệnh này sẽ build ra folder .next/standalone
RUN npm run build

# Stage 3: Chạy ứng dụng (Production Image)
FROM node:20-alpine AS runner
RUN apk add --no-cache libc6-compat
WORKDIR /app
ENV NODE_ENV production

# Tạo user non-root cho bảo mật
# RUN addgroup --system --gid 1001 nodejs
# RUN adduser --system --uid 1001 nextjs

# Copy file cần thiết từ bước Build
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# USER nextjs

EXPOSE 3000
ENV PORT 3000

# Chạy server.js (Next.js standalone tạo ra file này)
CMD ["node", "server.js"]
