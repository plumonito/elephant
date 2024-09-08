import time

import numpy as np

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QStatusTipEvent

from database import active_db, DatabaseFrame, Record
from sam2_processor import Sam2Processor
from video_scrubber import MainWindow
from queue import SimpleQueue

COLOR_GREEN = np.array([0, 255, 0], dtype=np.uint8).reshape(1, 1, 3)
COLOR_RED = np.array([0, 0, 255], dtype=np.uint8).reshape(1, 1, 3)


class BackgroundSegmenter:
    def __init__(self, window: MainWindow, work_queue: SimpleQueue) -> None:
        self.should_stop = False
        self.window = window

        self.run_with_sam = True
        if self.run_with_sam:
            self.sam2_ = Sam2Processor()
        else:
            self.sam2_ = None

        self.work_queue_ = work_queue
        # self.ui_queue_ = SimpleQueue()

    def run(self) -> None:
        while not self.should_stop:
            try:
                frame: DatabaseFrame = self.work_queue_.get(block=True, timeout=0.5)
            except:
                continue

            if QApplication.activeWindow() is not None:
                QApplication.sendEvent(
                    QApplication.activeWindow(),
                    QStatusTipEvent(
                        f"sam2:Segmenting {self.work_queue_.qsize()+1} frames..."
                    ),
                )
            for record in frame.records.values():
                if record.segmentation is None:
                    # Segment!
                    self.segment_record(frame, record)

            # Combine segmentations into a single image
            self.update_frame_image(frame)

            # Trigger UI update
            # self.ui_queue_.put(frame)
            self.window.update_ui(frame)

            if QApplication.activeWindow() is not None:
                if self.work_queue_.empty():
                    QApplication.sendEvent(
                        QApplication.activeWindow(), QStatusTipEvent("sam2:Ready")
                    )

    def segment_record(self, frame: DatabaseFrame, record: Record) -> None:
        if self.sam2_:
            mask = self.sam2_.process_click(
                frame.original_image, record.positive_points, record.negative_points
            )
            mask = mask.astype(np.uint8)
        else:
            mask = np.full(
                (frame.original_image.shape[0], frame.original_image.shape[1]), 0
            )
        record.segmentation = mask

    def update_frame_image(self, frame: DatabaseFrame) -> None:

        masked_image = frame.original_image.copy()
        for record in frame.records.values():
            assert record.segmentation is not None
            masked_image = masked_image * record.segmentation[:, :, np.newaxis]

        # Add clicks
        for record in frame.records.values():
            for pixelPos in record.positive_points:
                pixelPos = pixelPos.reshape(-1).astype(np.int32)
                masked_image[
                    pixelPos[1] - 5 : pixelPos[1] + 5, pixelPos[0] - 5 : pixelPos[0] + 5
                ] = COLOR_GREEN

            for pixelPos in record.negative_points:
                pixelPos = pixelPos.reshape(-1).astype(np.int32)
                masked_image[
                    pixelPos[1] - 5 : pixelPos[1] + 5, pixelPos[0] - 5 : pixelPos[0] + 5
                ] = COLOR_RED

        frame.segmented_image = masked_image
