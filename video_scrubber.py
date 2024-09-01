# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

"""PySide6 Multimedia player example"""
import sys
from PySide6.QtCore import QStandardPaths, Qt, Slot, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QImage, QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QApplication,
    QDialog,
    QFileDialog,
    QMainWindow,
    QSlider,
    QStyle,
    QToolBar,
)
from decord import VideoReader


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self._image_label = QLabel()
        self.setCentralWidget(self._image_label)

        self._video_reader: VideoReader | None = None
        self.timer = QTimer()
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.advance_frame)

        self.open("data/ELP - Sandbox_ohne_MGMT - 20221215 - 100627.mp4")
        self.timer.start()

    def open(self, filename: str):
        self._video_reader = VideoReader(filename)
        self._frame_index = -1
        self.advance_frame()

    def advance_frame(self) -> None:
        assert self._video_reader is not None
        self._frame_index += 1
        image_np = self._video_reader[self._frame_index].asnumpy()
        self._image = QImage(
            image_np,
            image_np.shape[1],
            image_np.shape[0],
            image_np.strides[0],
            QImage.Format.Format_BGR888,
        )
        self._image_label.setPixmap(QPixmap.fromImage(self._image))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    available_geometry = main_win.screen().availableGeometry()
    main_win.resize(available_geometry.width() / 3, available_geometry.height() / 2)
    main_win.show()
    sys.exit(app.exec())
