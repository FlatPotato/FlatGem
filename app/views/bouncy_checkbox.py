# app/views/bouncy_checkbox.py
# This file contains a truly custom checkbox with an animated indicator.

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QTransform

class CheckIndicator(QWidget):
    """The animated, clickable square part of the checkbox."""
    state_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self._checked = False
        self._scale = 1.0

        self.animation = QPropertyAnimation(self, b"scale")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.Type.OutBack) # This gives a nice overshoot "bounce"

    def isChecked(self): return self._checked

    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self.state_changed.emit(checked)
            self.update()

    def mousePressEvent(self, event):
        self.animation.setStartValue(1.0); self.animation.setEndValue(0.9)
        self.animation.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.rect().contains(event.pos()):
            self.setChecked(not self.isChecked())
            self.animation.setStartValue(0.9); self.animation.setEndValue(1.0)
            self.animation.start()
        else: # If mouse was dragged off, just return to normal
            self.animation.setStartValue(self.get_scale()); self.animation.setEndValue(1.0)
            self.animation.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Apply scale transform
        painter.translate(self.rect().center())
        painter.scale(self._scale, self._scale)
        painter.translate(-self.rect().center())

        # Draw the box
        rect = self.rect().adjusted(1, 1, -1, -1)
        if self._checked:
            painter.setBrush(QColor("#007bff"))
            painter.setPen(Qt.PenStyle.NoPen)
        else:
            painter.setBrush(QColor("#313341"))
            painter.setPen(QPen(QColor("#4f5263"), 2))
        painter.drawRoundedRect(rect, 4, 4)

        # Draw the checkmark if checked
        if self._checked:
            pen = QPen(Qt.GlobalColor.white, 2); pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(rect.x() + 5, rect.y() + 10, rect.x() + 9, rect.y() + 14)
            painter.drawLine(rect.x() + 9, rect.y() + 14, rect.x() + 15, rect.y() + 6)

    def get_scale(self): return self._scale
    def set_scale(self, scale): self._scale = scale; self.update()
    scale = Property(float, get_scale, set_scale)

class BouncyCheckBox(QWidget):
    """A container widget that combines the CheckIndicator and a QLabel."""
    stateChanged = Signal(bool)

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(10)
        self.indicator = CheckIndicator(self)
        self.label = QLabel(text, self)
        layout.addWidget(self.indicator); layout.addWidget(self.label)

        self.indicator.state_changed.connect(self.stateChanged)
        self.label.mouseReleaseEvent = self.indicator.mouseReleaseEvent

    def isChecked(self): return self.indicator.isChecked()
    def setChecked(self, checked): self.indicator.setChecked(checked)