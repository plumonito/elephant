from PySide6.QtCore import QSize
import numpy as np
from PySide6.QtGui import QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QLabel,
    QSizePolicy,
)


class ImageLabel(QLabel):
    def __init__(self):
        super().__init__()

        self.image_: np.ndarray | None = None
        self.aspect_ = 1.0

        self.setScaledContents(True)

    def set_image(self, image: np.ndarray):
        self.image_ = image

        # Ensure the image is in the correct format (BGR888 or RGB888)
        height = image.shape[0]
        width = image.shape[1]
        assert image.shape == (height, width, 3)

        # Convert NumPy array to bytes
        image_bytes = image.tobytes()

        # Create QImage from the byte array
        self.qimage_ = QImage(
            image_bytes,
            width,
            height,
            image.strides[0],  # bytes per line
            QImage.Format_RGB888,
        )

        self.aspect_ = width / height

        # Create a QPixmap from the QImage
        pixmap = QPixmap.fromImage(self.qimage_)
        self.setPixmap(pixmap)
        self.setMinimumSize(1, 1)
        self.update_margins()

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.update_margins()
        return super().resizeEvent(event)

    def update_margins(self) -> None:
        width = self.width()
        height = self.height()
        label_aspect = width / height

        if label_aspect > self.aspect_:
            hmargin = (width - height * self.aspect_) / 2
            vmargin = 0
        else:
            hmargin = 0
            vmargin = (height - width / self.aspect_) / 2
        self.setContentsMargins(hmargin, vmargin, hmargin, vmargin)
