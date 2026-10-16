"""Native Spider Audio Studio recording console: real owner-approved input only.

No device enumerated or opened on app startup. The Refresh and Record actions
are explicit. Captures independent vocal/guitar/bass/drum takes on separate
passes, and hands owner WAVs to existing non-destructive multitrack packaging.
"""
from __future__ import annotations

from pathlib import Path
import threading
from PyQt5.QtCore import Qt,QThread,pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QSpinBox,
    QLineEdit,QListWidget,QFileDialog,QMessageBox,QProgressBar,QCheckBox,
)
try:
    from .audio_capture_engine import (
        available_inputs,capture_take,new_take_filename,CaptureError,ROLES)
    from .multitrack import export_session,SessionError
    from .audio_overdub_engine import available_outputs,capture_overdub
    from .backing_cue import validate_recordable_cue
except ImportError:
    from audio_capture_engine import (
        available_inputs,capture_take,new_take_filename,CaptureError,ROLES)
    from multitrack import export_session,SessionError
    from audio_overdub_engine import available_outputs,capture_overdub
    from backing_cue import validate_recordable_cue

TAKE_ROOT=Path.home()/"Documents/Spider Studio/Music/Recorded Takes"

class CaptureWorker(QThread):
    recorded=pyqtSignal(object,str)
    levels=pyqtSignal(float,float,float)
    def __init__(self,filename,device,role,channels,rate,seconds,depth,parent=None):
        super().__init__(parent)
        self.filename,self.device,self.role=filename,device,role
        self.channels,self.rate,self.seconds,self.depth=channels,rate,seconds,depth
        self.stop_event=threading.Event()

    def run(self):
        try:
            result=capture_take(
                self.filename,device=self.device,role=self.role,
                channels=self.channels,rate=self.rate,max_seconds=self.seconds,
                bit_depth=self.depth,
                stop=self.stop_event,
                on_level=lambda peak,rms,seconds:self.levels.emit(peak,rms,seconds))
            self.recorded.emit(result,"")
        except (OSError,ValueError,RuntimeError,FileExistsError) as exc:
            self.recorded.emit(None,str(exc)[:340])

class OverdubWorker(QThread):
    recorded=pyqtSignal(object,str)
    levels=pyqtSignal(float,float,float)
    def __init__(self,filename,cue,input_device,output_device,role,channels,rate,
                 latency,seconds,parent=None):
        super().__init__(parent)
        self.filename=filename
        self.cue=cue
        self.input_device=input_device
        self.output_device=output_device
        self.role=role
        self.channels=channels
        self.rate=rate
        self.latency=latency
        self.seconds=seconds
        self.stop_event=threading.Event()
    def run(self):
        try:
            result=capture_overdub(
                self.filename,cue=self.cue,input_device=self.input_device,
                output_device=self.output_device,role=self.role,
                channels=self.channels,rate=self.rate,
                latency_ms=self.latency,max_seconds=self.seconds,
                stop=self.stop_event,
                on_level=lambda peak,rms,seconds:self.levels.emit(peak,rms,seconds))
            self.recorded.emit(result,"")
        except (OSError,ValueError,RuntimeError,FileExistsError) as exc:
            self.recorded.emit(None,str(exc)[:350])


class SessionWorker(QThread):
    recorded=pyqtSignal(object,str)
    def __init__(self,tracks,title,bpm,parent=None):
        super().__init__(parent)
        self.tracks=list(tracks)
        self.title=title
        self.bpm=bpm
        self.stop_event=threading.Event()
    def run(self):
        try:
            project=export_session(self.tracks,title=self.title,tempo_bpm=self.bpm,
                                   stop=self.stop_event)
            self.recorded.emit(str(project),"")
        except (OSError,ValueError,RuntimeError,SessionError) as exc:
            self.recorded.emit(None,str(exc)[:340])

class AudioCapturePanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.worker=None
        self.takes=[]
        self.last_session=None
        self.setObjectName("spiderAudioCaptureConsole")
        self.setStyleSheet("""QWidget#spiderAudioCaptureConsole{background:#110d20}
            QLabel{color:#f1e6ff} QPushButton{color:#fff;background:#35234c;
            border:1px solid #8968bc;border-radius:7px;padding:8px}
            QSpinBox,QComboBox,QLineEdit,QListWidget{background:#231931;color:#fff;
            border:1px solid #72558e;padding:6px}""")
        layout=QVBoxLayout(self)
        heading=QLabel("SPIDER RECORDING CONSOLE / REAL INSTRUMENT AND VOCAL TAKES")
        heading.setStyleSheet("font-size:20px;font-weight:bold;color:#cba6fa")
        layout.addWidget(heading)
        desc=QLabel(
            "Record real WAV takes using a manually selected input. Choose one "
            "vocal, bass, guitar, keyboard or drum source at a time, or stereo "
            "inputs if your interface supports them. Mic access is never automatic. "
            "No changes are made to PipeWire, JACK, Nova, Webbie or default routing.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        device_row=QHBoxLayout()
        device_row.addWidget(QLabel("Audio input"))
        self.input=QComboBox()
        self.input.setAccessibleName("User selected recording audio input device")
        device_row.addWidget(self.input,1)
        self.refresh_btn=self._button("Refresh Inputs",self.refresh_inputs)
        device_row.addWidget(self.refresh_btn)
        layout.addLayout(device_row)
        settings=QHBoxLayout()
        settings.addWidget(QLabel("Take role"))
        self.role=QComboBox()
        for role in ROLES:
            self.role.addItem(role.replace("_"," ").title(),role)
        self.role.setCurrentIndex(0)
        settings.addWidget(self.role)
        settings.addWidget(QLabel("Channels"))
        self.channels=QComboBox()
        self.channels.addItem("Mono (one input)",1)
        self.channels.addItem("Stereo (two inputs)",2)
        settings.addWidget(self.channels)
        settings.addWidget(QLabel("Rate"))
        self.rate=QComboBox()
        self.rate.addItem("48 kHz",48000)
        self.rate.addItem("44.1 kHz",44100)
        settings.addWidget(self.rate)
        settings.addWidget(QLabel("Bit depth"))
        self.depth=QComboBox()
        self.depth.addItem("16-bit PCM",16)
        self.depth.addItem("24-bit PCM (device must support)",24)
        self.depth.setCurrentIndex(1)
        self.depth.setAccessibleName("Native hardware capture bit depth")
        settings.addWidget(self.depth)
        settings.addWidget(QLabel("Maximum"))
        self.seconds=QSpinBox()
        self.seconds.setRange(1,300)
        self.seconds.setValue(180)
        self.seconds.setSuffix(" s")
        settings.addWidget(self.seconds)
        layout.addLayout(settings)
        overdub_heading=QLabel("BACKING TRACK / FULL-DUPLEX OVERDUB")
        overdub_heading.setStyleSheet("font-weight:bold;color:#c8a8ee")
        layout.addWidget(overdub_heading)
        overdub_row=QHBoxLayout()
        overdub_row.addWidget(QLabel("Cue WAV"))
        self.cue_file=QLineEdit()
        self.cue_file.setReadOnly(True)
        self.cue_file.setPlaceholderText("Select a 16-bit 44.1/48 kHz backing WAV")
        self.cue_file.setAccessibleName("Selected backing cue WAV for full-duplex recording")
        overdub_row.addWidget(self.cue_file,3)
        overdub_row.addWidget(self._button("Choose Backing WAV",self.select_cue))
        layout.addLayout(overdub_row)
        output_row=QHBoxLayout()
        output_row.addWidget(QLabel("Playback device"))
        self.output_device=QComboBox()
        self.output_device.setAccessibleName("Explicit stereo headphone or monitor output for cue")
        output_row.addWidget(self.output_device,2)
        output_row.addWidget(QLabel("Input timing correction"))
        self.latency=QSpinBox()
        self.latency.setRange(-250,250)
        self.latency.setValue(0)
        self.latency.setSuffix(" ms")
        self.latency.setAccessibleName("Manual latency compensation; positive moves recorded take earlier")
        output_row.addWidget(self.latency)
        layout.addLayout(output_row)
        caveat=QLabel(
            "Use headphones to prevent cue spill. This is one shared duplex "
            "stream clock, not measured physical interface latency. "
            "+ms moves recorded audio EARLIER; -ms moves it later. "
            "Overdub input is 16-bit PCM; separate takes can record at 24-bit.")
        caveat.setWordWrap(True)
        layout.addWidget(caveat)
        self.include_cue=QCheckBox(
            "Include backing WAV as an instrumental-bed track in exported sessions")
        self.include_cue.setChecked(False)
        self.include_cue.setAccessibleName("Explicitly add backing cue to multitrack recording exports")
        layout.addWidget(self.include_cue)
        tracks=QHBoxLayout()
        tracks.addWidget(QLabel("Project"))
        self.project_title=QLineEdit("Spider Recording Session")
        self.project_title.setAccessibleName("Recorded multitrack session project title")
        tracks.addWidget(self.project_title,2)
        tracks.addWidget(QLabel("Tempo"))
        self.tempo=QSpinBox()
        self.tempo.setRange(30,300)
        self.tempo.setValue(120)
        tracks.addWidget(self.tempo)
        layout.addLayout(tracks)
        action=QHBoxLayout()
        self.record_btn=self._button("● Record New WAV Take",self.record)
        self.record_btn.setEnabled(False)
        self.stop_btn=self._button("■ Stop and Save Take",self.stop)
        self.stop_btn.setEnabled(False)
        self.export_btn=self._button("Create Multitrack Session",self.export_multitrack)
        action.addWidget(self.record_btn)
        action.addWidget(self.stop_btn)
        action.addWidget(self.export_btn)
        layout.addLayout(action)
        overdub_action=QHBoxLayout()
        self.overdub_btn=self._button("▶ Record Along With Backing",self.record_overdub)
        self.overdub_btn.setEnabled(False)
        overdub_action.addWidget(self.overdub_btn)
        layout.addLayout(overdub_action)
        session_action=QHBoxLayout()
        self.arrange_btn=self._button(
            "Open Recorded Takes in Studio Multitrack Editor",self.open_multitrack)
        self.mix_btn=self._button(
            "Mix Last Recorded Session",self.open_session_mix)
        self.mix_btn.setEnabled(False)
        session_action.addWidget(self.arrange_btn)
        session_action.addWidget(self.mix_btn)
        layout.addLayout(session_action)
        level_row=QHBoxLayout()
        level_row.addWidget(QLabel("INPUT PEAK"))
        self.peak=QProgressBar()
        self.peak.setRange(0,100)
        self.peak.setValue(0)
        self.peak.setAccessibleName("Real-time audio input peak meter")
        level_row.addWidget(self.peak,1)
        self.meter_info=QLabel("No input capture active")
        level_row.addWidget(self.meter_info)
        layout.addLayout(level_row)
        layout.addWidget(QLabel("RECORDED TAKES (independent WAVs; no overwriting existing files)"))
        self.take_list=QListWidget()
        self.take_list.setMinimumHeight(175)
        layout.addWidget(self.take_list,1)
        self.status=QLabel(
            "No microphone has been opened. Click Refresh Inputs to list audio devices, "
            "then choose a device and press Record to start a take.")
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        # No refresh or capture call here: startup must remain device-private.

    def _button(self,title,fn):
        b=QPushButton(title)
        b.clicked.connect(fn)
        return b

    def load_generated_cue(self, path, rate):
        """Arm a finished virtual-band cue; NEVER start input or output devices."""
        if self.worker is not None and self.worker.isRunning():
            self.status.setText(
                "Backing rendered, but a recording or export is active. "
                "It was NOT switched mid-take. Stop first and choose the saved cue.")
            return False
        try:
            info=validate_recordable_cue(path,expected_rate=rate)
            self.cue_file.setText(str(Path(path)))
            self.rate.setCurrentIndex(0 if info["rate"]==48000 else 1)
            # Cue + possible reverb tail must fit within the safe recording bound.
            import math
            seconds=math.ceil(info["seconds"])
            self.seconds.setValue(max(self.seconds.value(),seconds))
            self.project_title.setText(Path(path).stem[:100])
            self.status.setText(
                f"Virtual band backing is ready ({info['seconds']:.1f}s, "
                f"{rate}Hz, 16-bit). Now click Refresh Inputs, choose "
                "a microphone/interface and headphone output, then manually "
                "press Record Along With Backing. Nothing is recording yet.")
            return True
        except (CaptureError,OSError,ValueError) as error:
            self.status.setText("Cannot select the rendered backing: "+str(error)[:280])
            return False

    def select_cue(self):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Finish the current recording before changing the backing track.")
            return
        filename,_=QFileDialog.getOpenFileName(
            self,"Select a licensed WAV backing track",str(Path.home()/"Music"),
            "PCM WAV (*.wav)")
        if filename:
            self.cue_file.setText(filename)
            self.status.setText(
                "Backing selected. Choose an input, stereo playback device, "
                "matching sample rate and headphones before starting overdub.")

    def refresh_inputs(self):
        if self.worker is not None and self.worker.isRunning():
            return
        try:
            results=available_inputs()
            outputs=available_outputs()
            self.input.clear()
            for index,name,channels in results:
                self.input.addItem(f"{name} ({channels} inputs)",(index,channels))
            self.output_device.clear()
            for index,name,channels in outputs:
                self.output_device.addItem(f"{name} ({channels} outputs)",(index,channels))
            self.status.setText(
                f"Found {len(results)} input(s) and {len(outputs)} stereo output(s). "
                "None are open. Choose an input and click Record."
                if results else "No input devices found. Check your audio interface/permissions.")
        except CaptureError as exc:
            self.status.setText(str(exc))
        self.record_btn.setEnabled(self.input.count()>0)
        self.overdub_btn.setEnabled(self.input.count()>0 and self.output_device.count()>0)

    def record_overdub(self):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Finish the other recording or export first.")
            return
        selected=self.input.currentData()
        output=self.output_device.currentData()
        if selected is None or output is None:
            self.status.setText("Refresh and explicitly choose an input and stereo output.")
            return
        if not self.cue_file.text().strip():
            self.status.setText("Select a local WAV backing track before recording along.")
            return
        input_id,max_channels=selected
        if self.channels.currentData()>max_channels:
            self.status.setText("The selected input has too few channels.")
            return
        try:
            TAKE_ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
            if TAKE_ROOT.is_symlink():
                raise CaptureError("The recorded-take directory cannot be a symlink")
            filename=new_take_filename(TAKE_ROOT,self.role.currentData())
            self.worker=OverdubWorker(
                str(filename),self.cue_file.text(),input_id,output[0],
                self.role.currentData(),self.channels.currentData(),
                self.rate.currentData(),self.latency.value(),self.seconds.value(),self)
            self.worker.recorded.connect(self._recorded)
            self.worker.levels.connect(self._levels)
            self.record_btn.setEnabled(False)
            self.overdub_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.worker.start()
            self.status.setText(
                "Full-duplex recording started. Backing plays through selected stereo "
                "output while input records into its own WAV. No live microphone "
                "signal is sent to the speakers.")
        except (CaptureError,OSError,ValueError) as exc:
            self.status.setText("Could not begin overdub: "+str(exc)[:280])

    def record(self):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Stop the current job before starting another recording.")
            return
        selected=self.input.currentData()
        if not selected:
            self.status.setText("Click Refresh Inputs, then choose a recording device.")
            return
        device,max_channels=selected
        channels=self.channels.currentData()
        if channels>max_channels:
            self.status.setText("The selected recording device cannot provide that many channels.")
            return
        try:
            TAKE_ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
            if TAKE_ROOT.is_symlink():
                raise CaptureError("Recording directory cannot be a symlink")
            filename=new_take_filename(TAKE_ROOT,self.role.currentData())
        except (OSError,CaptureError) as exc:
            self.status.setText("Could not prepare recording: "+str(exc)[:230])
            return
        self.worker=CaptureWorker(str(filename),device,self.role.currentData(),
                                  channels,self.rate.currentData(),self.seconds.value(),
                                  self.depth.currentData(),self)
        self.worker.recorded.connect(self._recorded)
        self.worker.levels.connect(self._levels)
        self.stop_btn.setEnabled(True)
        self.record_btn.setEnabled(False)
        self.overdub_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.worker.start()
        self.status.setText(
            "Recording is active on the selected device only. "
            "Click Stop and Save Take to end capture. Audio stays private on this computer.")

    def _levels(self,peak,rms,seconds):
        # Map -60..0 dBFS to a bounded visible meter.
        self.peak.setValue(max(0,min(100,round((peak+60)*100/60))))
        self.meter_info.setText(
            f"{peak:.1f} dBFS peak · {rms:.1f} dBFS RMS · {seconds:.1f} s")

    def stop(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop_event.set()
            self.status.setText("Stopping capture and validating the WAV. Do not close yet.")

    def _recorded(self,result,error):
        worker=self.worker
        if worker is not None and worker.isRunning():
            worker.wait(1500)
        self.record_btn.setEnabled(self.input.count()>0)
        self.stop_btn.setEnabled(False)
        self.refresh_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        if error:
            self.status.setText(
                "Capture rejected or cancelled: "+error+
                ". No incomplete take was published.")
            return
        if isinstance(result,dict):
            path=Path(result["path"])
            self.takes.append({
                "path":str(path),"role":result["role"],
                "label":path.stem[:100],
            })
            self.take_list.addItem(
                f"{len(self.takes):02d} · {result['role']} · "
                f"{result['duration_seconds']:.1f}s · {result['sample_rate']} Hz · "
                f"{result['channels']}ch · {result['sample_width_bits']}-bit · {path.name}")
            self.status.setText(
                "Captured real WAV: "+path.name+
                ". You can record another take or create a multitrack DAW session.")
        elif isinstance(result,str):
            self.last_session=Path(result)
            self.mix_btn.setEnabled(True)
            self.status.setText(
                "Created a private multitrack session: "+result+
                ". Open its copied WAV tracks in your preferred DAW.")

    def _selected_session_tracks(self):
        tracks=list(self.takes)
        if self.include_cue.isChecked():
            cue=Path(self.cue_file.text().strip())
            if (not self.cue_file.text().strip() or not cue.is_file()
                    or cue.is_symlink() or cue.suffix.lower()!=".wav"):
                raise CaptureError("Choose a regular WAV backing file or uncheck Include backing")
            if all(Path(t["path"]).resolve()!=cue.resolve() for t in tracks):
                tracks.insert(0,{"path":str(cue),"role":"instrumental_bed",
                                 "label":"Backing reference cue"})
        return tracks

    def open_multitrack(self):
        """Reuse the EXISTING native multitrack mixer/dialog, not a launcher."""
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Finish the current recording or export first.")
            return
        if not self.takes:
            self.status.setText("Record a real WAV take before opening the multitrack editor.")
            return
        try:
            if __package__:
                from .multitrack_dialog import MultitrackDialog
            else:
                from multitrack_dialog import MultitrackDialog
            editor=MultitrackDialog(
                seed_tracks=self._selected_session_tracks(),
                title=self.project_title.text().strip() or "Spider Recording",
                parent=self)
            editor.tempo.setValue(self.tempo.value())
            editor.exec_()
        except (OSError,ValueError,RuntimeError,SessionError,CaptureError) as exc:
            self.status.setText("Cannot open the recorded multitrack editor: "+str(exc)[:250])

    def open_session_mix(self):
        """Open the existing native audited mixer for actual recorded WAVs."""
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Finish recording or export before opening the mixer.")
            return
        if self.last_session is None or not self.last_session.is_dir():
            self.status.setText("Create a recorded multitrack session first.")
            return
        try:
            if __package__:
                from .session_mix_dialog import SessionMixDialog
            else:
                from session_mix_dialog import SessionMixDialog
            editor=SessionMixDialog(str(self.last_session),self)
            editor.exec_()
        except (OSError,RuntimeError,ValueError) as exc:
            self.status.setText("Cannot open recorded session mixer: "+str(exc)[:260])

    def export_multitrack(self):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Stop recording before exporting a session.")
            return
        if not self.takes:
            self.status.setText("Record at least one real WAV take first.")
            return
        try:
            selected_tracks=self._selected_session_tracks()
        except (CaptureError,OSError) as exc:
            self.status.setText("Cannot add backing cue: "+str(exc)[:230])
            return
        self.worker=SessionWorker(
            selected_tracks,self.project_title.text(),self.tempo.value(),self)
        self.worker.recorded.connect(self._recorded)
        self.stop_btn.setEnabled(False)
        self.record_btn.setEnabled(False)
        self.overdub_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.worker.start()
        self.status.setText("Copying your chosen recordings into a new private multitrack session.")

    def closeEvent(self,event):
        if self.worker is not None and self.worker.isRunning():
            self.stop()
            self.status.setText("Capture/session export is stopping; close after it finishes.")
            event.ignore()
            return
        super().closeEvent(event)
