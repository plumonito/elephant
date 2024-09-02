import json
import logging
from pathlib import Path

import cv2
from decord import VideoReader
from line_profiler import profile
from tqdm import tqdm

logger = logging.getLogger(__name__)


@profile
def detect_motion(
        video_path: Path,
        movement_threshold=5000,
        min_contour_area=500,
        step_sec=3,
        debug=False,
        cut_top=None,
        cut_bottom=None,
        cut_right=None,
        cut_left=None,
):
    # Open the video file
    vr = VideoReader(str(video_path))

    fps = 28
    frame_step = int(
        fps * step_sec
    )  # Number of frames to skip to achieve the desired interval

    frame_count = len(vr)
    iter_count = frame_count // frame_step

    motion_periods = []

    frame1 = vr[0]
    frame_index = 0

    width = frame1.shape[0]
    height = frame1.shape[1]
    crop_x = int(cut_left / 100 * width if cut_left else 0)
    crop_y = int(cut_top / 100 * height if cut_top else 0)
    crop_xx = width - int(cut_right / 100 * width if cut_right else 0)
    crop_yy = height - int(cut_bottom / 100 * height if cut_bottom else 0)

    def frame_preprocess(frame):
        frame = frame.asnumpy()
        frame = frame[crop_x:crop_xx, crop_y:crop_yy]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        down_scale = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5)
        return down_scale

    frame1 = frame_preprocess(frame1)

    motion_start_str = None
    motion_start = None

    for _ in tqdm(range(iter_count)):
        # Skip to the next frame after the desired interval
        frame2 = vr[frame_index + frame_step]

        frame2 = frame_preprocess(frame2)

        diff = cv2.absdiff(frame1, frame2)
        _, threshold_binary_image = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
        # dilated = cv2.dilate(threshold_binary_image, None, iterations=3)
        dilated = threshold_binary_image

        # if debug:
        #     cv2.imshow("diff", diff)
        #     cv2.imshow("down_scale1", down_scale1)
        #     cv2.imshow("down_scale2", down_scale2)
        #     cv2.waitKey(0)
        #     cv2.destroyAllWindows()

        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Calculate the total movement
        total_movement = sum(
            cv2.contourArea(c)
            for c in contours
            if cv2.contourArea(c) > min_contour_area
        )

        # Convert frame count to timestamp
        timestamp = frame_index / fps
        timestamp_str = f"{int(timestamp // 60)}:{int(timestamp % 60):02}"

        # Detect motion start and end times
        if total_movement > movement_threshold:
            if motion_start_str is None:
                motion_start_str = timestamp_str  # Start a new motion period
                motion_start = frame_index  # Start a new motion period

                if debug:
                    # Create a blank image with the same dimensions as the dilated image
                    contour_img = cv2.cvtColor(
                        dilated, cv2.COLOR_GRAY2BGR
                    )  # Convert to BGR to draw colored contours
                    # Draw the contours on the blank image
                    cv2.drawContours(
                        contour_img, contours, -1, (0, 255, 0), 2
                    )  # Green contours with thickness of 2
                    # Display the image with contours
                    cv2.imshow("Contours", contour_img)
                    cv2.imshow("down_scale1", frame1)
                    cv2.imshow("frame1", frame1)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
        else:
            if motion_start_str is not None:
                motion_periods.append(
                    {
                        "start": motion_start_str,
                        "end": timestamp_str,
                        "start_frames": motion_start,
                        "end_frames": frame_index,
                    }
                )
                motion_start_str = None  # Reset motion start
                motion_start = None

        # Update the frame and frame count
        frame1 = frame2
        frame_index += frame_step

    # If motion was ongoing at the end of the video
    if motion_start_str is not None:
        timestamp = frame_index / fps
        motion_periods.append(
            {
                "start": motion_start_str,
                "end": f"{int(timestamp // 60)}:{int(timestamp % 60):02}",
                "start_frames": motion_start,
                "end_frames": frame_index,
            }
        )

    # Save the motion periods to a JSON file
    output_json = video_path.with_suffix(".json")
    with open(output_json, "w") as f:
        json.dump(motion_periods, f, indent=4)

    print(f"Motion detection complete. Motion periods saved to {output_json}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    folder_path = Path("data")
    video_files = [f for f in folder_path.glob("*.mp4")]

    if len(video_files) == 0:
        print("No Videos found!")

    for file in video_files:
        logger.info("Processing: %s", file)
        assert file.exists()
        detect_motion(
            file,
            movement_threshold=1,
            min_contour_area=1000,
            step_sec=4,
            debug=False,
            cut_left=35,
            cut_right=15,
            cut_top=40,
        )


if __name__ == "__main__":
    main()
