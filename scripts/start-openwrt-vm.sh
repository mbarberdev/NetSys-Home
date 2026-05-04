#!/usr/bin/env bash
# Start the OpenWRT QEMU VM for NetSys-Home development.
# Forwards host:8080 → OpenWRT LuCI (192.168.1.1:80)
# Forwards host:2222 → OpenWRT SSH (192.168.1.1:22)
# ubus endpoint: http://localhost:8080/ubus

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
IMG="$ROOT_DIR/openwrt-23.05.5-x86-64-generic-ext4-combined.img"
PID_FILE="/tmp/openwrt-qemu.pid"
LOG_FILE="/tmp/openwrt-boot.log"

if [[ ! -f "$IMG" ]]; then
  echo "ERROR: OpenWRT image not found at $IMG"
  exit 1
fi

# Kill any existing instance
if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stopping existing QEMU instance (PID $OLD_PID)..."
    kill "$OLD_PID"
    sleep 2
  fi
  rm -f "$PID_FILE"
fi

echo "Starting OpenWRT VM..."
qemu-system-x86_64 \
  -enable-kvm \
  -m 256M \
  -drive "file=$IMG,format=raw" \
  -netdev "user,id=net0,net=192.168.1.0/24,host=192.168.1.100,hostfwd=tcp::2222-192.168.1.1:22,hostfwd=tcp::8080-192.168.1.1:80" \
  -device e1000,netdev=net0 \
  -nographic \
  -pidfile "$PID_FILE" \
  > "$LOG_FILE" 2>&1 &

echo "Waiting for OpenWRT to boot (up to 45s)..."
for i in $(seq 1 45); do
  if curl -s --max-time 2 http://localhost:8080/ >/dev/null 2>&1; then
    echo ""
    echo "✓  OpenWRT is up"
    echo "   Web UI : http://localhost:8080"
    echo "   SSH    : ssh root@localhost -p 2222"
    echo "   ubus   : http://localhost:8080/ubus"
    echo "   PID    : $(cat $PID_FILE)"
    exit 0
  fi
  printf "."
  sleep 1
done

echo ""
echo "WARNING: VM did not respond in 45s. Check $LOG_FILE for details."
exit 1
