from dataclasses import dataclass
import numpy as np


@dataclass
class Record:
    frame: int
    name: str
    positive_points: np.ndarray  # [point, coords]
    negative_points: np.ndarray  # [point, coords]

    segmentation: np.ndarray | None  # [H,W]


@dataclass
class DatabaseFrame:
    frame: int
    records: dict[str, Record]
    original_image: np.ndarray  # [H,W,3]
    segmented_image: np.ndarray | None  # [H,W,3]


@dataclass
class Database:
    frames: dict[int, DatabaseFrame]

    def add_point(
        self,
        frame: int,
        name: str,
        point: np.ndarray,
        is_positive: bool,
        original_image: np.ndarray,
    ) -> None:
        assert point.shape == (1, 2)

        frame_data = self.frames.get(frame)
        if frame_data is None:
            frame_data = DatabaseFrame(
                frame=frame,
                records={},
                original_image=original_image,
                segmented_image=None,
            )
            self.frames[frame] = frame_data

        record = frame_data.records.get(name)
        if record is None:
            record = Record(
                frame=frame,
                name=name,
                positive_points=np.ndarray((0, 2)),
                negative_points=np.ndarray((0, 2)),
                segmentation=None,
            )
            frame_data.records[name] = record

        # Check if the point cancels out with another point
        other_points = record.negative_points if is_positive else record.positive_points
        point_cancelled = False
        for i, other_point in enumerate(other_points):
            diff = np.linalg.norm(other_point - point)
            if diff < 100:
                other_points = np.delete(other_points, (i), axis=0)
                point_cancelled = True
                break

        if point_cancelled:
            if is_positive:
                record.negative_points = other_points
            else:
                record.positive_points = other_points
        else:
            # Add new point
            if is_positive:
                record.positive_points = np.concatenate([record.positive_points, point])
            else:
                record.negative_points = np.concatenate([record.negative_points, point])
        # Mask needs recalculating
        record.segmentation = None


database = Database(frames={})
