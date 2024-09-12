from queue import SimpleQueue

import numpy as np
from PySide6.QtGui import QStatusTipEvent
from PySide6.QtWidgets import QApplication

from database import DatabaseFrame, Record, active_db
from main_window import MainWindow
from sam2_processor import Sam2Processor

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

    def run(self) -> None:
        while not self.should_stop:
            if QApplication.activeWindow() is not None:
                if self.work_queue_.empty():
                    QApplication.sendEvent(
                        QApplication.activeWindow(), QStatusTipEvent("sam2:Ready")
                    )

            try:
                frame_index: int = self.work_queue_.get(block=True, timeout=0.5)
            except:
                continue

            frame = active_db().frames.get(frame_index)

            # Check that frame was not deleted
            if frame is not None:
                if QApplication.activeWindow() is not None:
                    QApplication.sendEvent(
                        QApplication.activeWindow(),
                        QStatusTipEvent(
                            f"sam2:Segmenting {self.work_queue_.qsize() + 1} frames..."
                        ),
                    )
                for record in frame.records.values():
                    if record.segmentation is None:
                        # Segment!
                        self.segment_record(frame, record)

                # Combine segmentations into a single image
                self.update_frame_image(frame)

            # Trigger UI update
            self.window.update_ui(frame_index)

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
        mask_colors = np.array(
            [
                [255, 0, 0],
                [0, 255, 0],
                [0, 0, 255],
                [255, 0, 255],
                [255, 255, 0],
                [0, 255, 255],
            ],
            dtype=np.float32,
        )

        base_alpha = 0.4
        masked_image = frame.original_image.astype(dtype=np.float32, copy=True)
        masked_image *= 0.8
        for i, record in enumerate(frame.records.values()):
            assert record.segmentation is not None
            mask = record.segmentation
            alpha_mask = base_alpha * mask[:, :, np.newaxis]
            color_mask = mask_colors[i].reshape(1, 1, 3) * mask[:, :, np.newaxis]
            masked_image = masked_image * (1 - alpha_mask) + alpha_mask * color_mask
        masked_image = masked_image.astype(np.uint8)

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
