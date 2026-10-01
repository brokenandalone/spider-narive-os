#!/usr/bin/env bash
# Runs inside the installed-system chroot after apt dependencies are installed.
set -Eeuo pipefail

spider_ollama_pid=''
cleanup_runtime_build() {
    if [[ -n "${spider_ollama_pid}" ]]; then
        kill "${spider_ollama_pid}" 2>/dev/null || true
        wait "${spider_ollama_pid}" 2>/dev/null || true
    fi
    rm -rf /tmp/whisper.cpp /tmp/spider-ollama.tar.zst
}
trap cleanup_runtime_build EXIT

git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git /tmp/whisper.cpp
cmake -S /tmp/whisper.cpp -B /tmp/whisper.cpp/build \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF
cmake --build /tmp/whisper.cpp/build --target whisper-cli -j"$(nproc)"
install -Dm755 /tmp/whisper.cpp/build/bin/whisper-cli /usr/local/bin/whisper-cli
install -d /usr/local/share/spider-os/whisper
bash /tmp/whisper.cpp/models/download-ggml-model.sh base.en /usr/local/share/spider-os/whisper
test -s /usr/local/share/spider-os/whisper/ggml-base.en.bin
/usr/local/bin/whisper-cli --help >/dev/null

python3 -m venv /opt/spider-webbie
/opt/spider-webbie/bin/pip install --no-cache-dir edge-tts
python3 -m venv /opt/spider-forage
/opt/spider-forage/bin/pip install --no-cache-dir 'ddgs==9.16.0'

curl -fL --retry 5 https://ollama.com/download/ollama-linux-amd64.tar.zst \
    -o /tmp/spider-ollama.tar.zst
tar --zstd -xf /tmp/spider-ollama.tar.zst -C /usr
if ! id ollama >/dev/null 2>&1; then
    useradd --system --user-group --home-dir /usr/share/ollama --shell /usr/sbin/nologin ollama
fi
install -d -m755 -o ollama -g ollama /usr/share/ollama
install -d -m700 -o ollama -g ollama /usr/share/ollama/.ollama
install -d -m755 -o ollama -g ollama /usr/share/ollama/.ollama/models
# The build has the host's network namespace. Use a separate loopback port,
# and retain the child PID so failures also stop the temporary server.
export HOME=/usr/share/ollama
export OLLAMA_HOST=127.0.0.1:11435
export OLLAMA_MODELS=/usr/share/ollama/.ollama/models
if curl -fsS --max-time 2 "http://${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
    echo 'Ollama build port 11435 is already occupied' >&2
    exit 1
fi
runuser -u ollama -- /usr/bin/ollama serve >/tmp/spider-ollama-build.log 2>&1 &
spider_ollama_pid=$!
spider_ollama_ready=false
for attempt in {1..60}; do
    kill -0 "${spider_ollama_pid}" 2>/dev/null || break
    if curl -fsS --max-time 2 "http://${OLLAMA_HOST}/api/tags" >/dev/null; then
        spider_ollama_ready=true
        break
    fi
    sleep 1
done
if [[ "${spider_ollama_ready}" != true ]]; then
    cat /tmp/spider-ollama-build.log >&2
    exit 1
fi
runuser -u ollama -- /usr/bin/ollama pull qwen3:1.7b
runuser -u ollama -- /usr/bin/ollama list
rm -f /tmp/spider-ollama-build.log
