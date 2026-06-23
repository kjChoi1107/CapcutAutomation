#!/bin/bash
# Shorts Auto Editor - 서버 시작 스크립트
# 사용법: bash start.sh [API_KEY]

if [ -n "$1" ]; then
  export ANTHROPIC_API_KEY="$1"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

/usr/bin/python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/Library/Python/3.9/lib/python/site-packages'))
os.chdir('$SCRIPT_DIR')
import uvicorn
port = int(os.environ.get('PORT', 8000))
print(f'서버 시작: http://localhost:{port}')
uvicorn.run('main:app', host='0.0.0.0', port=port, loop='asyncio', http='h11')
"
