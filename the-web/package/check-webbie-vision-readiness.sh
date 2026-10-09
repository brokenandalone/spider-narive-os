#!/usr/bin/env bash
# Zero-change host readiness check for Spider OS Webbie Vision + Author.
# No sudo, package installs, webcam capture, service restart, or file writes.
set -uo pipefail

echo '===== Spider OS Webbie Vision Readiness ====='
echo 'This check does not access webcam images, microphone audio or manuscripts.'
echo
for command in python3 ffmpeg ollama git; do
  if command -v "$command" >/dev/null 2>&1; then
    printf 'PASS %-12s %s\n' "$command" "$(command -v "$command")"
  else
    printf 'MISSING %-12s\n' "$command"
  fi
done
echo
echo '===== Resident Webbie ====='
if command -v systemctl >/dev/null 2>&1; then
  systemctl --user is-active webbie.service 2>/dev/null || true
  systemctl --user is-enabled webbie.service 2>/dev/null || true
fi
echo
echo '===== Video hardware (listing only) ====='
found=0
for camera in /dev/video[0-9]*; do
  [[ -c "$camera" ]] || continue
  found=1
  if [[ -r "$camera" ]]; then
    echo "ACCESSIBLE: $camera"
  else
    echo "NOT READABLE: $camera (check video device permissions)"
  fi
done
(( found )) || echo 'No /dev/videoN camera nodes detected'
echo
echo '===== Local Ollama model (listing only) ====='
if command -v ollama >/dev/null 2>&1; then
  if command -v timeout >/dev/null 2>&1; then
    timeout 10 ollama list 2>&1 || echo 'Local model listing unavailable or timed out'
  else
    ollama list 2>&1 || true
  fi
fi
echo
echo '===== Optional face matching ====='
if /usr/bin/python3 -c 'import face_recognition' >/dev/null 2>&1; then
  echo 'AVAILABLE: Optional local familiar-face matching'
else
  echo 'OPTIONAL: face_recognition not present for system Python'
  echo 'Webcam room awareness and microphone remain usable without face profiles.'
fi
echo
echo '===== Installed modules (non-destructive) ====='
for path in \
  /usr/local/lib/spider-os/the-web/shell/main.py \
  /usr/local/lib/spider-os/the-web/shell/webbie_panel.py \
  /usr/local/lib/spider-os/webbie/agent/webbie.py \
  '/home/spider/Documents/Spider OS/Author/library.sqlite3'
do
  if [[ -f "$path" ]]; then
    echo "PRESENT: $path"
  else
    echo "NOT FOUND: $path"
  fi
done
echo
echo 'Readiness inspection complete. No system configuration changed.'
