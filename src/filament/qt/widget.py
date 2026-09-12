from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget

from ..core import Engine, OrbitCameraController
from ..types import Backend, Viewport


class FilamentWidget(QWidget):
    """QWidget that owns the standard Filament rendering objects."""

    def __init__(self, parent=None, backend=Backend.AUTO):
        super().__init__(parent)
        self.engine = Engine(backend)
        self.renderer = self.engine.create_renderer()
        self.scene = self.engine.create_scene()
        self.view = self.engine.create_view()
        self.camera = self.engine.create_camera()
        self.view.scene, self.view.camera = self.scene, self.camera
        self.swap_chain = None
        self._controller = OrbitCameraController(self.camera)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(0)

    @property
    def clear_color(self):
        return self.view.clear_color

    @clear_color.setter
    def clear_color(self, value):
        self.view.clear_color = tuple(value)

    @property
    def environment(self):
        return self.scene.environment

    @environment.setter
    def environment(self, value):
        self.scene.environment = value

    def load_model(self, path):
        return self.engine.load_model(path)

    def load(self, path):
        model = self.load_model(path)
        self.scene.add(model)
        return model

    def fit_camera(self):
        self._controller.distance = 5.0
        self._controller._apply()

    def showEvent(self, event):
        super().showEvent(event)
        if self.swap_chain is None:
            self.swap_chain = self.engine.create_swap_chain(native_handle=int(self.winId()))

    def resizeEvent(self, event):
        size = event.size()
        self.view.viewport = Viewport(0, 0, size.width(), size.height())
        super().resizeEvent(event)

    def paintEvent(self, event):
        if self.swap_chain is not None:
            self.renderer.render_frame(self.swap_chain, self.view)
        super().paintEvent(event)

    def closeEvent(self, event):
        self.engine.close()
        super().closeEvent(event)
