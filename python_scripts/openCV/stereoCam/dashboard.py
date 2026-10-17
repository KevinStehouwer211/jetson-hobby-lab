"""One screen-sized Qt dashboard; no independent OpenCV control windows."""
from collections import deque
import os
import time

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator


class ImageView(QtWidgets.QWidget):
    roiSelected = QtCore.Signal(tuple)

    def __init__(self):
        super().__init__()
        self.image = QtGui.QImage()
        self.selecting = False
        self.start = None
        self.end = None
        self.setMinimumSize(40, 40)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def set_rgb(self, rgb):
        rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        h, w = rgb.shape[:2]
        fmt = QtGui.QImage.Format_RGB888 if rgb.shape[2] == 3 else QtGui.QImage.Format_RGBA8888
        self.image = QtGui.QImage(rgb.data, w, h, rgb.strides[0], fmt).copy()
        self.update()

    def image_rect(self):
        if self.image.isNull():
            return QtCore.QRect()
        size = self.image.size().scaled(self.size(), QtCore.Qt.KeepAspectRatio)
        return QtCore.QRect((self.width()-size.width())//2, (self.height()-size.height())//2,
                            size.width(), size.height())

    def native_point(self, point):
        rect = self.image_rect()
        if not rect.width() or not rect.height():
            return None
        x = np.clip((point.x()-rect.x())*self.image.width()/rect.width(), 0, self.image.width()-1)
        y = np.clip((point.y()-rect.y())*self.image.height()/rect.height(), 0, self.image.height()-1)
        return int(round(x)), int(round(y))

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor('#111820'))
        if not self.image.isNull():
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            painter.drawImage(self.image_rect(), self.image)
        if self.selecting and self.start is not None and self.end is not None:
            painter.setPen(QtGui.QPen(QtGui.QColor('#37b9ff'), 2, QtCore.Qt.DashLine))
            painter.drawRect(QtCore.QRect(self.start, self.end).normalized())

    def mousePressEvent(self, event):
        if self.selecting and event.button() == QtCore.Qt.LeftButton and self.image_rect().contains(event.position().toPoint()):
            self.start = event.position().toPoint()
            self.end = self.start

    def mouseMoveEvent(self, event):
        if self.selecting and self.start is not None:
            self.end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.selecting and self.start is not None:
            first = self.native_point(self.start)
            last = self.native_point(event.position().toPoint())
            if first is not None and last is not None:
                x, y = min(first[0], last[0]), min(first[1], last[1])
                w, h = abs(first[0]-last[0])+1, abs(first[1]-last[1])+1
                if w > 2 and h > 2:
                    self.roiSelected.emit((x, y, w, h))
            self.start = self.end = None
            self.update()


class HSVPanel(QtWidgets.QGroupBox):
    def __init__(self, title, values, maxima):
        super().__init__(title)
        self.sliders = {}
        self.spinboxes = {}
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(8, 16, 8, 6)
        layout.setVerticalSpacing(2)
        for row, (name, maximum) in enumerate(maxima.items()):
            label = QtWidgets.QLabel(name)
            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            spin = QtWidgets.QSpinBox()
            slider.setRange(0, maximum)
            spin.setRange(0, maximum)
            slider.setValue(values[name])
            spin.setValue(values[name])
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(slider.setValue)
            slider.setMinimumWidth(20)
            spin.setMaximumWidth(60)
            layout.addWidget(label, row, 0)
            layout.addWidget(slider, row, 1)
            layout.addWidget(spin, row, 2)
            self.sliders[name] = slider
            self.spinboxes[name] = spin
        layout.setColumnStretch(1, 1)

    def values(self):
        return {name: slider.value() for name, slider in self.sliders.items()}


class LivePlot:
    def __init__(self, fps):
        self.interval = 1/fps
        self.last_draw = 0.
        self.history = deque(maxlen=150)
        self.current = None
        self.halfwidth = None
        self.figure = Figure(figsize=(6, 6), dpi=100, facecolor='white')
        self.canvas = FigureCanvasAgg(self.figure)
        self.axes = self.figure.add_subplot(111, projection='3d')
        self.figure.subplots_adjust(left=.03, right=.87, bottom=.07, top=.95)
        self.axes.set(xlabel='X (m)', ylabel='Y (m)', zlabel='Z (m)')
        self.axes.view_init(elev=float(np.degrees(np.arctan(1/np.sqrt(2)))), azim=-45)
        self.axes.set_proj_type('ortho')
        self.axes.set_box_aspect((1, 1, 1))
        self.axes.tick_params(labelsize=9, pad=1)
        for axis in [self.axes.xaxis, self.axes.yaxis, self.axes.zaxis]:
            axis.set_major_locator(MaxNLocator(4))
        self.trail, = self.axes.plot([], [], [], color='#8cbfc6', lw=1.5)
        self.marker, = self.axes.plot([], [], [], 'o', color='#008a9c', markersize=9)
        self.bounds = [self.axes.plot([], [], [], color='#008a9c', alpha=.6, lw=2)[0] for _ in range(3)]

    def clear(self):
        self.history.clear()
        self.last_draw = 0.

    def update(self, location, new_pair):
        self.current = None if location is None else np.array(location.xyz)
        self.halfwidth = None if location is None else np.array(location.halfwidth95)
        if new_pair:
            if self.current is not None:
                self.history.append(self.current.copy())
            elif self.history and np.isfinite(self.history[-1]).all():
                self.history.append(np.full(3, np.nan))

    def render(self, force=False):
        if not force and time.perf_counter()-self.last_draw < self.interval:
            return None
        self.last_draw = time.perf_counter()
        points = np.array(self.history).reshape(-1, 3)
        self.trail.set_data_3d(*points.T)
        if self.current is None:
            self.marker.set_data_3d([], [], [])
            for line in self.bounds:
                line.set_data_3d([], [], [])
        else:
            self.marker.set_data_3d(*self.current.reshape(3, 1))
            for axis, line in enumerate(self.bounds):
                ends = np.tile(self.current, (2, 1))
                ends[:, axis] += np.array([-1, 1])*self.halfwidth[axis]
                line.set_data_3d(*ends.T)
        finite = points[np.isfinite(points).all(axis=1)]
        if self.current is not None:
            finite = np.vstack([finite, self.current-self.halfwidth, self.current+self.halfwidth])
        center = (finite.min(0)+finite.max(0))/2 if len(finite) else np.zeros(3)
        radius = max(.15, float(np.ptp(finite, axis=0).max())*.65) if len(finite) else .5
        self.axes.set(xlim=(center[0]-radius, center[0]+radius),
                      ylim=(center[1]-radius, center[1]+radius),
                      zlim=(center[2]-radius, center[2]+radius))
        self.canvas.draw()
        return np.asarray(self.canvas.buffer_rgba()).copy()


class DashboardWindow(QtWidgets.QMainWindow):
    closed = False

    def closeEvent(self, event):
        self.closed = True
        super().closeEvent(event)


class StereoDashboard:
    def __init__(self, settings, maxima, rotated, plot_fps=6., window_size=None, mode='color'):
        face_mode = mode == 'face'
        # OpenCV wheels can export their Qt5 plugin path; this UI uses PySide6.
        if '/cv2/' in os.environ.get('QT_QPA_PLATFORM_PLUGIN_PATH', ''):
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.PluginsPath)
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        self.window = DashboardWindow()
        self.window.setWindowTitle('StereoCam — live '+('face' if face_mode else 'red')+' tracking and 3D reconstruction')
        self.window.setStyleSheet('''
            QMainWindow, QWidget#central { background: #f1f4f8; color: #182c3d; }
            QGroupBox { background: white; border: 1px solid #cbd5df; border-radius: 6px;
                        font-weight: bold; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QPushButton { padding: 6px 10px; border: 1px solid #c3ced9; border-radius: 4px; background: white; }
            QPushButton:hover { background: #e3f1f3; }
            QSpinBox { background: #f5f7fa; padding: 1px; font-weight: normal; }
            QSlider::groove:horizontal { height: 5px; background: #dae3eb; border-radius: 2px; }
            QSlider::handle:horizontal { width: 13px; margin: -4px 0; background: #008a9c; border-radius: 6px; }
        ''')
        central = QtWidgets.QWidget()
        central.setObjectName('central')
        self.window.setCentralWidget(central)
        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(10, 6, 10, 8)
        outer.setSpacing(5)
        self.actions = deque()
        self.shortcuts = []
        toolbar = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel('STEREO CAM')
        title.setStyleSheet('font-size: 18px; font-weight: bold; color: #007e90;')
        toolbar.addWidget(title)
        toolbar.addStretch()
        for name, key in [('Save ROIs · S' if face_mode else 'Save HSV · S', 's'), ('Select ROIs · R', 'r'), ('Clear ROIs · C', 'c'),
                          ('Clear trail · T', 't'), ('Quit · Q', 'q')]:
            button = QtWidgets.QPushButton(name)
            button.clicked.connect(lambda checked=False, k=key: self.actions.append(k))
            toolbar.addWidget(button)
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(key.upper()), self.window)
            shortcut.activated.connect(lambda k=key: self.actions.append(k))
            self.shortcuts.append(shortcut)
        shortcut = QtGui.QShortcut(QtGui.QKeySequence('Escape'), self.window)
        shortcut.activated.connect(lambda: self.actions.append('q'))
        self.shortcuts.append(shortcut)
        outer.addLayout(toolbar)
        self.status = QtWidgets.QLabel('Waiting for both cameras…')
        self.status.setStyleSheet('font-size: 14px; font-weight: bold;')
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        body = QtWidgets.QHBoxLayout()
        body.setSpacing(10)
        outer.addLayout(body, 1)
        left = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(left)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(5)
        self.cameras, self.masks, self.controls = [], [], []
        for c, name in enumerate(['cam1 · Dashcam', 'cam2 · Dofbot']):
            group = QtWidgets.QGroupBox(name)
            box = QtWidgets.QVBoxLayout(group)
            box.setContentsMargins(4, 15, 4, 4)
            image = ImageView()
            image.roiSelected.connect(lambda roi, camera=c: self.roi_selected(camera, roi))
            box.addWidget(image)
            grid.addWidget(group, 0, c)
            self.cameras.append(image)
            mask_group = QtWidgets.QGroupBox('Detected face regions' if face_mode else 'Red mask')
            box = QtWidgets.QVBoxLayout(mask_group)
            box.setContentsMargins(4, 12, 4, 4)
            mask = ImageView()
            mask.setMinimumHeight(35)
            box.addWidget(mask)
            grid.addWidget(mask_group, 1, c)
            self.masks.append(mask)
            if face_mode:
                panel = QtWidgets.QGroupBox('Face tracking · '+name)
                info = QtWidgets.QVBoxLayout(panel)
                text = QtWidgets.QLabel('Haar face detection + eye overlays\n\n'
                                        'Both cameras must see the same face.\n'
                                        'R: drag a search region to isolate one face.\n'
                                        'XYZ estimates the detected face-box centre.\n'
                                        'Blue circles mark detected eyes.')
                text.setWordWrap(True)
                info.addWidget(text)
            else:
                panel = HSVPanel('HSV · '+name, settings[c], maxima)
                self.controls.append(panel)
            grid.addWidget(panel, 2, c)
        grid.setRowStretch(0, 5)
        grid.setRowStretch(1, 2)
        grid.setRowStretch(2, 0)
        for c in range(2):
            grid.setColumnStretch(c, 1)
        body.addWidget(left, 3)
        right = QtWidgets.QWidget()
        box = QtWidgets.QVBoxLayout(right)
        box.setContentsMargins(0, 0, 0, 0)
        cards = QtWidgets.QHBoxLayout()
        self.readouts = []
        for axis, color in zip('XYZ', ['#bd423b', '#29805d', '#2768b6']):
            card = QtWidgets.QGroupBox(axis+' · metres')
            layout = QtWidgets.QVBoxLayout(card)
            value = QtWidgets.QLabel('—')
            value.setAlignment(QtCore.Qt.AlignCenter)
            value.setMinimumWidth(0)
            value.setStyleSheet(f'color: {color}; font-weight: bold;')
            value.setFont(QtGui.QFont('Sans Serif', 25, QtGui.QFont.Bold))
            layout.addWidget(value)
            cards.addWidget(card, 1)
            self.readouts.append(value)
        box.addLayout(cards)
        self.uncertainty = QtWidgets.QLabel('XYZ unavailable until a usable match is visible in both views.')
        self.uncertainty.setWordWrap(True)
        box.addWidget(self.uncertainty)
        self.frame_label = QtWidgets.QLabel('+Z up · reference fall frame' if rotated else 'Original calibration coordinate frame')
        box.addWidget(self.frame_label)
        group = QtWidgets.QGroupBox('Live 3D · isometric view')
        plot_layout = QtWidgets.QVBoxLayout(group)
        plot_layout.setContentsMargins(0, 14, 0, 0)
        self.plot_view = ImageView()
        plot_layout.addWidget(self.plot_view)
        box.addWidget(group, 1)
        note = QtWidgets.QLabel('Recent accepted positions · units: m\n95% bounds assume pixel noise; timing/calibration errors are excluded.')
        note.setWordWrap(True)
        box.addWidget(note)
        body.addWidget(right, 2)
        left.setMinimumWidth(0)
        right.setMinimumWidth(0)
        self.hint = QtWidgets.QLabel('FaceTracking.py detection method · XYZ is a face-box-centre estimate, not an anatomical landmark.'
                                    if face_mode else 'Eight HSV controls per camera, matching HSV.py. Both hue masks are combined.')
        self.hint.setWordWrap(True)
        outer.addWidget(self.hint)
        self.plot = LivePlot(plot_fps)
        self.pending_rois = set()
        screen = self.app.primaryScreen().availableGeometry()
        if window_size:
            self.window.resize(*window_size)
            self.window.show()
        else:
            self.window.setGeometry(screen)
            self.window.showMaximized()
        self.app.processEvents()
        self.plot_view.set_rgb(self.plot.render(force=True))

    def poll(self):
        self.app.processEvents()
        actions = list(self.actions)
        self.actions.clear()
        if self.window.closed:
            actions.append('q')
        return actions

    def settings(self):
        return [control.values() for control in self.controls]

    def roi_selected(self, camera, roi):
        self.actions.append(('roi', camera, roi))
        self.pending_rois.discard(camera)
        self.cameras[camera].selecting = False
        self.cameras[camera].unsetCursor()
        if not self.pending_rois:
            self.hint.setText('ROIs selected. C clears them; S saves settings.')

    def select_rois(self):
        cancel = bool(self.pending_rois)
        self.pending_rois = set() if cancel else {0, 1}
        for camera in self.cameras:
            camera.selecting = not cancel
            camera.start = camera.end = None
            camera.setCursor(QtCore.Qt.ArrowCursor if cancel else QtCore.Qt.CrossCursor)
        self.hint.setText('Drag a rectangle on each camera image. R cancels selection.' if not cancel else 'ROI selection cancelled.')

    def clear_rois(self):
        self.pending_rois.clear()
        for camera in self.cameras:
            camera.selecting = False
            camera.start = camera.end = None
            camera.unsetCursor()
        self.hint.setText('Search ROIs cleared.')

    def update(self, annotated_pair, masks, location, status, rates, skew, new_pair):
        # annotate() contains a 100-pixel export banner; the dashboard has native labels instead.
        width = annotated_pair.shape[1]//2
        for c in range(2):
            bgr = annotated_pair[100:, c*width:(c+1)*width]
            self.cameras[c].set_rgb(bgr[:, :, ::-1])
            self.masks[c].set_rgb(np.repeat(masks[c][:, :, None], 3, axis=2))
        self.status.setText(f'{status}  |  Dashcam {rates[0]:.1f} fps · Dofbot {rates[1]:.1f} fps' +
                            (f'  |  host arrival gap {skew:.1f} ms' if skew is not None else '  |  replay'))
        self.status.setStyleSheet('font-size: 14px; font-weight: bold; color: '+('#007e70' if location is not None else '#ae6616')+';')
        for i, label in enumerate(self.readouts):
            label.setText(f'{location.xyz[i]:+.3f}' if location is not None else '—')
            font = label.font()
            for size in range(27, 13, -1):
                font.setPointSize(size)
                if QtGui.QFontMetrics(font).horizontalAdvance(label.text()) <= max(40, label.width()-6):
                    break
            label.setFont(font)
        self.uncertainty.setText(('Conditional 95% ± XYZ: '+', '.join(f'{v*1000:.1f}' for v in location.halfwidth95)+
                                 f' mm · fit {location.rms_px:.2f} px') if location is not None else 'No current 3D location — waiting for a usable stereo match.')
        self.plot.update(location, new_pair)
        rendered = self.plot.render()
        if rendered is not None:
            self.plot_view.set_rgb(rendered)
        self.app.processEvents()

    def save_preview(self, path):
        self.plot_view.set_rgb(self.plot.render(force=True))
        self.app.processEvents()
        return self.window.grab().save(str(path))

    def close(self):
        self.window.close()
        self.app.processEvents()
