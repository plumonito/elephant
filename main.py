import sys
import threading

from PySide6.QtWidgets import (
    QApplication,
)

from ui_components.record import database
from background_segmenter import BackgroundSegmenter
from video_scrubber import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    main_win = MainWindow()

    segmenter = BackgroundSegmenter(main_win)
    segmenter_thread = threading.Thread(target=segmenter.run, daemon=False)
    segmenter_thread.start()

    available_geometry = main_win.screen().availableGeometry()
    main_win.resize(available_geometry.width() / 3, available_geometry.height() / 2)
    main_win.show()
    sys.exit(app.exec())
