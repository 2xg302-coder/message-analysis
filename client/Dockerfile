# 使用 Node.js 基础镜像
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 全局安装 pnpm
RUN npm install -g pnpm

# 复制 package.json 和 lock 文件
COPY package.json pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install

# 暴露端口
EXPOSE 5173

# 启动命令
CMD ["pnpm", "dev", "--host"]
