import sys
import threading
from queue import SimpleQueue
from PySide6.QtWidgets import QApplication
from background_segmenter import BackgroundSegmenter
from main_window import MainWindow
from folder_picker import FolderPicker


def open_main_app(folder_path, folder_picker_window) -> None:
    """
    Function to open the main app once a folder is selected in FolderPicker.
    """
    # Close the folder picker window (optional, if you want to hide it)
    folder_picker_window.close()

    # Create the work queue and main window
    work_queue = SimpleQueue()
    main_win = MainWindow(work_queue, folder_path)

    # Initialize and start the background segmenter thread
    segmenter = BackgroundSegmenter(main_win, work_queue)
    segmenter_thread = threading.Thread(target=segmenter.run, daemon=False)
    segmenter_thread.start()

    # Resize and display the main window
    available_geometry = main_win.screen().availableGeometry()
    main_win.resize(available_geometry.width() // 3, available_geometry.height() // 2)

    # Show the main application window
    main_win.show()


if __name__ == "__main__":
    # Create the application instance
    app = QApplication(sys.argv)

    # Create the FolderPicker window
    window = FolderPicker()
    window.setWindowTitle("Select Video Folder")
    window.resize(400, 50)

    # Connect the folder_selected signal to the open_main_app function
    # We now also pass the 'window' instance to allow closing the folder picker
    window.folder_selected.connect(lambda folder: open_main_app(folder, window))

    # Show the folder picker window
    window.show()

    # Start the event loop
    sys.exit(app.exec())
