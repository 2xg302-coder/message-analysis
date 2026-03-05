#!/bin/bash

# 获取脚本所在目录并进入
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "🚀 正在启动智能新闻分析系统 (Python 后端版)..."

# 检查 Python 环境
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

# 检查前端依赖
if [ ! -d "client/node_modules" ]; then
    echo "📦 安装前端依赖..."
    cd client && pnpm install && cd ..
fi

# 启动服务
echo "✅ 环境准备就绪，启动服务..."
echo "🌐 前端地址: http://localhost:5173"
echo "🔌 后端地址: http://localhost:3001"
echo "提示: 按 Ctrl+C 可停止所有服务"

# 使用 concurrently 并行启动
# 需要先确保根目录安装了 concurrently
if [ ! -d "node_modules" ]; then
    pnpm install
fi

# 修改 package.json 的 start 命令 (临时覆盖或直接运行)
# 这里直接使用 concurrently 命令
./node_modules/.bin/concurrently \
    "cd server_py && venv/bin/python -m uvicorn main:app --reload --port 3001" \
    "cd client && pnpm dev"
