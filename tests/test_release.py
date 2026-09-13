import filament as fl
import pytest


class NativeRecorder:
    backend = int(fl.Backend.VULKAN)

    def __init__(self):
        self.calls = []
        self.next_handle = 1

    def _create(self, kind):
        value = self.next_handle
        self.next_handle += 1
        self.calls.append(("create", kind, value))
        return value

    def create_renderer(self): return self._create("renderer")
    def create_scene(self): return self._create("scene")
    def create_view(self): return self._create("view")
    def create_camera(self): return self._create("camera")
    def create_headless_swap_chain(self, width, height): return self._create("swap_chain")
    def create_window_swap_chain(self, handle): return self._create("swap_chain")
    def destroy(self, handle, kind): self.calls.append(("destroy", kind, handle))
    def begin_frame(self, renderer, swap): self.calls.append(("begin", renderer, swap)); return True
    def render(self, renderer, view): self.calls.append(("render", renderer, view))
    def end_frame(self, renderer): self.calls.append(("end", renderer))
    def view_set_scene(self, view, scene): self.calls.append(("scene", view, scene))
    def view_set_camera(self, view, camera): self.calls.append(("camera", view, camera))
    def view_set_viewport(self, view, x, y, width, height): self.calls.append(("viewport", width, height))
    def camera_look_at(self, camera, eye, target, up): self.calls.append(("look_at", camera))
    def camera_set_perspective(self, camera, *projection): self.calls.append(("perspective", camera))
    def close(self): self.calls.append(("close",))


def native_engine():
    engine = fl.Engine(native=False)
    engine._native = NativeRecorder()
    return engine


def test_version_is_stable():
    assert fl.__version__ == "1.0.0"


def test_core_calls_are_forwarded_to_native_runtime():
    engine = native_engine()
    renderer, scene = engine.create_renderer(), engine.create_scene()
    view, camera = engine.create_view(), engine.create_camera()
    swap = engine.create_swap_chain(width=32, height=24, headless=True)
    view.scene, view.camera = scene, camera
    view.viewport = fl.Viewport(0, 0, 32, 24)
    camera.look_at((0, 0, 2), (0, 0, 0))
    camera.set_perspective(45, 4 / 3, 0.1, 100)
    renderer.render_frame(swap, view)
    names = [call[0] for call in engine._native.calls]
    assert {"scene", "camera", "viewport", "look_at", "perspective", "begin", "render", "end"} <= set(names)
    engine.close()
    assert engine._native.calls[-1] == ("close",)


def test_release_validation():
    engine = fl.Engine(native=False)
    with pytest.raises(ValueError):
        fl.RenderTarget(engine, 0, 10)
    with pytest.raises(ValueError):
        fl.VertexBuffer(engine, 0)
    with pytest.raises(ValueError):
        fl.Mesh(engine, [[0, 0, 0]], [1])
    with pytest.raises(TypeError):
        engine.create_view().scene = object()
    engine.close()


def test_closing_native_dependencies_cannot_leave_dangling_handles():
    engine = native_engine()
    view, camera, scene = engine.create_view(), engine.create_camera(), engine.create_scene()
    view.camera, view.scene = camera, scene
    with pytest.raises(ValueError):
        view.camera = None
    scene.close()
    assert view.scene is None and view.alive
    camera.close()
    assert not view.alive

    renderer = engine.create_renderer()
    swap = engine.create_swap_chain(width=4, height=4, headless=True)
    assert renderer.begin_frame(swap)
    with pytest.raises(RuntimeError):
        swap.close()
    renderer.end_frame()
    swap.close()
    engine.close()


def test_frame_submission_rejects_another_engine():
    first, second = fl.Engine(native=False), fl.Engine(native=False)
    renderer = first.create_renderer()
    with pytest.raises(ValueError):
        renderer.begin_frame(second.create_swap_chain(width=4, height=4, headless=True))
    assert renderer.begin_frame(first.create_swap_chain(width=4, height=4, headless=True))
    with pytest.raises(ValueError):
        renderer.render(second.create_view())
    renderer.end_frame()
    first.close()
    second.close()
