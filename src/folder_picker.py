from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
)


class FolderPicker(QWidget):
    # Define a custom signal that will emit the selected folder path
    folder_selected = Signal(str)

    def __init__(self):
        super().__init__()

        # Create the layout and widgets
        self.layout = QVBoxLayout()

        self.label = QLabel("Please select the folder where the videos are stored.")
        self.button = QPushButton("Pick a Folder")

        # Add widgets to the layout
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.button)

        # Set the layout for the window
        self.setLayout(self.layout)

        # Connect the button click to the folder picking function
        self.button.clicked.connect(self.pick_folder)

    def pick_folder(self):
        # Open a folder picker dialog
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")

        # If a folder is selected emit the signal
        if folder:
            self.folder_selected.emit(folder)  # Emit the signal with the folder pat
