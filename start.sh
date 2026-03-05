#!/bin/bash

# 获取脚本所在目录并进入
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "🚀 正在启动智能新闻分析系统 (Python 后端版)..."

# ==========================================
# 1. Python 环境准备
# ==========================================

# 检查 Python 是否存在
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未检测到 python3，请先安装 Python 3.8+"
    exit 1
fi

# 初始化 Python 虚拟环境
if [ ! -d "server_py/venv" ]; then
    echo "🐍 创建 Python 虚拟环境..."
    python3 -m venv server_py/venv
fi

# 激活虚拟环境并安装依赖
echo "📦 正在检查并安装 Python 依赖..."
source server_py/venv/bin/activate
pip install -r server_py/requirements.txt

# ==========================================
# 2. 前端环境准备
# ==========================================

# 检查 pnpm 是否存在
if ! command -v pnpm &> /dev/null; then
    echo "⚠️ 未检测到 pnpm，正在尝试使用 npm 安装 pnpm..."
    npm install -g pnpm
    if ! command -v pnpm &> /dev/null; then
        echo "❌ pnpm 安装失败，请手动安装 pnpm: npm install -g pnpm"
        exit 1
    fi
fi

# 安装根目录依赖 (concurrently)
if [ ! -d "node_modules" ]; then
    echo "📦 安装根目录工具依赖..."
    pnpm install
fi

# 安装前端依赖
if [ ! -d "client/node_modules" ]; then
    echo "📦 安装前端依赖..."
    cd client
    pnpm install
    cd ..
fi

# ==========================================
# 3. 启动服务
# ==========================================

echo "✅ 环境准备就绪，启动服务..."
echo "🌐 前端地址: http://localhost:5173"
echo "🔌 后端地址: http://localhost:3001"
echo "提示: 按 Ctrl+C 可停止所有服务"

# 使用 concurrently 并行启动
# 注意：这里使用绝对路径引用 venv 中的 python，确保正确性
./node_modules/.bin/concurrently \
    --kill-others \
    --prefix "[{name}]" \
    --names "BACKEND,FRONTEND" \
    --prefix-colors "blue,magenta" \
    "cd server_py && venv/bin/python -m uvicorn main:app --reload --port 3001" \
    "cd client && pnpm dev"
