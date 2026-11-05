#!/bin/bash
set -e

REMOTE=""
PORT="22"
FETCH_ALL=false
PROJECT_NAME=$(basename "$(pwd)")
REMOTE_ARTIFACTS_DIR="/workspace/$PROJECT_NAME/artifacts"

while [[ $# -gt 0 ]]; do
   case $1 in
   --all)
      FETCH_ALL=true
      shift
      ;;
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
   echo "[ERROR] Usage: ./fetch.sh user@host [-p port] [--all]"
   exit 1
fi

echo "[INFO] Verifying artifacts exist on the remote server..."
if ! ssh -p "$PORT" "$REMOTE" "[ -d $REMOTE_ARTIFACTS_DIR ]"; then
   echo "[ERROR] Sanity Check Failed: No 'artifacts' directory found in /workspace/$PROJECT_NAME."
   exit 1
fi

mkdir -p ./artifacts

if [ "$FETCH_ALL" = true ]; then
   echo "[INFO] Fetching ALL artifacts using rsync (Resume Supported)..."
   rsync -avz --partial --progress -e "ssh -p $PORT" "$REMOTE:$REMOTE_ARTIFACTS_DIR/" ./artifacts/
   echo "[SUCCESS] All artifacts successfully synced!"
else
   echo "[INFO] Locating the most recent run..."
   LATEST_DIR=$(ssh -p "$PORT" "$REMOTE" "ls -td $REMOTE_ARTIFACTS_DIR/*/ 2>/dev/null | head -1")

   if [ -z "$LATEST_DIR" ]; then
      echo "[ERROR] No run directories found inside remote artifacts/."
      exit 1
   fi

   # Clean up potential trailing slashes and whitespace
   LATEST_DIR=$(echo "$LATEST_DIR" | sed 's:/*$::')
   BASENAME=$(basename "$LATEST_DIR")

   echo "[INFO] Fetching latest run: $BASENAME using rsync..."
   rsync -avz --partial --progress -e "ssh -p $PORT" "$REMOTE:$LATEST_DIR" "./artifacts/"

   echo "[SUCCESS] Downloaded successfully to ./artifacts/$BASENAME"
fi
