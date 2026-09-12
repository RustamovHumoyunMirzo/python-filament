#include <filament/Engine.h>
#include <backend/DriverEnums.h>
#include <pybind11/pybind11.h>

#include <stdexcept>
#include <string>

namespace py = pybind11;

namespace {
filament::Engine::Backend to_native_backend(int value) {
    using Backend = filament::Engine::Backend;
    switch (value) {
        case 0: return Backend::DEFAULT;
        case 1: return Backend::OPENGL;
        case 2: return Backend::VULKAN;
        case 3: return Backend::METAL;
        default: throw std::invalid_argument("unsupported Filament backend");
    }
}

class NativeEngine {
public:
    explicit NativeEngine(int backend) {
        engine_ = filament::Engine::create(to_native_backend(backend));
        if (!engine_) throw std::runtime_error("Filament could not create an engine");
    }
    ~NativeEngine() { close(); }
    NativeEngine(NativeEngine const&) = delete;
    NativeEngine& operator=(NativeEngine const&) = delete;

    void close() noexcept {
        if (engine_) {
            filament::Engine::destroy(&engine_);
            engine_ = nullptr;
        }
    }
    bool alive() const noexcept { return engine_ != nullptr; }
    int backend() const {
        if (!engine_) throw std::runtime_error("Engine has already been destroyed");
        return static_cast<int>(engine_->getBackend());
    }

private:
    filament::Engine* engine_ = nullptr;
};
}  // namespace

PYBIND11_MODULE(_native, module) {
    module.doc() = "Minimal lifetime-safe bridge to Filament";
    module.attr("FILAMENT_VERSION") = "1.76.1";
    py::class_<NativeEngine>(module, "Engine")
        .def(py::init<int>(), py::arg("backend") = 0)
        .def_property_readonly("alive", &NativeEngine::alive)
        .def_property_readonly("backend", &NativeEngine::backend)
        .def("close", &NativeEngine::close);
}

