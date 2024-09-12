import sys
import threading
from queue import SimpleQueue
from PySide6.QtWidgets import QApplication, QFileDialog
from background_segmenter import BackgroundSegmenter
from main_window import MainWindow


if __name__ == "__main__":
    # Create the application instance
    app = QApplication(sys.argv)

    videos_path = QFileDialog.getExistingDirectory(
        None, "Select the folder with videos"
    )

    # Create the work queue and main window
    work_queue = SimpleQueue()
    main_win = MainWindow(work_queue, videos_path)

    # Initialize and start the background segmenter thread
    segmenter = BackgroundSegmenter(main_win, work_queue)
    segmenter_thread = threading.Thread(target=segmenter.run, daemon=False)
    segmenter_thread.start()

    # Resize and display the main window
    available_geometry = main_win.screen().availableGeometry()
    main_win.resize(available_geometry.width() // 3, available_geometry.height() // 2)

    # Show the main application window
    main_win.show()
    ret_value = app.exec()

    segmenter.should_stop = True

    sys.exit(ret_value)
