#!/bin/bash
set -e

REMOTE=""
PORT="22"
PROJECT_NAME=$(basename "$(pwd)")
REMOTE_DIR="/workspace/$PROJECT_NAME"

while [[ $# -gt 0 ]]; do
   case $1 in
   -p)
      PORT="$2"
      shift 2
      ;;
   *)
      REMOTE="$1"
      shift
      ;;
   esac
done

if [ -z "$REMOTE" ]; then
   echo "[ERROR] Usage: ./push.sh user@host [-p port]"
   exit 1
fi

echo "[INFO] Bootstrapping remote directory $REMOTE_DIR..."
ssh -p "$PORT" "$REMOTE" "mkdir -p $REMOTE_DIR"

echo "[INFO] Pushing codebase to $REMOTE:$REMOTE_DIR..."
rsync -avz -e "ssh -p $PORT" \
   --exclude 'artifacts/' \
   --exclude 'dataset/' \
   --exclude 'docs/figs/' \
   --exclude '.git/' \
   --exclude '.mypy_cache/' \
   --exclude '.idea/' \
   --exclude '.vscode/' \
   --exclude 'venv/' \
   --exclude 'frontend/' \
   --exclude 'vast/' \
   --exclude '__pycache__/' \
   --exclude '*.pyc' \
   --exclude '*.log' \
   --exclude '.DS_Store' \
   ./ "$REMOTE:$REMOTE_DIR/"

echo "[SUCCESS] Codebase pushed successfully to $PROJECT_NAME!"
