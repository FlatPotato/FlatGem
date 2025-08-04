# app/views/static_icon_button.py
# This file contains a custom QPushButton that ensures its icon never changes color.

from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QIcon, QPainter, QPaintEvent
from PySide6.QtCore import Qt, QSize, QRect

class StaticIconButton(QPushButton):
    """
    A custom QPushButton that paints its icon manually to prevent it from
    being recolored by QSS or disabled states.

    The icon remains static regardless of the button's state (hover,
    pressed, disabled).
    """
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._icon = QIcon()
        self._icon_size = QSize(16, 16) # Default icon size
        self._icon_padding = 8 # Space between icon and text

    def setIcon(self, icon: QIcon):
        """Sets the icon to be displayed."""
        self._icon = icon
        self.update() # Trigger a repaint

    def setIconSize(self, size: QSize):
        """Sets the size for the icon to be drawn."""
        self._icon_size = size
        self.update()

    def paintEvent(self, event: QPaintEvent):
        """
        Overrides the default paint event to draw the button and then
        manually draw the icon on top.
        """
        # First, let the original QPushButton draw itself (background, text, etc.)
        # This respects all QSS properties except for the icon itself.
        super().paintEvent(event)

        # Now, draw our icon on top of the already-drawn button.
        if not self._icon.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # --- Calculate Icon Position ---
            # Get the full rectangle of the button's contents
            content_rect = self.contentsRect()
            # Get the rectangle that the text occupies
            text_rect = painter.fontMetrics().boundingRect(self.text())

            # Position the icon to the left of the text
            # Total width of icon + padding + text
            total_width = self._icon_size.width() + self._icon_padding + text_rect.width()

            # Starting X position for the icon
            icon_x = content_rect.x() + (content_rect.width() - total_width) / 2
            # Center the icon vertically
            icon_y = content_rect.y() + (content_rect.height() - self._icon_size.height()) / 2

            # --- FIX: Use the icon's height, not the button's height ---
            # The actual rectangle where the icon will be drawn
            icon_draw_rect = QRect(int(icon_x), int(icon_y), self._icon_size.width(), self._icon_size.height())

            # --- Draw the Icon ---
            # We use painter.drawPixmap, which does not get affected by color styles.
            # We get the pixmap from the QIcon for the "normal" state only.
            pixmap = self._icon.pixmap(self._icon_size, QIcon.Mode.Normal, QIcon.State.Off)
            painter.drawPixmap(icon_draw_rect, pixmap)