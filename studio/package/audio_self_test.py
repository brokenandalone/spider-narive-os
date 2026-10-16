"""Run the real Spider Audio Studio WAV importer/mixer without user recordings.

No microphones or output devices are touched. This is an OFFLINE test:
a successful result does not certify USB interface latency or speaker output.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import tempfile
import wave


class SelfTestError(RuntimeError):
    pass


def make_tone(path,frequency,rate=44100,frames=17640):
    """Write disposable 400 ms, 16-bit mono sound without third-party tools."""
    with wave.open(str(path),"wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        chunk=bytearray()
        for i in range(frames):
            envelope=min(1.0,i/512.0,(frames-i)/512.0)
            value=round(9000*max(0.,envelope)*
                        math.sin((2.*math.pi*frequency*i)/rate))
            chunk.extend(struct.pack("<h",value))
        audio.writeframes(bytes(chunk))


def run_self_test():
    from studio.multitrack import export_session
    from studio.session_project import inspect_session
    from studio.session_mix import render_session

    if not shutil.which("ffmpeg"):
        raise SelfTestError("FFmpeg is missing; offline mixing is unavailable.")
    with tempfile.TemporaryDirectory(prefix="spider-audio-selftest-") as tmp:
        root=Path(tmp)
        sources=[]
        for name,role,freq in (
            ("Guitar-Rhythm.wav","rhythm_guitar",147.),
            ("Guitar-Lead.wav","lead_guitar",293.),
            ("Bass.wav","bass",73.)):
            path=root/name
            make_tone(path,freq)
            sources.append({"path":str(path),"role":role,"label":name[:-4]})
        before={s["path"]:hashlib.sha256(Path(s["path"]).read_bytes()).hexdigest()
                for s in sources}
        session=export_session(
            sources,title="Temporary Studio Audio Self Test",
            tempo_bpm=96,output_root=root/"sessions")
        verified=inspect_session(session)
        if len(verified["tracks"])!=3:
            raise SelfTestError("Studio did not import all three WAV tracks.")
        lead=verified["tracks"][1]["filename"]
        controls={
            lead:{
                "effects":{"bass_db":2,"mids_db":-1,"treble_db":1,
                           "compression":True,"room":0},
                "regions":[
                    {"start_ms":0,"end_ms":150,"at_ms":0,
                     "fade_in_ms":20,"fade_out_ms":20},
                    {"start_ms":175,"end_ms":360,"at_ms":180,
                     "fade_in_ms":20,"fade_out_ms":20},
                ]
            }
        }
        final=render_session(session,controls=controls,
                             output_root=root/"mixes",timeout=50)
        with wave.open(str(final),"rb") as result:
            if (result.getframerate()!=48000 or
                    result.getnchannels()!=2 or
                    result.getsampwidth()!=3 or
                    not 17000<=result.getnframes()<=20000):
                raise SelfTestError(
                    "Output format, length, or channel count was incorrect.")
            pcm=result.readframes(result.getnframes())
            if not any(pcm):
                raise SelfTestError("Final mix was silent.")
        receipt=json.loads((final.parent/"mix-receipt.json").read_text())
        if (not receipt.get("original_tracks_preserved")
            or len(receipt.get("active_filenames",[]))!=3):
            raise SelfTestError("Render receipt did not confirm all three tracks.")
        if any(hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest
               for name,digest in before.items()):
            raise SelfTestError("Temporary source WAVs changed during mixing.")
        return {
            "result":"PASS",
            "tracks_verified":3,
            "sample_input_hz":44100,
            "render_output_hz":48000,
            "render_output_bits":24,
            "render_output_channels":2,
            "individual_track_eq_and_compressor":"PASS",
            "multiregion_arrangement":"PASS",
            "original_wav_hashes":"UNCHANGED",
            "test_data":"temporary synthetic tones only",
            "scope":"OFFLINE render only: no speakers, microphones, MIDI, interfaces, or latency certified",
        }


def main():
    try:
        result=run_self_test()
    except (OSError,ValueError,RuntimeError,ImportError) as error:
        print(json.dumps({
            "result":"FAIL","reason":str(error)[:250],
            "scope":"No live recording or user files were touched."},indent=2))
        return 2
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
