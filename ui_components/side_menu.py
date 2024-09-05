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
from ui_components.record import database


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

        # Save status indicator
        self.save_status_label = QLabel("")

        # List widget for records
        self.record_list = QListWidget()
        records_label_layout = QHBoxLayout()
        records_label = QLabel("Records List:")
        records_label_layout.addWidget(records_label)
        records_label_layout.addWidget(self.save_status_label)
        self.layout.addLayout(records_label_layout)
        self.layout.addWidget(self.record_list)

        # Save button at the bottom
        self.save_button = QPushButton("Save Records")
        self.save_button.clicked.connect(self.save_records)
        self.layout.addWidget(self.save_button)

        self.setLayout(self.layout)

        self.records_saved = False  # Initialize save status as False
        self.update_save_status()  # Update the save status indicator

    def load_names(self):
        # Load names from a names.json file
        try:
            with open("names.json", "r") as file:
                names = json.load(file)
                self.name_dropdown.addItems(names)
        except Exception as e:
            print(f"Failed to load names: {e}")

    def load_records(self, file_name):
        pass
        # self.file_name = file_name

        # # Load records from records.json file
        # try:
        #     with open(file_name, "r") as file:
        #         records_data = json.load(file)  # Store records
        #         self.records = [Record(**record) for record in records_data]
        # except Exception as e:
        #     self.records = []  # Default to empty list if loading fails

        # self.display_records()
        # self.records_saved = True
        # self.update_save_status()

    def display_records(self):
        self.record_list.clear()

        # Display each record as a list item with "Display" and "Delete" buttons
        for frame in database.frames.values():
            for record in frame.records.values():
                # Create a custom widget for each list item
                item_widget = QWidget()
                item_layout = QHBoxLayout()

                # Display the record info
                label = QLabel(
                    f"{record.name} at {record.frame} +{record.positive_points.shape[0]} -{record.negative_points.shape[0]}"
                )
                item_layout.addWidget(label)

                # Add a "Display" button for each record
                display_button = QPushButton("Display")
                display_button.clicked.connect(
                    lambda _, r=record: self.display_record_details(r)
                )
                item_layout.addWidget(display_button)

                # Add a "Delete" button for each record
                delete_button = QPushButton("Delete")
                delete_button.clicked.connect(lambda _, r=record: self.delete_record(r))
                item_layout.addWidget(delete_button)

                # Set the layout to the custom widget
                item_widget.setLayout(item_layout)

                # Create a QListWidgetItem
                list_item = QListWidgetItem(self.record_list)
                list_item.setSizeHint(
                    item_widget.sizeHint()
                )  # Set the size hint of the QListWidgetItem

                # Add the custom widget to the QListWidget
                self.record_list.addItem(list_item)
                self.record_list.setItemWidget(list_item, item_widget)

    def display_record_details(self, record):
        print(record)
        self.slider.setValue(record.frame)

    def delete_record(self, record):
        # Remove the record from the list and refresh the UI
        self.records = [r for r in self.records if r != record]
        self.display_records()
        self.records_saved = False
        self.update_save_status()

    def get_selected_name(self):
        return self.name_dropdown.currentText()

    def on_database_changed(self) -> None:
        self.display_records()
        self.records_saved = False
        self.update_save_status()

    def save_records(self):
        if self.file_name:
            try:
                # Write the records to the selected file
                with open(self.file_name, "w") as file:
                    json.dump(
                        [record.__dict__ for record in self.records], file, indent=4
                    )
                self.records_saved = True
                self.update_save_status()
            except Exception as e:
                print(f"Failed to save records: {e}")

    def update_save_status(self):
        if self.records_saved:
            self.save_status_label.setText("All changes saved")
            self.save_status_label.setStyleSheet("color: green;")
        else:
            self.save_status_label.setText("Unsaved Changes")
            self.save_status_label.setStyleSheet("color: red;")
