#!/bin/bash

# 获取脚本所在目录并进入
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "🚀 正在启动智能新闻分析系统..."

# 检查是否安装了 pnpm
if ! command -v pnpm &> /dev/null; then
    echo "❌ 错误: 未检测到 pnpm，请先安装: npm install -g pnpm"
    exit 1
fi

# 安装依赖
echo "📦 正在检查并安装依赖..."

# 根目录依赖
if [ ! -d "node_modules" ]; then
    echo "Installing root dependencies..."
    pnpm install
fi

# 前端依赖
if [ ! -d "client/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd client && pnpm install && cd ..
fi

# 后端依赖
if [ ! -d "server/node_modules" ]; then
    echo "Installing backend dependencies..."
    cd server && pnpm install && cd ..
fi

# 启动服务
echo "✅ 依赖安装完成，启动服务..."
echo "🌐 前端地址: http://localhost:5173"
echo "🔌 后端地址: http://localhost:3001"
echo "提示: 按 Ctrl+C 可停止所有服务"

pnpm start
