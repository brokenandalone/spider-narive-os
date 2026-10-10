#!/usr/bin/env python3

import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


WEBBIE_ROOT = Path(
    "/usr/local/lib/spider-os/webbie"
)

if not WEBBIE_ROOT.exists():
    WEBBIE_ROOT = (
        Path(__file__).resolve().parents[1]
    )


sys.path.insert(
    0,
    str(WEBBIE_ROOT / "brain")
)

sys.path.insert(
    0,
    str(WEBBIE_ROOT / "voice")
)


from brain import respond
from interruptible_speech import InterruptibleSpeech
from interrupt_intent import is_direct_stop
from stop_signal import request_stop
from app_open_route import installed_app_request
from voice_turns import VoiceTurnTracker
from dialogue_state import next_window, is_end_conversation
from workspace_names import context_name
from night_mode import asleep as quiet_asleep, set_mode as set_quiet_mode, spoken_mode
from vision_query import visual_question, ask_vision


CONFIG_FILE = (
    WEBBIE_ROOT
    / "config"
    / "default.json"
)


STATE_DIR = (
    Path.home()
    / ".local"
    / "state"
    / "spider-os"
)


RUNTIME_DIR = (
    Path(
        os.environ.get(
            "XDG_RUNTIME_DIR",
            f"/run/user/{os.getuid()}",
        )
    )
    / "spider-os"
)


SOCKET_PATH = (
    RUNTIME_DIR
    / "webbie.sock"
)


WORKSPACE_FILE = (
    RUNTIME_DIR
    / "workspace"
)


STATE_FILE = (
    STATE_DIR
    / "webbie.json"
)


running = True
speech_lock = threading.Lock()
voice_turn_lock = threading.Lock()
speech_playback = InterruptibleSpeech()
voice_turns = VoiceTurnTracker()
awaiting_command_until = 0.0


def load_config():
    try:
        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8",
        ) as handle:
            return json.load(handle)

    except Exception:
        return {
            "wake_words": [
                "hey webbie",
                "webbie",
                "hey web",
                "web",
            ],
            "greet_on_login": True,
            "check_in_minutes": 45,
            "default_user_name": "Cory",
            "context_names": {
                "default": "Cory",
                "studio": "Justin",
                "kali-bay": "Spider",
            },
        }


CONFIG = load_config()


def ensure_directories():
    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RUNTIME_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def current_workspace():
    try:
        value = (
            WORKSPACE_FILE
            .read_text(
                encoding="utf-8"
            )
            .strip()
            .lower()
        )

        return value or "default"

    except Exception:
        return "default"


def current_name():
    # Preserve explicit owner choices; Author defaults to Writer.
    return context_name(current_workspace(), CONFIG)


def write_state(**updates):
    state = {
        "online": True,
        "pid": os.getpid(),
        "workspace": current_workspace(),
        "user_name": current_name(),
        "updated": datetime.now().isoformat(),
    }

    try:
        if STATE_FILE.exists():
            old = json.loads(
                STATE_FILE.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(old, dict):
                state.update(old)

    except Exception:
        pass

    state.update(updates)

    state["online"] = True
    state["pid"] = os.getpid()
    state["workspace"] = current_workspace()
    state["user_name"] = current_name()
    state["updated"] = datetime.now().isoformat()

    try:
        STATE_FILE.write_text(
            json.dumps(
                state,
                indent=2,
            ),
            encoding="utf-8",
        )

    except Exception:
        pass


def notify(title, message):
    try:
        subprocess.Popen(
            [
                "notify-send",
                title,
                message,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    except Exception:
        pass


def say(text):
    text = str(text or "").strip()

    if not text:
        return

    write_state(
        last_reply=text,
    )

    notify(
        "Webbie",
        text,
    )

    speaking_marker = (
        RUNTIME_DIR
        / "webbie-speaking"
    )

    with speech_lock:
        try:
            speaking_marker.write_text(
                "speaking",
                encoding="utf-8",
            )

            speech_playback.speak(text)

        finally:
            try:
                speaking_marker.unlink()
            except OSError:
                pass


def launch(command):
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        return True

    except Exception:
        return False


def workspace_path(*parts):
    return str(
        Path(
            "/usr/local/lib/spider-os"
        ).joinpath(*parts)
    )


def set_workspace(name):
    try:
        WORKSPACE_FILE.write_text(
            name,
            encoding="utf-8",
        )

    except Exception:
        pass


def handle_builtin(command):
    lower = command.lower().strip()

    if re.search(
        r"\b(open|launch|start)\b.*\bthe web\b",
        lower,
    ):
        set_workspace("default")

        launch(
            [
                "python3",
                workspace_path(
                    "the-web",
                    "shell",
                    "main.py",
                ),
            ]
        )

        return "Opening The Web."

    if (
        "deep forage" in lower
        and any(
            word in lower
            for word in (
                "open",
                "launch",
                "start",
                "run",
            )
        )
    ):
        set_workspace("forage")

        launch(
            [
                "python3",
                workspace_path(
                    "forage",
                    "deep-forage",
                    "deep_forage.py",
                ),
            ]
        )

        return "Opening Deep Forage."

    if (
        "forage" in lower
        and any(
            word in lower
            for word in (
                "open",
                "launch",
                "start",
                "run",
            )
        )
    ):
        set_workspace("forage")

        launch(
            [
                "python3",
                workspace_path(
                    "forage",
                    "forage.py",
                ),
            ]
        )

        return "Opening Forage."

    if (
        "kali bay" in lower
        and any(
            word in lower
            for word in (
                "open",
                "launch",
                "start",
                "enter",
            )
        )
    ):
        set_workspace("kali-bay")

        launch(
            [
                workspace_path(
                    "kali-bay",
                    "bin",
                    "kali-bay",
                ),
            ]
        )

        return "Opening Kali Bay."

    if (
        "media" in lower
        and any(
            word in lower
            for word in (
                "open",
                "launch",
                "start",
            )
        )
    ):
        set_workspace("media")

        if launch(
            [
                "/usr/local/bin/spider-media-player"
            ]
        ):
            return "Opening Media."

        return (
            "Spider Media Player is not installed yet."
        )

    if (
        "study" in lower
        and any(
            word in lower
            for word in (
                "open",
                "launch",
                "start",
            )
        )
    ):
        set_workspace("study")

        launch(
            [
                "python3",
                workspace_path(
                    "study",
                    "study.py",
                ),
            ]
        )

        return "Opening Study."

    if (
        "studio" in lower
        and any(
            word in lower
            for word in (
                "open",
                "launch",
                "start",
            )
        )
    ):
        set_workspace("studio")

        return (
            "Studio selected. "
            "I'll call you Justin here."
        )

    if "terminal" in lower and any(
        word in lower
        for word in (
            "open",
            "launch",
            "start",
        )
    ):
        launch(["konsole"])

        return "Opening the terminal."

    if (
        "system settings" in lower
        or "open settings" in lower
    ):
        launch(["systemsettings"])

        return "Opening system settings."

    if (
        "what time" in lower
        or "current time" in lower
    ):
        return datetime.now().strftime(
            "It's %I:%M %p."
        ).replace(" 0", " ")

    if "who am i" in lower:
        return (
            f"You're {current_name()} "
            f"while we're in {current_workspace()}."
        )

    if (
        "who are you" in lower
        or "what are you" in lower
    ):
        return (
            "I'm Webbie, the resident AI "
            "inside Spider OS."
        )

    return None


def handle_command(command, voice=False, expected_turn=None):
    command = str(command or "").strip()

    if not command:
        return ""

    # Stop is a direct, strictly matched intervention, not a generated answer.
    if is_direct_stop(command):
        voice_turns.interrupted()
        speech_playback.stop()
        try:
            request_stop()
        except (OSError, PermissionError):
            pass
        return "Stopped."

    write_state(
        last_heard=command,
        last_input="voice" if voice else "text",
    )

    # Speech-triggered camera questions work only with consent granted in
    # The Web GUI. They cannot enable the webcam or bypass quiet sleep.
    if voice and visual_question(command):
        reply = ask_vision(command)
    else:
        built_in = handle_builtin(command)
        if built_in:
            reply = built_in
        else:
            # A spoken installed-app launch only requests the exact current
            # owner-selected GUI grant; it cannot create one or run commands.
            app_reply = installed_app_request(command) if voice else None
            reply = (app_reply if app_reply is not None else
                     respond(command, context_name=current_name()))

    if voice:
        # A completed model request cannot resume speaking after STOP.
        if expected_turn is not None and not voice_turns.current(expected_turn):
            return 'Stopped.'
        say(reply)

    else:
        write_state(
            last_reply=reply,
        )

    return reply


def clean_phrase(text):
    text = text.lower()
    text = re.sub(
        r"[^a-z0-9\s']",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def remove_wake_word(phrase):
    phrase = clean_phrase(phrase)

    wake_words = sorted(
        CONFIG.get(
            "wake_words",
            [],
        ),
        key=len,
        reverse=True,
    )

    for wake in wake_words:
        wake = clean_phrase(wake)

        index = phrase.find(wake)

        if index >= 0:
            remainder = (
                phrase[
                    index + len(wake):
                ]
                .strip()
            )

            return True, remainder

    return False, phrase


def voice_listener():
    global awaiting_command_until

    try:
        voice_path = str(
            WEBBIE_ROOT
            / "voice"
        )

        if voice_path not in sys.path:
            sys.path.insert(
                0,
                voice_path,
            )

        from whisper_listener import (
            listen_forever,
        )

    except Exception as error:
        write_state(
            voice_listener=False,
            voice_engine="whisper.cpp",
            voice_error=str(error),
        )

        return

    write_state(
        voice_listener=True,
        voice_engine="whisper.cpp",
        voice_error=None,
    )

    def start_voice_turn(command):
        # Keep the microphone listener unblocked while speech and inference
        # run on the reply thread. An overlap is ignored, not queued.
        if not voice_turn_lock.acquire(blocking=False):
            return
        expected_turn = voice_turns.start()
        def worker():
            try:
                handle_command(command, voice=True, expected_turn=expected_turn)
            finally:
                voice_turn_lock.release()
        threading.Thread(target=worker, name='webbie-voice-turn', daemon=True).start()

    def on_interrupt(phrase):
        global awaiting_command_until
        if not is_direct_stop(phrase):
            return
        awaiting_command_until = next_window(
            awaiting_command_until, 'stop', time.time())
        voice_turns.interrupted()
        speech_playback.stop()
        try:
            request_stop()
        except (OSError, PermissionError):
            pass
        write_state(last_reply='Voice interruption requested')

    def on_text(phrase):
        global awaiting_command_until

        phrase = clean_phrase(
            phrase
        )

        if not phrase:
            return

        # Stay operational at night without answering TV, casual speech or
        # wake words alone. Only an exact, deliberate wake phrase reopens chat.
        sleeping = quiet_asleep()
        mode = spoken_mode(phrase, sleeping=sleeping)
        if sleeping:
            awaiting_command_until = 0
            if mode == 'wake':
                set_quiet_mode('wake')
                say("I'm awake.")
            return
        if mode == 'sleep':
            awaiting_command_until = 0
            say("Goodnight. I'll keep everything running quietly.")
            set_quiet_mode('sleep')
            return

        now = time.time()

        # Direct stop cancels current output and keeps follow-up listening open.
        if is_direct_stop(phrase):
            on_interrupt(phrase)
            return
        if is_end_conversation(phrase):
            awaiting_command_until = next_window(
                awaiting_command_until, 'end', now)
            return

        if now < awaiting_command_until:
            woke, command = remove_wake_word(phrase)
            awaiting_command_until = next_window(
                awaiting_command_until, 'command', now)
            start_voice_turn(command if woke and command else phrase)
            return

        woke, command = (
            remove_wake_word(
                phrase
            )
        )

        if not woke:
            return

        if command:
            awaiting_command_until = next_window(
                awaiting_command_until, 'command', now)
            start_voice_turn(command)
            return

        awaiting_command_until = next_window(
            awaiting_command_until, 'wake', now)

        say(
            f"I'm here, "
            f"{current_name()}."
        )

    try:
        listen_forever(
            on_text=on_text,
            should_continue=lambda: running,
            on_interrupt=on_interrupt,
        )

    except Exception as error:
        write_state(
            voice_listener=False,
            voice_engine="whisper.cpp",
            voice_error=str(error),
        )


def session_is_active():
    try:
        output = subprocess.check_output(
            [
                "loginctl",
                "list-sessions",
                "--no-legend",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        for line in output.splitlines():
            parts = line.split()

            if len(parts) < 3:
                continue

            session_id = parts[0]
            username = parts[2]

            if username != os.environ.get(
                "USER",
                "",
            ):
                continue

            active = subprocess.check_output(
                [
                    "loginctl",
                    "show-session",
                    session_id,
                    "-p",
                    "Active",
                    "--value",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            idle = subprocess.check_output(
                [
                    "loginctl",
                    "show-session",
                    session_id,
                    "-p",
                    "IdleHint",
                    "--value",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            return (
                active == "yes"
                and idle != "yes"
            )

    except Exception:
        pass

    return False


def proactive_loop():
    if CONFIG.get(
        "greet_on_login",
        True,
    ):
        time.sleep(8)

        hour = datetime.now().hour

        if hour < 12:
            greeting = "Good morning"

        elif hour < 18:
            greeting = "Good afternoon"

        else:
            greeting = "Good evening"

        if not quiet_asleep():
            say(
                f"{greeting}, {current_name()}. "
                "Webbie is online."
            )

    minutes = max(
        15,
        int(
            CONFIG.get(
                "check_in_minutes",
                45,
            )
        ),
    )

    next_check = (
        time.time()
        + minutes * 60
    )

    while running:
        time.sleep(30)

        if time.time() < next_check:
            continue

        next_check = (
            time.time()
            + minutes * 60
        )

        if not session_is_active() or quiet_asleep():
            # Postpone conversation, not the background service loop.
            continue

        say(
            f"{current_name()}, "
            "do you need anything?"
        )


def socket_server():
    try:
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
    except OSError:
        pass

    server = socket.socket(
        socket.AF_UNIX,
        socket.SOCK_STREAM,
    )

    server.bind(
        str(SOCKET_PATH)
    )

    os.chmod(
        SOCKET_PATH,
        0o600,
    )

    server.listen(5)
    server.settimeout(1)

    while running:
        try:
            client, _ = server.accept()

        except socket.timeout:
            continue

        except OSError:
            break

        with client:
            try:
                data = client.recv(
                    65536
                )

                command = data.decode(
                    "utf-8",
                    errors="replace",
                ).strip()

                reply = handle_command(
                    command,
                    voice=False,
                )

                client.sendall(
                    reply.encode("utf-8")
                )

            except Exception as error:
                try:
                    client.sendall(
                        (
                            "Webbie error: "
                            + str(error)
                        ).encode("utf-8")
                    )

                except Exception:
                    pass

    server.close()

    try:
        SOCKET_PATH.unlink()
    except OSError:
        pass


def stop_service(signum, frame):
    global running
    running = False


def main():
    ensure_directories()

    signal.signal(
        signal.SIGTERM,
        stop_service,
    )

    signal.signal(
        signal.SIGINT,
        stop_service,
    )

    print(
        "Webbie resident AI online.",
        flush=True,
    )

    write_state(
        starting=True,
    )

    threads = [
        threading.Thread(
            target=socket_server,
            name="webbie-ipc",
            daemon=True,
        ),
        threading.Thread(
            target=voice_listener,
            name="webbie-voice",
            daemon=True,
        ),
        threading.Thread(
            target=proactive_loop,
            name="webbie-proactive",
            daemon=True,
        ),
    ]

    for thread in threads:
        thread.start()

    write_state(
        starting=False,
    )

    while running:
        time.sleep(2)

        write_state()

    write_state(
        online=False,
    )

    print(
        "Webbie resident AI shutting down.",
        flush=True,
    )


if __name__ == "__main__":
    main()
