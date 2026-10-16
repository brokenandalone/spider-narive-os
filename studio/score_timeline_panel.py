"""Native Spider Studio note/score arrangement editor with bounded table pages."""
from __future__ import annotations
from fractions import Fraction
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,
    QTableWidgetItem,QAbstractItemView,QComboBox,QSpinBox,QLineEdit,
    QMessageBox,
)
try:
    from .score_edit_session import ScoreEditor
    from .spider_piano_roll import SpiderPianoRoll
except ImportError:
    from score_edit_session import ScoreEditor
    from spider_piano_roll import SpiderPianoRoll

PAGE_SIZE=300

class ScoreTimelinePanel(QWidget):
    """Owner edits symbolic score notes; Auto Performer receives each revision."""
    def __init__(self, changed=None, parent=None):
        super().__init__(parent)
        self.changed=changed
        self.editor=None
        self.setObjectName("spiderScoreTimeline")
        self.setStyleSheet("""QWidget#spiderScoreTimeline {background:#110d20;color:#eee0ff}
            QLabel {color:#eaddfb} QPushButton {color:white;background:#3b2754;
            padding:7px;border:1px solid #8662ae;border-radius:6px}
            QLineEdit,QComboBox,QSpinBox,QTableWidget {color:#f3e8fc;background:#1d172c;
            border:1px solid #65507f}""")
        layout=QVBoxLayout(self)
        title=QLabel("SPIDER PERFORMANCE EDITOR / FIX NOTES · QUANTIZE · UNDO")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#d5b5ff")
        layout.addWidget(title)
        introduction=QLabel(
            "Edit the actual MIDI/sheet-music performance. The original imported score "
            "stays untouched. Musical positions are quarter-note beats; enter a "
            "fraction such as 1/3 for triplets. Save the result in Auto Performer.")
        introduction.setWordWrap(True)
        layout.addWidget(introduction)
        row=QHBoxLayout()
        row.addWidget(QLabel("View page"))
        self.page=QSpinBox()
        self.page.setRange(1,1)
        self.page.setValue(1)
        self.page.valueChanged.connect(self.refresh)
        row.addWidget(self.page)
        self.totals=QLabel("No performance loaded.")
        row.addWidget(self.totals,1)
        layout.addLayout(row)
        self.piano=SpiderPianoRoll(self)
        self.piano.note_selected.connect(self._roll_note_selected)
        layout.addWidget(self.piano)
        self.table=QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(
            ["Part","Pitch","Start (beats)","Length (beats)","Velocity","Instrument"])
        self.table.setMinimumHeight(240)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._note_selected)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table,1)
        detail=QHBoxLayout()
        detail.addWidget(QLabel("Note"))
        self.pitch=QSpinBox()
        self.pitch.setRange(0,127)
        detail.addWidget(self.pitch)
        detail.addWidget(QLabel("Start"))
        self.start=QLineEdit("0")
        self.start.setAccessibleName("Selected note start beat as decimal or fraction")
        detail.addWidget(self.start)
        detail.addWidget(QLabel("Duration"))
        self.duration=QLineEdit("1")
        self.duration.setAccessibleName("Selected note length in quarter-note beats")
        detail.addWidget(self.duration)
        detail.addWidget(QLabel("Velocity"))
        self.velocity=QSpinBox()
        self.velocity.setRange(1,127)
        detail.addWidget(self.velocity)
        self.apply_button=self._button("Apply Note Edit",self.apply_note)
        detail.addWidget(self.apply_button)
        self.delete_button=self._button("Delete Note",self.delete_note)
        detail.addWidget(self.delete_button)
        layout.addLayout(detail)
        bar=QHBoxLayout()
        bar.addWidget(QLabel("Quantize grid"))
        self.grid=QComboBox()
        for label,sub in (
            ("1/4",1),("1/8",2),("1/8 triplet",3),("1/16",4),
            ("1/16 triplet",6),("1/32",8),("1/32 triplet",12),("1/64",16)):
            self.grid.addItem(label,sub)
        self.grid.setCurrentIndex(3)
        bar.addWidget(self.grid)
        bar.addWidget(QLabel("Strength"))
        self.strength=QSpinBox()
        self.strength.setRange(0,100)
        self.strength.setValue(100)
        self.strength.setSuffix("%")
        bar.addWidget(self.strength)
        self.part=QComboBox()
        self.part.addItem("All parts",None)
        bar.addWidget(self.part)
        bar.addWidget(self._button("Quantize Notes",self.quantize))
        layout.addLayout(bar)
        trans=QHBoxLayout()
        trans.addWidget(QLabel("Transpose selected part"))
        self.transpose_amount=QSpinBox()
        self.transpose_amount.setRange(-24,24)
        self.transpose_amount.setValue(0)
        self.transpose_amount.setSuffix(" semitones")
        trans.addWidget(self.transpose_amount)
        trans.addWidget(self._button("Transpose",self.transpose_part))
        trans.addWidget(self._button("Undo",self.undo))
        trans.addWidget(self._button("Redo",self.redo))
        layout.addLayout(trans)
        self.status=QLabel("Import notation or a recorded MIDI take in Auto Performer first.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def _button(self,text,fn):
        b=QPushButton(text)
        b.clicked.connect(fn)
        return b

    def set_score(self,score):
        self.editor=ScoreEditor(score)
        self.page.blockSignals(True)
        self.page.setValue(1)
        self.page.blockSignals(False)
        self.part.clear()
        self.part.addItem("All parts",None)
        for i,p in enumerate(score.parts):
            self.part.addItem(p.name,i)
        self.refresh()

    def sync_external(self,score):
        """Preserve edit history when another panel changed only GM patches."""
        if self.editor is not None:
            self.editor.score = ScoreEditor(score).score
            self.refresh()

    def _chosen(self):
        if self.editor is None:
            raise ValueError("Load a score first")
        row=self.table.currentRow()
        if row < 0 or row >= self.table.rowCount():
            raise ValueError("Select a note from the table")
        return (self.page.value()-1)*PAGE_SIZE+row

    def refresh(self,*unused):
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(0)
            if self.editor is None:
                self.totals.setText("No performance loaded")
                return
            score=self.editor.score
            pages=max(1,(len(score.notes)+PAGE_SIZE-1)//PAGE_SIZE)
            self.page.blockSignals(True)
            self.page.setRange(1,pages)
            self.page.blockSignals(False)
            index=(self.page.value()-1)*PAGE_SIZE
            subset=score.notes[index:index+PAGE_SIZE]
            self.table.setRowCount(len(subset))
            self.piano.set_notes(subset)
            for row,note in enumerate(subset):
                part=score.parts[note.part]
                values=(part.name,str(note.pitch),str(note.start),str(note.duration),
                        str(note.velocity),str(part.program))
                for col,value in enumerate(values):
                    self.table.setItem(row,col,QTableWidgetItem(value))
            self.totals.setText(
                f"{len(score.notes)} notes · {len(score.parts)} instruments · "
                f"{score.bpm} BPM · {score.duration_seconds:.2f} sec · "
                f"undo {len(self.editor._undo)} / redo {len(self.editor._redo)}")
        finally:
            self.table.blockSignals(False)

    def _roll_note_selected(self,index):
        if 0 <= index < self.table.rowCount():
            self.table.selectRow(index)

    def _note_selected(self):
        try:
            note=self.editor.score.notes[self._chosen()]
        except (ValueError,IndexError,AttributeError):
            return
        self.piano.set_selected(self.table.currentRow())
        self.pitch.setValue(note.pitch)
        self.start.setText(str(note.start))
        self.duration.setText(str(note.duration))
        self.velocity.setValue(note.velocity)

    def _perform(self,fn,success):
        if self.editor is None:
            self.status.setText("Load a score in Auto Performer first.")
            return
        try:
            result=fn()
            self.refresh()
            if result and self.changed is not None:
                self.changed(self.editor.score)
            self.status.setText(success if result else "No musical notes changed.")
        except (ValueError,ZeroDivisionError,OverflowError) as error:
            self.status.setText("Edit refused; original notes preserved: "+str(error)[:220])

    def apply_note(self):
        self._perform(lambda:self.editor.edit_note(
            self._chosen(),pitch=self.pitch.value(),
            start=Fraction(self.start.text().strip()),
            duration=Fraction(self.duration.text().strip()),
            velocity=self.velocity.value()),"Applied note change. Undo available.")

    def delete_note(self):
        self._perform(lambda:self.editor.delete_note(self._chosen()),
                      "Deleted selected note. Undo available.")

    def quantize(self):
        self._perform(lambda:self.editor.quantize(
            self.grid.currentData(),self.strength.value(),self.part.currentData()),
            "Quantized note start positions. Undo available.")

    def transpose_part(self):
        if self.part.currentData() is None:
            self.status.setText("Select one instrument part to transpose; drums remain mapped.")
            return
        self._perform(lambda:self.editor.transpose(self.part.currentData(),
            self.transpose_amount.value()),"Transposed part. Undo available.")

    def undo(self):
        self._perform(lambda:self.editor.undo(),"Undid previous edit.")

    def redo(self):
        self._perform(lambda:self.editor.redo(),"Restored previous edit.")
