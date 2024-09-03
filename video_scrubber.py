import json
import os
import sys
import threading

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QAction, QMouseEvent
from PySide6.QtWidgets import (
    QLabel,
    QApplication,
    QMainWindow,
    QSlider,
    QToolBar,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
    QWidget,
    QHBoxLayout,
    QSizePolicy, QDialog, QComboBox,
)
from decord import VideoReader

from mark_canvas import MarkCanvas
from sam2_processor import Sam2Processor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize variables
        self.run_with_sam = True
        if self.run_with_sam:
            self.sam2_ = Sam2Processor()
        else:
            self.sam2_ = None
        self.video_reader_ = None
        self.timer_ = QTimer()
        self.timer_.setInterval(24)  # will be overridden by video loader
        self.timer_.timeout.connect(self.advance_frame)
        self.frame_index_ = 0
        self.playback_speed_ = 1  # Playback speed multiplier
        self.playback_direction_ = 1  # 1 for forward, -1 for reverse
        self.folder_path_ = "data"
        self.current_video_index_ = 0
        self.frame_count_ = 0

        # Load video files
        self.video_files_ = [f for f in os.listdir(self.folder_path_) if f.endswith(".mp4")]
        if not self.video_files_:
            QMessageBox.critical(self, "Error", "No .mp4 files found in the selected folder.")
            sys.exit()

        self.image_label_ = QLabel()
        self.image_label_.setScaledContents(False)  # Set to False to handle scaling manually
        self.image_label_.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label_.mousePressEvent = self.image_clicked

        # Toolbar for controls
        self.toolbar_ = QToolBar()
        self.addToolBar(Qt.BottomToolBarArea, self.toolbar_)

        # Custom widget to hold the two rows
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)

        # Scrubber (QSlider)
        self.position_slider_ = QSlider(Qt.Horizontal)
        self.position_slider_.setTickPosition(QSlider.TicksBelow)
        self.position_slider_.setMinimum(0)
        self.position_slider_.setMaximum(100)
        self.position_slider_.setValue(0)
        self.position_slider_.valueChanged.connect(self.set_position)

        # Set up layout
        layout = QVBoxLayout()
        self.mark_canvas_ = MarkCanvas([], self.position_slider_)
        layout.addWidget(self.image_label_)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Buttons Layout (Horizontal layout for buttons)
        button_layout = QHBoxLayout()

        # Play/Pause Button
        self.play_pause_action_ = QAction("Play", self)
        self.play_pause_action_.triggered.connect(self.toggle_play_pause)
        play_button = QPushButton("Play")
        play_button.clicked.connect(self.toggle_play_pause)
        button_layout.addWidget(play_button)

        # Next/Previous Video Buttons
        self.next_video_action_ = QAction("Next Video", self)
        self.next_video_action_.triggered.connect(self.next_video)
        next_button = QPushButton("Next Video")
        next_button.clicked.connect(self.next_video)
        button_layout.addWidget(next_button)

        self.prev_video_action_ = QAction("Previous Video", self)
        self.prev_video_action_.triggered.connect(self.prev_video)
        prev_button = QPushButton("Previous Video")
        prev_button.clicked.connect(self.prev_video)
        button_layout.addWidget(prev_button)

        control_layout.addWidget(self.mark_canvas_)
        control_layout.addWidget(self.position_slider_)
        control_layout.addLayout(button_layout)

        self.toolbar_.addWidget(control_widget)

        # Keyboard Shortcuts
        self.addAction(self.create_action("Play/Pause", self.toggle_play_pause, "Space"))
        self.addAction(self.create_action("Increase Speed", self.increase_speed, "L"))
        self.addAction(self.create_action("Play Reverse", self.play_reverse, "J"))
        self.addAction(self.create_action("Play Normal Speed", self.play_normal_speed, "K"))

        # Load the first video
        self.load_video(self.current_video_index_)

    def create_action(self, name, func, shortcut):
        action = QAction(name, self)
        action.triggered.connect(func)
        action.setShortcut(shortcut)
        return action

    def load_video(self, index: int):
        video_file = self.video_files_[index]
        video_path = os.path.join(self.folder_path_, video_file)

        # Use decord for video reading
        self.video_reader_ = VideoReader(video_path)
        self.frame_count_ = len(self.video_reader_)

        # Set the timer interval based on the framerate
        video_fps = self.video_reader_.get_avg_fps()
        self.timer_.setInterval(int(1000 / video_fps))

        # Get the first frame to determine the size
        first_frame = self.video_reader_[0].asnumpy()
        self.original_width = first_frame.shape[1]
        self.original_height = first_frame.shape[0]

        self.position_slider_.setMaximum(self.frame_count_ - 1)
        self.display_image_by_index(0)

        json_file_path = os.path.join(self.folder_path_, video_file.replace('.mp4', '.json'))
        try:
            with open(json_file_path, 'r') as f:
                json_data = json.load(f)
                self.mark_canvas_.json_data = json_data
                self.mark_canvas_.update()  # Trigger a repaint
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load JSON file: {e}")

        self.update_window_title()

    def next_video(self):
        self.current_video_index_ += 1
        if self.current_video_index_ >= len(self.video_files_):
            self.current_video_index_ = 0
        self.load_video(self.current_video_index_)

    def prev_video(self):
        self.current_video_index_ -= 1
        if self.current_video_index_ < 0:
            self.current_video_index_ = len(self.video_files_) - 1
        self.load_video(self.current_video_index_)

    def update_window_title(self):
        self.setWindowTitle(f"Video {self.current_video_index_ + 1} out of {len(self.video_files_)}")

    def toggle_play_pause(self):
        if self.timer_.isActive():
            self.timer_.stop()
            self.play_pause_action_.setText("Play")
        else:
            self.timer_.start()
            self.play_pause_action_.setText("Pause")

    def increase_speed(self):
        if self.playback_direction_ == 1:
            self.playback_speed_ += 4
        else:
            self.playback_direction_ = 1
            self.playback_speed_ = 2

    def play_reverse(self):
        if self.playback_direction_ == -1:
            self.playback_speed_ += 4
        else:
            self.playback_direction_ = -1
            self.playback_speed_ = 2

    def play_normal_speed(self):
        self.playback_speed_ = 2
        self.playback_direction_ = 1

    def set_position(self, position):
        if self.video_reader_:
            self.display_image_by_index(position)

    def advance_frame(self):
        new_frame_index = self.frame_index_ + (self.playback_speed_ * self.playback_direction_)
        self.display_image_by_index(new_frame_index)

    def display_image_by_index(self, index: int):
        if not self.video_reader_:
            return

        if index < 0:
            index = 0
        elif index >= self.frame_count_:
            index = self.frame_count_ - 1

        self.frame_index_ = index
        self.display_image(self.video_reader_[self.frame_index_].asnumpy())
        self.position_slider_.setValue(self.frame_index_)

    def display_image(self, image: np.ndarray):
        self.image_ = image

        # Ensure the image is in the correct format (BGR888 or RGB888)
        if self.image_.ndim != 3 or self.image_.shape[2] not in [3]:
            raise ValueError("Image must be a HxWx3 array for BGR or RGB format")

        # Convert NumPy array to bytes
        image_bytes = self.image_.tobytes()

        # Determine the format of the image
        format = QImage.Format_BGR888 if self.image_.shape[2] == 3 else QImage.Format_RGB888

        # Create QImage from the byte array
        self.qimage_ = QImage(
            image_bytes,
            self.image_.shape[1],  # width
            self.image_.shape[0],  # height
            self.image_.strides[0],  # bytes per line
            format
        )

        # Create a QPixmap from the QImage
        pixmap = QPixmap.fromImage(self.qimage_)

        # Get the size of the QLabel
        canvas_width = self.image_label_.width()
        canvas_height = self.image_label_.height()

        # Calculate the scaling factor
        scale_factor = min(
            canvas_width / self.original_width,
            canvas_height / self.original_height
        )

        # Calculate new dimensions
        new_width = max(1, int(self.original_width * scale_factor))
        new_height = max(1, int(self.original_height * scale_factor))

        # Scale the pixmap to fit the QLabel
        pixmap = pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Set the scaled pixmap to QLabel
        self.image_label_.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Redisplay the image when the window is resized
        self.display_image_by_index(self.frame_index_)

    def image_clicked(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.LeftButton:
            localPos = np.array(ev.position().toTuple())
            labelSize = np.array(self.image_label_.size().toTuple())
            relPos = localPos / labelSize
            relPos[0], relPos[1] = relPos[1], relPos[0]
            pixelPos = relPos * self.image_.shape[0:2]
            pixelPos[0], pixelPos[1] = pixelPos[1], pixelPos[0]
            pixelPos = pixelPos.reshape(1, 2)

            if self.run_with_sam:
                threading.Thread(target=self.do_segment(pixelPos), daemon=True).start()
            self.show_popup(pixelPos)

    def do_segment(self, pixelPos: np.ndarray) -> None:
        mask = self.sam2_.process_click(self.image_, pixelPos)
        mask = mask.astype(np.uint8)
        masked_image = self.image_ * mask[:, :, np.newaxis]
        self.display_image(masked_image)

    def show_popup(self, pixelPos):
        popup = QDialog(self)
        popup.setWindowTitle("Select Name")
        popup_layout = QVBoxLayout()

        names = ["Name1", "Name2", "Name3", "sam2"]
        combobox = QComboBox()
        combobox.addItems(names)
        popup_layout.addWidget(combobox)

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save_click_position(popup, pixelPos, combobox.currentText()))
        popup_layout.addWidget(save_button)

        popup.setLayout(popup_layout)
        popup.exec()

    def save_click_position(self, popup, pixelPos, selected_name):
        if selected_name:
            video_name = os.path.splitext(self.video_files_[self.current_video_index_])[0]
            json_file = os.path.join(self.folder_path_, f"{video_name}_points.json")

            data = {"x": int(pixelPos[0][0]), "y": int(pixelPos[0][1]), "name": selected_name}

            if os.path.exists(json_file):
                with open(json_file, "r+") as f:
                    points = json.load(f)
                    points.append(data)
                    f.seek(0)
                    json.dump(points, f, indent=4)
            else:
                with open(json_file, "w") as f:
                    json.dump([data], f, indent=4)

        popup.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    available_geometry = main_win.screen().availableGeometry()
    main_win.resize(available_geometry.width() / 3, available_geometry.height() / 2)
    main_win.show()
    sys.exit(app.exec())
