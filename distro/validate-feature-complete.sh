#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"
fail=0
ok(){ printf 'OK  %s\n' "$1"; }
bad(){ printf 'ERR %s\n' "$1"; fail=1; }
for f in \
  webbie/actions/gateway.py webbie/actions/webbie-action \
  webbie/agent/webbie.py webbie/voice/whisper_listener.py webbie/brain/brain.py \
  forage/local_index.py forage/forage.py forage/engine.py forage/deep-forage/deep_forage.py \
  kali-bay/bin/kali-bay kali-bay/ui/kali_bay.py \
  study/study.py study/store.py study/apa.py study/dashboard.py study/paper_dialog.py \
  media/ai-dj/service.py media/bin/spider-media-player \
  studio/main.py studio/bin/studio author/main.py author/store.py author/bin/author system/apps.py media/bin/spider-media-center \
  system/guardian.py system/vault.py system/bin/spider-guardian system/bin/spider-vault \
  the-web/shell/main.py distro/install-spm.sh distro/build-personal.sh; do
  [[ -f "$f" ]] && ok "$f" || bad "$f missing"
done
python3 -m py_compile webbie/actions/gateway.py webbie/agent/webbie.py webbie/voice/whisper_listener.py webbie/brain/brain.py forage/local_index.py forage/engine.py forage/forage.py forage/deep-forage/deep_forage.py kali-bay/ui/kali_bay.py study/store.py study/study.py study/apa.py study/dashboard.py study/paper_dialog.py media/ai-dj/service.py system/guardian.py system/vault.py system/apps.py studio/main.py author/main.py author/store.py the-web/shell/main.py && ok 'Python syntax' || bad 'Python syntax'
for f in distro/build-iso.sh distro/install-spm.sh distro/build-personal.sh kali-bay/bin/kali-bay media/bin/spider-media-player media/bin/spider-media-center studio/bin/studio author/bin/author webbie/actions/webbie-action; do bash -n "$f" || bad "$f syntax"; done
ok 'Shell syntax'
if grep -Rqi pocketsphinx webbie distro/packages/spider-os-packages.list; then bad 'PocketSphinx remains'; else ok 'Whisper replaced PocketSphinx'; fi
ASSET=''
for f in distro/assets/media/Spider-Media-Player-7.5.0-Kabel-Linux-x64.zip distro/assets/media/Spider-Media-Player-7.5.0-Kabel-Linux-x64-NORMALIZED.zip; do [[ -f "$f" ]] && ASSET="$f" && break; done
if [[ -n "$ASSET" ]]; then
  python3 - "$ASSET" <<'PY'
import sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    names={n.replace('\\','/') for n in z.namelist()}
    assert 'linux-unpacked/spider-media-player' in names
    assert 'linux-unpacked/resources/app.asar' in names
print('OK  Spider Media Player 7.5 Kabel package')
PY
else
  if [[ "${SPM_PROFILE:-public}" == personal ]]; then
    bad 'Personal Kabel ZIP missing from distro/assets/media'
  else
    echo 'SKIP Personal Kabel package: public build; supply a public media ZIP to include Media Player'
  fi
fi
[[ $fail -eq 0 ]] || exit 1
echo '========================================'
echo ' SPIDER OS FEATURE VALIDATION: PASSED'
echo '========================================'
