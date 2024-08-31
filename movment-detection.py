from tqdm import tqdm
import logging
from tkinter import filedialog
import cv2
import json
from pathlib import Path

logger = logging.getLogger(__name__)


def detect_motion(
    video_path,
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
    cap = cv2.VideoCapture(video_path)

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_step = int(
        fps * step_sec
    )  # Number of frames to skip to achieve the desired interval

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    iter_count = frame_count // frame_step

    motion_periods = []

    ret, frame1 = cap.read()
    frame_index = 0

    motion_start_str = None
    motion_start = None

    for _ in tqdm(range(iter_count)):
        if not ret:
            break

        # Skip to the next frame after the desired interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index + frame_step)
        ret, frame2 = cap.read()
        if not ret:
            break

        frame1_resized = frame1
        frame2_resized = frame2

        if cut_top:
            frame1_resized = resize_by_cutting(frame1_resized, percentage=cut_top)
            frame2_resized = resize_by_cutting(frame2_resized, percentage=cut_top)
        if cut_right:
            frame1_resized = resize_by_cutting(
                frame1_resized, percentage=cut_right, side="right"
            )
            frame2_resized = resize_by_cutting(
                frame2_resized, percentage=cut_right, side="right"
            )
        if cut_left:
            frame1_resized = resize_by_cutting(
                frame1_resized, percentage=cut_left, side="left"
            )
            frame2_resized = resize_by_cutting(
                frame2_resized, percentage=cut_left, side="left"
            )
        if cut_bottom:
            frame1_resized = resize_by_cutting(
                frame1_resized, percentage=cut_bottom, side="bottom"
            )
            frame2_resized = resize_by_cutting(
                frame2_resized, percentage=cut_bottom, side="bottom"
            )

        # Calculate the absolute difference between the two frames
        gray1 = cv2.cvtColor(frame1_resized, cv2.COLOR_BGR2GRAY)
        down_scale1 = cv2.resize(gray1, (0, 0), fx=0.5, fy=0.5)
        gray2 = cv2.cvtColor(frame2_resized, cv2.COLOR_BGR2GRAY)
        down_scale2 = cv2.resize(gray2, (0, 0), fx=0.5, fy=0.5)

        diff = cv2.absdiff(down_scale1, down_scale2)
        _, threshold_binary_image = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(threshold_binary_image, None, iterations=3)

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
                    cv2.imshow("down_scale1", down_scale1)
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
                        "end_frames": frame_count,
                    }
                )
                motion_start_str = None  # Reset motion start
                motion_start = None

        # Update the frame and frame count
        frame1 = frame2
        frame_index += frame_step

    # If motion was ongoing at the end of the video
    if motion_start_str is not None:
        timestamp = frame_count / fps
        motion_periods.append(
            {
                "start": motion_start_str,
                "end": f"{int(timestamp // 60)}:{int(timestamp % 60):02}",
                "start_frames": motion_start,
                "end_frames": frame_count,
            }
        )

    # Release the video capture object
    cap.release()

    # Save the motion periods to a JSON file
    output_json = video_path.replace(".mp4", ".json")
    with open(output_json, "w") as f:
        json.dump(motion_periods, f, indent=4)

    print(f"Motion detection complete. Motion periods saved to {output_json}")


def resize_by_cutting(frame, percentage=20, side="top"):
    height, width = frame.shape[:2]
    cut_size = percentage / 100

    if side.lower() == "top":
        # Calculate the height to cut and crop the top
        cut_height = int(height * cut_size)
        cropped_frame = frame[cut_height:, :]
    elif side.lower() == "bottom":
        # Calculate the height to cut and crop the bottom
        cut_height = int(height * cut_size)
        cropped_frame = frame[:-cut_height, :]
    elif side.lower() == "left":
        # Calculate the width to cut and crop the left
        cut_width = int(width * cut_size)
        cropped_frame = frame[:, cut_width:]
    elif side.lower() == "right":
        # Calculate the width to cut and crop the right
        cut_width = int(width * cut_size)
        cropped_frame = frame[:, :-cut_width]
    else:
        raise ValueError(
            "Invalid side. Choose from 'top', 'bottom', 'left', or 'right'."
        )

    return cropped_frame


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # Usage
    folder_path = Path(
        filedialog.askdirectory(title="Select Folder Containing MP4 and JSON Files")
    )
    video_files = [f for f in folder_path.glob("*.mp4")]

    for file in video_files:
        logger.info(f"Processing: {file}")
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
