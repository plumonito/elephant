import time

import numpy as np

from ui_components.record import database, DatabaseFrame, Record
from ui_components.sam2_processor import Sam2Processor
from video_scrubber import MainWindow


class BackgroundSegmenter:
    def __init__(self, window: MainWindow) -> None:
        self.should_stop = False
        self.window = window

        self.run_with_sam = True
        if self.run_with_sam:
            self.sam2_ = Sam2Processor()
        else:
            self.sam2_ = None

    def run(self) -> None:
        while not self.should_stop:
            time.sleep(0.5)

            for frame in database.frames.values():
                frame_stale = frame.segmented_image is None
                for record in frame.records.values():
                    if record.segmentation is None:
                        # Segment!
                        frame_stale = True
                        self.segment_record(frame, record)

                if frame_stale:
                    # Combine segmentations into a single image
                    self.update_frame_image(frame)

                    # Trigger UI update
                    self.window.update_ui(frame)

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
        color_green = np.array([0, 255, 0], dtype=np.uint8).reshape(1, 1, 3)
        color_red = np.array([255, 0, 0], dtype=np.uint8).reshape(1, 1, 3)

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
                ] = color_green

            for pixelPos in record.negative_points:
                pixelPos = pixelPos.reshape(-1).astype(np.int32)
                masked_image[
                    pixelPos[1] - 5 : pixelPos[1] + 5, pixelPos[0] - 5 : pixelPos[0] + 5
                ] = color_red

        frame.segmented_image = masked_image
