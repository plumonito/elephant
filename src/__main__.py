import sys
import threading

from PySide6.QtWidgets import (
    QApplication,
)
from queue import SimpleQueue

from background_segmenter import BackgroundSegmenter
from video_scrubber import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    work_queue = SimpleQueue()
    main_win = MainWindow(work_queue)

    segmenter = BackgroundSegmenter(main_win, work_queue)
    segmenter_thread = threading.Thread(target=segmenter.run, daemon=False)
    segmenter_thread.start()

    available_geometry = main_win.screen().availableGeometry()
    main_win.resize(available_geometry.width() // 3, available_geometry.height() // 2)

    def close_event(*args, **kwargs) -> None:
        segmenter.should_stop = True

    main_win.closeEvent = close_event
    main_win.show()
    sys.exit(app.exec())
