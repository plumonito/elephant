import json
import os
import threading
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import cv2
from PIL import Image, ImageTk


class VideoPlayer:
    def __init__(self, root, folder_path):
        self.root = root

        # Init Variables
        self.cap = None
        self.playing = False
        self.frame = None
        self.canvas_width = 200
        self.canvas_height = 200
        self.video_path = False
        self.skip_scrubber_update = False

        self.folder_path = folder_path
        self.video_files = [
            f for f in os.listdir(self.folder_path) if f.endswith(".mp4")
        ]

        if not self.video_files:
            messagebox.showerror("Error", "No .mp4 files found in the selected folder.")
            self.root.quit()
            return

        # Initialize UI components
        self.canvas = tk.Canvas(root)
        self.canvas.pack(fill="both", expand=True)

        # Scrubber Frame
        self.scrubber_frame = tk.Frame(root)
        self.scrubber_frame.pack(fill="x")

        # Canvas for Red Marks Above the Scrubber
        self.marker_canvas = tk.Canvas(self.scrubber_frame, height=20)
        self.marker_canvas.pack(fill="x", expand=True)

        # Scrubber
        self.scrubber = tk.Scale(
            self.scrubber_frame,
            from_=0,
            to=1,
            orient="horizontal",
            command=self.on_scrub,
            showvalue=False,
        )
        self.scrubber.pack(fill="x", expand=True)

        # Control buttons
        self.play_stop_btn = tk.Button(root, text="Play", command=self.toggle_play_pause)
        self.play_stop_btn.pack(side="left")

        self.next_btn = tk.Button(root, text="Next Video", command=self.next_video)
        self.next_btn.pack(side="left")

        self.prev_btn = tk.Button(root, text="Previous Video", command=self.prev_video)
        self.prev_btn.pack(side="left")

        # Bind resizing event to adjust video
        self.canvas.bind("<Configure>", self.on_resize)

        # Bind space bar to play/pause
        self.root.bind("<space>", self.toggle_play_pause)

        # Bind click event on the video
        self.canvas.bind("<Button-1>", self.on_video_click)

        self.current_video_index = 0
        self.load_video(self.current_video_index)
        self.update_window_title()

    def load_video(self, index):
        video_file = self.video_files[index]
        self.video_path = os.path.join(self.folder_path, video_file)
        json_file = os.path.join(
            self.folder_path, os.path.splitext(video_file)[0] + ".json"
        )

        if not os.path.exists(json_file):
            messagebox.showerror("Error", f"JSON file {json_file} not found.")
            self.root.quit()
            return

        with open(json_file, "r") as f:
            time_data = json.load(f)

        self.cap = cv2.VideoCapture(self.video_path)
        self.frame = None

        # Get video properties
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.duration = self.total_frames / self.fps
        self.original_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.original_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Convert JSON time data to frame numbers
        self.marked_frames = [
            (int(t["start_frames"]), int(t["end_frames"])) for t in time_data
        ]

        # Initialize scrubber and draw marks
        self.scrubber.config(to=self.total_frames)
        self.draw_marks_on_scrubber()
        self.update_frame(single_frame=True)

    def draw_marks_on_scrubber(self):
        if not self.scrubber.winfo_width():
            return

        self.marker_canvas.delete("all")  # Clear previous lines

        scrubber_length = self.scrubber.winfo_width()
        for idx, (start_frame, end_frame) in enumerate(self.marked_frames):
            start_pos = (start_frame / self.total_frames) * scrubber_length
            end_pos = (end_frame / self.total_frames) * scrubber_length

            # Create a red line and tag it with a unique identifier
            line_id = f"mark_{idx}"
            self.marker_canvas.create_line(
                start_pos, 20, end_pos, 20, fill="red", width=50, tags=line_id
            )

            # Bind the click event to the line
            self.marker_canvas.tag_bind(
                line_id, "<Button-1>", lambda event, idx=idx: self.on_mark_click(idx)
            )

    def on_mark_click(self, idx):
        """Handles click event on a mark, jumps to the corresponding frame range."""
        start_frame, _ = self.marked_frames[idx]
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        self.update_frame(single_frame=True)
        self.scrubber.set(start_frame)

    def on_video_click(self, event):
        """Handles click event on the video, shows a popup with a dropdown."""
        # Get the click position
        mapped_x = int(event.x / self.scale_factor)
        mapped_y = int(event.y / self.scale_factor)

        # Create a new Toplevel window
        popup = tk.Toplevel(self.root)
        popup.title("Select Name")
        popup.geometry(
            f"+{event.x_root}+{event.y_root}"
        )  # Position the popup near the click

        # List of names for the dropdown
        names = ["Name1", "Name2", "Name3"]  # Modify with actual names

        # Label
        label = tk.Label(popup, text="Choose a name:")
        label.pack(pady=5)

        # Dropdown (Combobox)
        combobox = ttk.Combobox(popup, values=names, state="readonly")
        combobox.pack(pady=5)
        combobox.current(0)  # Set the first name as default

        # Save button
        save_button = tk.Button(
            popup,
            text="Save",
            command=lambda: self.save_and_close(
                popup, combobox.get(), mapped_x, mapped_y
            ),
        )
        save_button.pack(pady=5)

    def save_and_close(self, popup, selected_name, x, y):
        """Saves the click position and name to a JSON file and closes the popup."""
        if selected_name:
            # Save the (x, y) and selected name to a JSON file
            self.save_click_position(x, y, selected_name)

        # Close the popup window
        popup.destroy()

    def save_click_position(self, x, y, name):
        """Saves the click position and name to a JSON file."""
        video_name = os.path.splitext(os.path.basename(self.video_path))[0]
        json_file = os.path.join(self.folder_path, f"{video_name}_points.json")

        data = {"x": x, "y": y, "name": name}

        if os.path.exists(json_file):
            with open(json_file, "r+") as f:
                points = json.load(f)
                points.append(data)
                f.seek(0)
                json.dump(points, f, indent=4)
        else:
            with open(json_file, "w") as f:
                json.dump([data], f, indent=4)

    def toggle_play_pause(self, event=None):
        if self.playing:
            self.playing = False
            self.play_stop_btn.config(text="Play")
        else:
            self.playing = True
            threading.Thread(target=self.update_frame, daemon=True).start()
            self.play_stop_btn.config(text="Stop")

    def on_scrub(self, value):
        if self.skip_scrubber_update:
            self.skip_scrubber_update = False
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(value))
        self.update_frame(single_frame=True)

    def on_resize(self, event):
        # Update canvas dimensions and redraw marks
        self.canvas_width = int(event.width)
        self.canvas_height = int(event.height)
        print('Width: %s', event.width)
        print('Height: %s', event.height)
        # Only update frame if resizing might affect the display
        self.draw_marks_on_scrubber()
        self.update_frame(single_frame=True)

    def update_frame(self, single_frame=False):
        if not self.playing and not single_frame:
            return

        ret, self.frame = self.cap.read()
        if ret:
            self.display_frame(self.frame)
            self.skip_scrubber_update = True
            self.scrubber.set(int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)))
            if not single_frame:
                self.root.after(int(1000 / self.fps), self.update_frame)
        else:
            self.playing = False

    def display_frame(self, frame):
        if self.canvas_width <= 0 or self.canvas_height <= 0:
            return

        self.scale_factor = min(
            self.canvas_width / self.original_width,
            self.canvas_height / self.original_height,
        )
        new_width = max(1, int(self.original_width * self.scale_factor))
        new_height = max(1, int(self.original_height * self.scale_factor))

        frame_resized = cv2.resize(frame, (new_width, new_height))

        cv2image = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)

        self.canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        self.canvas.image = imgtk

    def next_video(self):
        self.current_video_index += 1
        if self.current_video_index >= len(self.video_files):
            self.current_video_index = 0
        self.load_video(self.current_video_index)
        self.update_window_title()

    def prev_video(self):
        self.current_video_index -= 1
        if self.current_video_index < 0:
            self.current_video_index = len(self.video_files) - 1
        self.load_video(self.current_video_index)
        self.update_window_title()

    def on_closing(self):
        self.cap.release()
        self.root.destroy()

    def update_window_title(self):
        self.root.title(
            "Video "
            + str(self.current_video_index + 1)
            + " out of "
            + str(len(self.video_files))
        )


# Initialize the app
folder_path = 'data'
root = tk.Tk()
if folder_path:
    player = VideoPlayer(root, folder_path)
    root.protocol("WM_DELETE_WINDOW", player.on_closing)
    root.mainloop()
