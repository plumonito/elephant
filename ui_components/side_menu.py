import json

from PySide6.QtWidgets import (
    QVBoxLayout,
    QComboBox,
    QLabel,
    QListWidget,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QListWidgetItem,
)


class SideMenu(QWidget):
    def __init__(self, slider):
        super().__init__()

        self.slider = slider

        # Main Layout
        self.file_name = None
        self.layout = QVBoxLayout()

        # Dropdown for names
        self.name_dropdown = QComboBox()
        self.load_names()  # Load names from the JSON file
        self.layout.addWidget(QLabel("Select Name:"))
        self.layout.addWidget(self.name_dropdown)

        # List widget for points
        self.point_list = QListWidget()
        self.points = []  # Store points loaded from the JSON
        self.layout.addWidget(QLabel("Points List:"))
        self.layout.addWidget(self.point_list)

        # Save button at the bottom
        self.save_button = QPushButton("Save Points")
        self.save_button.clicked.connect(self.save_points)
        self.layout.addWidget(self.save_button)

        self.setLayout(self.layout)

        self.points_saved = False

    def load_names(self):
        # Load names from a names.json file
        try:
            with open("names.json", "r") as file:
                names = json.load(file)
                self.name_dropdown.addItems(names)
        except Exception as e:
            print(f"Failed to load names: {e}")

    def load_points(self, file_name):
        self.file_name = file_name

        # Load points from points.json file
        try:
            with open(file_name, "r") as file:
                self.points = json.load(file)  # Store points
        except Exception as e:
            self.points = []  # Default to empty list if loading fails

        self.display_points()
        self.points_saved = True

    def display_points(self):
        self.point_list.clear()

        # Display each point as a list item with a "Display" button
        for point in self.points:
            # Create a custom widget for each list item
            item_widget = QWidget()
            item_layout = QHBoxLayout()

            # Display the point info (x, y, name)
            label = QLabel(
                f"Point: Name: {point['name']} Frame: {point['frame']}"
            )
            item_layout.addWidget(label)

            # Add a "Display" button for each point
            display_button = QPushButton("Display")
            display_button.clicked.connect(
                lambda _, p=point: self.display_point_details(p)
            )
            item_layout.addWidget(display_button)

            # Set the layout to the custom widget
            item_widget.setLayout(item_layout)

            # Create a QListWidgetItem
            list_item = QListWidgetItem(self.point_list)
            list_item.setSizeHint(
                item_widget.sizeHint()
            )  # Set the size hint of the QListWidgetItem

            # Add the custom widget to the QListWidget
            self.point_list.addItem(list_item)
            self.point_list.setItemWidget(list_item, item_widget)

    def display_point_details(self, point):
        print(point)
        self.slider.setValue(point['frame'])

    def get_selected_name(self):
        return self.name_dropdown.currentText()

    def add_point(self, pixel_pos, frame_index):
        data = {
            "x": int(pixel_pos[0][0]),
            "y": int(pixel_pos[0][1]),
            "name": self.get_selected_name(),
            "frame": frame_index
        }
        self.points.append(data)
        self.display_points()
        self.points_saved = False

    def save_points(self):
        if self.file_name:
            try:
                # Write the points to the selected file
                with open(self.file_name, 'w') as file:
                    json.dump(self.points, file, indent=4)
                self.points_saved = True
            except Exception as e:
                print(f"Failed to save points: {e}")
