#!/usr/bin/env python3
"""Webbie local voice verification. Profiles stay on-device, not in GitHub."""
import argparse
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

DEFAULT_PROFILES = Path.home() / ".config/spider-os/webbie/voiceprints.json"
ALLOWED_NAMES = {"cory": "Cory", "shayna": "Shayna"}

def _normalize(values):
    nums = [float(x) for x in values]
    norm = math.sqrt(sum(x*x for x in nums))
    if not nums or norm < 1e-10 or not all(math.isfinite(x) for x in nums):
        raise ValueError("Invalid voice embedding")
    return [x/norm for x in nums]

def _cosine(a, b):
    return sum(x*y for x,y in zip(a,b)) if len(a) == len(b) else -1.0

def _read_profiles(path):
    if not path.is_file():
        return {}
    if path.is_symlink():
        raise ValueError("Profile file must not be a symlink")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("profiles"), dict):
        raise ValueError("Unsupported voiceprint format")
    return data["profiles"]

def _write_profiles(path, profiles):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    fd, temporary = tempfile.mkstemp(prefix=".voiceprints-", dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"version":1,"profiles":profiles},f,indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

class SpeakerGuard:
    """Fail closed if voice model, profiles or match confidence is missing."""
    def __init__(self, config=None, extractor=None):
        config = config or {}
        self.required = config.get("require_voiceprint",True) is not False
        self.threshold = float(config.get("threshold",0.78))
        self.min_gap = float(config.get("min_gap",0.06))
        if not 0.0 < self.threshold <= 1.0 or self.min_gap < 0.0:
            raise ValueError("Invalid voice verification configuration")
        self.path = Path(os.path.expanduser(config.get("profiles_file",str(DEFAULT_PROFILES))))
        self.extractor = extractor
        self._encoder = None
        self.last_error = None

    def profiles(self):
        return _read_profiles(self.path)

    def _embedding(self, wav_path):
        if self.extractor is not None:
            return _normalize(self.extractor(wav_path))
        from resemblyzer import VoiceEncoder, preprocess_wav
        if self._encoder is None:
            self._encoder = VoiceEncoder(device="cpu")
        wav = preprocess_wav(Path(wav_path))
        if len(wav) < 16000:
            raise ValueError("Too little audio for voice matching")
        return _normalize(self._encoder.embed_utterance(wav))

    def identify(self, wav_path):
        if not self.required:
            return "unverified"
        try:
            profiles = self.profiles()
            if not profiles:
                self.last_error = "no_profiles_enrolled"
                return None
            sample = self._embedding(wav_path)
            scores = []
            for name, template in profiles.items():
                if name.lower() not in ALLOWED_NAMES:
                    continue
                scores.append((name,_cosine(sample,_normalize(template))))
            scores.sort(key=lambda item:item[1],reverse=True)
            if not scores or scores[0][1] < self.threshold:
                self.last_error = "voice_not_matched"
                return None
            if len(scores)>1 and scores[0][1]-scores[1][1]<self.min_gap:
                self.last_error = "ambiguous_speaker"
                return None
            self.last_error = None
            return scores[0][0]
        except (ImportError,OSError,ValueError,TypeError,KeyError,RuntimeError) as exc:
            self.last_error = "verifier_unavailable:" + type(exc).__name__
            return None

    def enroll_from_paths(self,name,wav_paths):
        canonical=ALLOWED_NAMES.get(name.lower())
        if not canonical:
            raise ValueError("Only Cory and Shayna may be enrolled")
        if len(wav_paths)<3:
            raise ValueError("At least three voice samples required")
        vectors=[self._embedding(p) for p in wav_paths]
        if len({len(v) for v in vectors})!=1:
            raise ValueError("Incompatible embedding sizes")
        template=_normalize([sum(v[i] for v in vectors) for i in range(len(vectors[0]))])
        profiles=self.profiles()
        profiles[canonical]=template
        _write_profiles(self.path,profiles)
        return canonical

def main(argv=None):
    parser=argparse.ArgumentParser(description="Local Webbie speaker enrollment")
    parser.add_argument("action",choices=("status","enroll","delete"))
    parser.add_argument("name",nargs="?",choices=("Cory","Shayna"))
    args=parser.parse_args(argv)
    guard=SpeakerGuard()
    if args.action=="status":
        try:
            names=sorted(guard.profiles())
            print("Enrolled speakers:",", ".join(names) if names else "(none)")
        except (ValueError,OSError) as e:
            print("Could not read voiceprints:",e)
            return 1
        return 0
    if not args.name:
        parser.error("Speaker name required")
    if args.action=="delete":
        profiles=guard.profiles()
        profiles.pop(args.name,None)
        _write_profiles(guard.path,profiles)
        print("Deleted local voiceprint:",args.name)
        return 0
    try:
        import resemblyzer
    except ImportError:
        print("Install optional resemblyzer in Webbie's Python environment first.")
        return 2
    print("Enroll",args.name,"using three distinct 8-second samples in a quiet room.")
    paths=[]
    try:
        for i in range(3):
            input(f"Press Enter for sample {i+1}/3, then speak naturally... ")
            fd,p=tempfile.mkstemp(prefix="webbie-enroll-",suffix=".wav")
            os.close(fd)
            os.chmod(p,0o600)
            paths.append(p)
            result=subprocess.run(["arecord","-q","-f","S16_LE","-r","16000","-c","1","-d","8",p],check=False)
            if result.returncode:
                raise RuntimeError("Microphone recording failed")
        print("Saved LOCAL voiceprint for",guard.enroll_from_paths(args.name,paths))
        print("Restart: systemctl --user restart webbie.service")
        return 0
    finally:
        for p in paths:
            try:
                os.unlink(p)
            except OSError:
                pass

if __name__=="__main__":
    raise SystemExit(main())
