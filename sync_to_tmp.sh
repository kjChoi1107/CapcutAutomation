#!/bin/bash
# 소스 변경 시 /tmp/shorts_app/ 동기화
PROJ=/Users/a10955/Documents/Project/CapcutAutomation
TMP=/tmp/shorts_app

cp -f "$PROJ/main.py" "$TMP/main.py"
sed -i '' 's|BASE_DIR = Path(__file__).parent|BASE_DIR = Path("/tmp/shorts_app")|' "$TMP/main.py"
cp -f "$PROJ/pipeline/"*.py "$TMP/pipeline/"
cp -f "$PROJ/static/index.html" "$TMP/static/index.html"
echo "동기화 완료"
