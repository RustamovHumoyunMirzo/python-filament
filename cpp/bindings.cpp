#include <filament/Camera.h>
#include <filament/Engine.h>
#include <filament/Renderer.h>
#include <filament/Scene.h>
#include <filament/SwapChain.h>
#include <filament/View.h>
#include <filament/Viewport.h>
#include <math/vec3.h>
#include <pybind11/pybind11.h>
#include <utils/EntityManager.h>

#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <utility>
#include <vector>

namespace py = pybind11;

namespace {
using Backend = filament::Engine::Backend;

Backend to_backend(int value) {
    switch (value) {
        case 0: return Backend::DEFAULT;
        case 1: return Backend::OPENGL;
        case 2: return Backend::VULKAN;
        case 3: return Backend::METAL;
        default: throw std::invalid_argument("unsupported Filament backend");
    }
}

template<typename T> T* pointer(uintptr_t value) {
    if (!value) throw std::invalid_argument("native handle cannot be zero");
    return reinterpret_cast<T*>(value);
}
template<typename T> uintptr_t handle(T* value) { return reinterpret_cast<uintptr_t>(value); }
template<typename T> void erase(std::vector<T*>& values, T* value) {
    values.erase(std::remove(values.begin(), values.end(), value), values.end());
}

class NativeEngine {
public:
    explicit NativeEngine(int requested_backend) {
        engine_ = filament::Engine::create(to_backend(requested_backend));
        if (!engine_) throw std::runtime_error("Filament could not create an engine");
    }
    ~NativeEngine() { close(); }
    NativeEngine(NativeEngine const&) = delete;
    NativeEngine& operator=(NativeEngine const&) = delete;

    bool alive() const noexcept { return engine_ != nullptr; }
    int backend() const { require_alive(); return static_cast<int>(engine_->getBackend()); }

    uintptr_t create_renderer() { require_alive(); auto* p = engine_->createRenderer(); renderers_.push_back(p); return handle(p); }
    uintptr_t create_scene() { require_alive(); auto* p = engine_->createScene(); scenes_.push_back(p); return handle(p); }
    uintptr_t create_view() { require_alive(); auto* p = engine_->createView(); views_.push_back(p); return handle(p); }
    uintptr_t create_camera() {
        require_alive();
        auto entity = utils::EntityManager::get().create();
        auto* camera = engine_->createCamera(entity);
        cameras_.push_back({camera, entity});
        return handle(camera);
    }
    uintptr_t create_window_swap_chain(uintptr_t native_window) {
        require_alive();
        if (!native_window) throw std::invalid_argument("native window handle cannot be zero");
        auto* p = engine_->createSwapChain(reinterpret_cast<void*>(native_window));
        swap_chains_.push_back(p); return handle(p);
    }
    uintptr_t create_headless_swap_chain(uint32_t width, uint32_t height) {
        require_alive(); auto* p = engine_->createSwapChain(width, height);
        swap_chains_.push_back(p); return handle(p);
    }

    void destroy(uintptr_t value, const std::string& kind) {
        if (!engine_ || !value) return;
        if (kind == "renderer") { auto* p = pointer<filament::Renderer>(value); erase(renderers_, p); engine_->destroy(p); }
        else if (kind == "scene") { auto* p = pointer<filament::Scene>(value); erase(scenes_, p); engine_->destroy(p); }
        else if (kind == "view") { auto* p = pointer<filament::View>(value); erase(views_, p); engine_->destroy(p); }
        else if (kind == "swap_chain") { auto* p = pointer<filament::SwapChain>(value); erase(swap_chains_, p); engine_->destroy(p); }
        else if (kind == "camera") {
            auto* p = pointer<filament::Camera>(value);
            auto found = std::find_if(cameras_.begin(), cameras_.end(), [p](auto const& item) { return item.first == p; });
            if (found != cameras_.end()) {
                engine_->destroy(found->second); utils::EntityManager::get().destroy(found->second); cameras_.erase(found);
            }
        } else throw std::invalid_argument("unknown native resource kind: " + kind);
    }

    bool begin_frame(uintptr_t renderer, uintptr_t swap_chain) {
        require_alive(); return pointer<filament::Renderer>(renderer)->beginFrame(pointer<filament::SwapChain>(swap_chain));
    }
    void render(uintptr_t renderer, uintptr_t view) {
        require_alive(); pointer<filament::Renderer>(renderer)->render(pointer<filament::View>(view));
    }
    void end_frame(uintptr_t renderer) { require_alive(); pointer<filament::Renderer>(renderer)->endFrame(); }
    void view_set_scene(uintptr_t view, uintptr_t scene) {
        require_alive(); pointer<filament::View>(view)->setScene(scene ? pointer<filament::Scene>(scene) : nullptr);
    }
    void view_set_camera(uintptr_t view, uintptr_t camera) {
        require_alive(); pointer<filament::View>(view)->setCamera(pointer<filament::Camera>(camera));
    }
    void view_set_viewport(uintptr_t view, int32_t x, int32_t y, uint32_t width, uint32_t height) {
        require_alive(); pointer<filament::View>(view)->setViewport({x, y, width, height});
    }
    void camera_look_at(uintptr_t camera, py::sequence eye, py::sequence target, py::sequence up) {
        require_alive();
        auto vec = [](py::sequence value) {
            if (py::len(value) != 3) throw std::invalid_argument("vector must contain three values");
            return filament::math::double3(value[0].cast<double>(), value[1].cast<double>(), value[2].cast<double>());
        };
        pointer<filament::Camera>(camera)->lookAt(vec(eye), vec(target), vec(up));
    }
    void camera_set_perspective(uintptr_t camera, double fov, double aspect, double near, double far) {
        require_alive(); pointer<filament::Camera>(camera)->setProjection(fov, aspect, near, far);
    }

    void close() noexcept {
        if (!engine_) return;
        for (auto* p : views_) engine_->destroy(p);
        for (auto const& item : cameras_) { engine_->destroy(item.second); utils::EntityManager::get().destroy(item.second); }
        for (auto* p : scenes_) engine_->destroy(p);
        for (auto* p : renderers_) engine_->destroy(p);
        for (auto* p : swap_chains_) engine_->destroy(p);
        views_.clear(); cameras_.clear(); scenes_.clear(); renderers_.clear(); swap_chains_.clear();
        filament::Engine::destroy(&engine_);
    }

private:
    void require_alive() const { if (!engine_) throw std::runtime_error("Engine has already been destroyed"); }
    filament::Engine* engine_ = nullptr;
    std::vector<filament::Renderer*> renderers_;
    std::vector<filament::Scene*> scenes_;
    std::vector<filament::View*> views_;
    std::vector<filament::SwapChain*> swap_chains_;
    std::vector<std::pair<filament::Camera*, utils::Entity>> cameras_;
};
}  // namespace

PYBIND11_MODULE(_native, module) {
    module.doc() = "Lifetime-safe core bridge to Filament";
    module.attr("FILAMENT_VERSION") = "1.76.1";
    module.attr("BINDING_VERSION") = PYTHON_FILAMENT_VERSION;
    py::class_<NativeEngine>(module, "Engine")
        .def(py::init<int>(), py::arg("backend") = 0)
        .def_property_readonly("alive", &NativeEngine::alive)
        .def_property_readonly("backend", &NativeEngine::backend)
        .def("create_renderer", &NativeEngine::create_renderer)
        .def("create_scene", &NativeEngine::create_scene)
        .def("create_view", &NativeEngine::create_view)
        .def("create_camera", &NativeEngine::create_camera)
        .def("create_window_swap_chain", &NativeEngine::create_window_swap_chain)
        .def("create_headless_swap_chain", &NativeEngine::create_headless_swap_chain)
        .def("destroy", &NativeEngine::destroy)
        .def("begin_frame", &NativeEngine::begin_frame)
        .def("render", &NativeEngine::render)
        .def("end_frame", &NativeEngine::end_frame)
        .def("view_set_scene", &NativeEngine::view_set_scene)
        .def("view_set_camera", &NativeEngine::view_set_camera)
        .def("view_set_viewport", &NativeEngine::view_set_viewport)
        .def("camera_look_at", &NativeEngine::camera_look_at)
        .def("camera_set_perspective", &NativeEngine::camera_set_perspective)
        .def("close", &NativeEngine::close);
}
