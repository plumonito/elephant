import json
import os
import sys
import time
import math

# from decord import VideoReader
import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import (
    QMainWindow,
    QSlider,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
    QWidget,
    QHBoxLayout,
)

from ui_components.image_label import ImageLabel
from ui_components.mark_canvas import MarkCanvas
from ui_components.record import database, DatabaseFrame
from ui_components.side_menu import SideMenu


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize variables
        self.video_reader_ = None
        self.video_fps_ = 1
        self.last_advance_time_ms = 0
        self.image_: np.array | None = None
        self.timer_ = QTimer()
        self.timer_.setInterval(1000 / 24)  # will be overridden by video loader
        self.timer_.timeout.connect(self.advance_frame)
        self.frame_index_ = 0
        self.playback_speed_ = 1  # Playback speed multiplier
        self.folder_path_ = "data"
        self.current_video_index_ = 0
        self.frame_count_ = 0

        # Load video files
        self.video_files_ = [
            f for f in os.listdir(self.folder_path_) if f.endswith(".mp4")
        ]
        if not self.video_files_:
            QMessageBox.critical(
                self, "Error", "No .mp4 files found in the selected folder."
            )
            sys.exit()

        # Create the central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout (Horizontal)
        main_layout = QHBoxLayout(self.central_widget)

        # Left side layout (70% of the width)
        left_layout = QVBoxLayout()

        # Video display
        self.image_label_ = ImageLabel()
        self.image_label_.mousePressEvent = self.image_clicked
        left_layout.addWidget(self.image_label_, alignment=Qt.AlignmentFlag.AlignLeft)

        # Scrubber (QSlider)
        self.position_slider_ = QSlider(Qt.Horizontal)
        self.position_slider_.setTickPosition(QSlider.TicksBelow)
        self.position_slider_.setMinimum(0)
        self.position_slider_.setMaximum(100)
        self.position_slider_.setValue(0)
        self.position_slider_.valueChanged.connect(self.set_position)

        # Buttons Layout (Horizontal layout for buttons)
        button_layout = QHBoxLayout()

        # Play/Pause Button
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play_pause)
        button_layout.addWidget(self.play_button)

        # Next/Previous Video Buttons
        self.next_button = QPushButton("Next Video")
        self.next_button.clicked.connect(self.next_video)
        button_layout.addWidget(self.next_button)

        self.prev_button = QPushButton("Previous Video")
        self.prev_button.clicked.connect(self.prev_video)
        button_layout.addWidget(self.prev_button)

        # Add MarkCanvas to the left layout
        self.mark_canvas_ = MarkCanvas([], self.position_slider_)

        left_layout.addWidget(self.mark_canvas_)
        left_layout.addWidget(self.position_slider_)
        left_layout.addLayout(button_layout)

        # Add left layout to the main layout
        main_layout.addLayout(left_layout, 7)  # 70% width

        # Right side layout (30% of the width)
        right_layout = QVBoxLayout()

        # JSON content display
        self.side_menu = SideMenu(self.position_slider_)
        right_layout.addWidget(self.side_menu)

        # Add right layout to the main layout
        main_layout.addLayout(right_layout, 3)  # 30% width

        # Keyboard Shortcuts
        self.addAction(
            self.create_action("Play/Pause", self.toggle_play_pause, "Space")
        )
        self.addAction(self.create_action("Increase Speed", self.increase_speed, "L"))
        self.addAction(self.create_action("Play Reverse", self.play_reverse, "J"))
        self.addAction(
            self.create_action("Play Normal Speed", self.play_normal_speed, "K")
        )

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
        self.video_reader_ = cv2.VideoCapture(video_path)
        self.frame_count_ = int(self.video_reader_.get(cv2.CAP_PROP_FRAME_COUNT))

        # Set the timer interval based on the framerate
        self.video_fps_ = self.video_reader_.get(cv2.CAP_PROP_FPS)
        self.timer_.setInterval(1000 / self.video_fps_)
        print(f"FPS: {self.video_fps_}")

        # Get the first frame to determine the size
        self.original_width = self.video_reader_.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.original_height = self.video_reader_.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"Image size: {(self.original_width,self.original_height)}")

        self.position_slider_.setMaximum(self.frame_count_ - 1)
        self.display_image_by_index(0)

        json_file_path_for_movement = os.path.join(
            self.folder_path_, video_file.replace(".mp4", ".json")
        )

        json_file_path_for_points = os.path.join(
            self.folder_path_, video_file.replace(".mp4", "_points.json")
        )

        self.side_menu.load_records(json_file_path_for_points)

        try:
            with open(json_file_path_for_movement, "r") as f:
                json_data = json.load(f)
                self.mark_canvas_.json_data = json_data
                self.mark_canvas_.update()  # Trigger a repaint
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load JSON file: {e}")

        self.update_window_title()

    def next_video(self):
        if self.side_menu.points_saved:
            self.current_video_index_ += 1
            if self.current_video_index_ >= len(self.video_files_):
                self.current_video_index_ = 0
            self.load_video(self.current_video_index_)
        else:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setText("Points need to be saved first.")
            msg_box.setWindowTitle("Error")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()

    def prev_video(self):
        self.current_video_index_ -= 1
        if self.current_video_index_ < 0:
            self.current_video_index_ = len(self.video_files_) - 1
        self.load_video(self.current_video_index_)

    def update_window_title(self):
        self.setWindowTitle(
            f"Video {self.current_video_index_ + 1} out of {len(self.video_files_)}"
        )

    def toggle_play_pause(self):
        self.playback_speed_ = math.copysign(1, self.playback_speed_)  # Keep sign

        if self.timer_.isActive():
            self.timer_.stop()
            self.play_button.setText("Play")
        else:
            self.timer_.start()
            self.play_button.setText("Pause")

    def increase_speed(self):
        if self.playback_speed_ > 0:
            self.playback_speed_ += 1
        else:
            self.play_normal_speed()

    def play_reverse(self):
        if self.playback_speed_ < 0:
            self.playback_speed_ -= 1
        else:
            self.play_normal_speed()
            self.playback_speed_ *= -1

    def play_normal_speed(self):
        self.playback_speed_ = 1

    def set_position(self, position):
        if self.video_reader_:
            self.display_image_by_index(position)

    def advance_frame(self):
        now_ms = time.time() * 1000
        duration_ms = (
            now_ms - self.last_advance_time_ms if self.last_advance_time_ms > 0 else 0
        )
        self.last_advance_time_ms = now_ms

        time_factor = self.video_fps_ / (1000 / duration_ms)

        new_frame_index = self.frame_index_ + self.playback_speed_ * time_factor
        self.display_image_by_index(new_frame_index)

    def display_image_by_index(self, index: int):
        if not self.video_reader_:
            return

        if index < 0:
            index = 0
        elif index >= self.frame_count_:
            index = self.frame_count_ - 1

        self.frame_index_ = index
        db_frame = database.frames.get(self.frame_index_)
        if db_frame is not None:
            # Display image from the database
            self.image_ = (
                db_frame.segmented_image
                if db_frame.segmented_image is not None
                else db_frame.original_image
            )
        else:
            # Nothing in db, just display raw from video
            # self.image_ = self.video_reader_[self.frame_index_].asnumpy()
            self.video_reader_.set(cv2.CAP_PROP_POS_FRAMES, self.frame_index_)
            ret, cv_frame = self.video_reader_.read()
            if not ret:
                return
            self.image_ = cv_frame
        assert self.image_ is not None
        self.image_label_.set_image(self.image_)
        self.position_slider_.setValue(self.frame_index_)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def image_clicked(self, ev: QMouseEvent):
        if ev.button() in [Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton]:
            if self.timer_.isActive():
                self.toggle_play_pause()

            pixelPos = self.image_label_.event_to_image_position(ev.position())

            database.add_point(
                self.frame_index_,
                self.side_menu.get_selected_name(),
                pixelPos,
                is_positive=ev.button() == Qt.MouseButton.LeftButton,
                original_image=self.image_,
            )
            self.side_menu.on_database_changed()

    def update_ui(self, frame: DatabaseFrame) -> None:
        if self.frame_index_ == frame.frame:
            if frame.segmented_image is not None:
                self.image_label_.set_image(frame.segmented_image)
            else:
                self.image_label_.set_image(frame.original_image)
