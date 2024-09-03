# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

"""PySide6 Multimedia player example"""
import numpy as np
import sys
from PySide6.QtCore import QStandardPaths, Qt, Slot, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QImage, QPixmap, QMouseEvent
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
from sam2_processor import Sam2Processor


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.sam2_ = Sam2Processor()

        self.image_label_ = QLabel()
        self.image_label_.setScaledContents(True)
        self.setCentralWidget(self.image_label_)

        tool_bar = QToolBar()
        self.addToolBar(tool_bar)
        self.position_slider_ = QSlider()
        self.position_slider_.setOrientation(Qt.Horizontal)
        self.position_slider_.setMinimum(0)
        self.position_slider_.setMaximum(100)
        available_width = self.screen().availableGeometry().width()
        # self.position_slider_.setwidthsetFixedWidth(available_width / 10)
        self.position_slider_.setValue(0)
        self.position_slider_.setTickInterval(10)
        self.position_slider_.setTickPosition(QSlider.TicksBelow)
        self.position_slider_.setToolTip("Position")
        self.position_slider_.valueChanged.connect(self.set_position)
        tool_bar.addWidget(self.position_slider_)

        self.video_reader_: VideoReader | None = None
        self.timer_ = QTimer()
        self.timer_.setInterval(33)
        self.timer_.timeout.connect(self.advance_frame)

        self.open("data/elephant1.mp4")
        # self.timer_.start()

    def open(self, filename: str):
        self.video_reader_ = VideoReader(filename)
        self.frame_count_ = len(self.video_reader_)
        self.display_image_by_index(0)

    def advance_frame(self) -> None:
        self.display_image_by_index(self.frame_index_ + 1)

    def display_image_by_index(self, index: int):
        assert self.video_reader_ is not None
        if index < 0:
            index = 0
        elif index >= self.frame_count_:
            index = self.frame_count_ - 1
        self.frame_index_ = index
        self.display_image(self.video_reader_[self.frame_index_].asnumpy())

    def display_image(self, image: np.ndarray):
        self.image_ = image
        self.qimage_ = QImage(
            self.image_.tobytes(),
            self.image_.shape[1],
            self.image_.shape[0],
            self.image_.strides[0],
            QImage.Format.Format_BGR888,
        )
        self.image_label_.setPixmap(QPixmap.fromImage(self.qimage_))
        self.image_label_.setMinimumSize(1, 1)
        self.image_label_.mousePressEvent = self.image_clicked

    def set_position(self, position):
        if not self.video_reader_:
            return
        index = int(len(self.video_reader_) * position / 100)
        self.display_image_by_index(index)

    def image_clicked(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.LeftButton:
            localPos = np.array(ev.position().toTuple())
            labelSize = np.array(self.image_label_.size().toTuple())
            relPos = localPos / labelSize
            relPos[0], relPos[1] = relPos[1], relPos[0]
            pixelPos = relPos * self.image_.shape[0:2]
            pixelPos[0], pixelPos[1] = pixelPos[1], pixelPos[0]
            pixelPos = pixelPos.reshape(1, 2)
            self.do_segment(pixelPos)

    def do_segment(self, pixelPos: np.ndarray) -> None:
        mask = self.sam2_.process_click(self.image_, pixelPos)
        mask = mask.astype(np.uint8)
        masked_image = self.image_ * mask[:, :, np.newaxis]
        # color = np.array([30, 144, 255], dtype=np.uint8)
        # mask = mask.astype(np.uint8)
        # masked_image = mask[:, :, np.newaxis] * color.reshape(1, 1, -1)
        # masked_image = np.full(masked_image.shape, 0, dtype=np.uint8)
        self.display_image(masked_image)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    available_geometry = main_win.screen().availableGeometry()
    main_win.resize(available_geometry.width() / 3, available_geometry.height() / 2)
    main_win.show()
    sys.exit(app.exec())
