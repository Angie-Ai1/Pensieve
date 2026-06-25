#!/bin/bash
# 將 Windows Google Drive 虛擬磁碟(G:，drvfs 串流模式)掛載到 WSL 的 /mnt/g。
# 開機時 Google Drive 桌面版可能還沒就緒，所以加上重試。
set -u

MOUNT_POINT=/mnt/g
DRIVE_LETTER=G:
MAX_RETRIES=30
RETRY_INTERVAL_SEC=10

mkdir -p "$MOUNT_POINT"

if mountpoint -q "$MOUNT_POINT"; then
  echo "mount_gdrive: $MOUNT_POINT 已掛載，略過"
  exit 0
fi

for i in $(seq 1 "$MAX_RETRIES"); do
  if mount -t drvfs "$DRIVE_LETTER" "$MOUNT_POINT" 2>/dev/null; then
    echo "mount_gdrive: 第 $i 次嘗試成功掛載 $DRIVE_LETTER 到 $MOUNT_POINT"
    exit 0
  fi
  sleep "$RETRY_INTERVAL_SEC"
done

echo "mount_gdrive: 重試 $MAX_RETRIES 次後仍無法掛載 $DRIVE_LETTER 到 $MOUNT_POINT" >&2
exit 1
