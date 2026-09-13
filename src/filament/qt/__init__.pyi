from typing import Any, Optional
from PySide6.QtWidgets import QWidget
from filament import Backend, Camera, Engine, Environment, Model, Renderer, Scene, SwapChain, View

class FilamentWidget(QWidget):
    engine: Engine
    renderer: Renderer
    scene: Scene
    view: View
    camera: Camera
    swap_chain: Optional[SwapChain]
    clear_color: tuple
    environment: Optional[Environment]
    def __init__(self, parent: Optional[QWidget] = ..., backend: Backend = ...) -> None: ...
    def load_model(self, path: Any) -> Model: ...
    def load(self, path: Any) -> Model: ...
    def fit_camera(self) -> None: ...
