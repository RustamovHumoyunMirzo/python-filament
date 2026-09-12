import asyncio

import numpy as np
import pytest

import filament as fl


def engine():
    return fl.Engine(native=False)


def test_resource_lifetime_and_context_manager():
    with engine() as value:
        scene = value.create_scene()
        scene.close()
        scene.close()
        with pytest.raises(fl.ResourceDestroyedError):
            scene.add(fl.Node())
    assert not value.alive
    with pytest.raises(fl.ResourceDestroyedError):
        value.create_scene()


def test_scene_rejects_resources_from_another_engine():
    first, second = engine(), engine()
    with pytest.raises(ValueError):
        first.create_scene().add(second.create_entity())
    first.close()
    second.close()


def test_scene_graph_and_math():
    root, child = fl.Node("root"), fl.Node("wheel")
    root.add_child(child)
    child.rotation = fl.Quaternion.from_euler(0, 90, 0, degrees=True)
    assert root.find("wheel") is child
    assert np.allclose(np.asarray(fl.Matrix4.translation(1, 2, 3))[:3, 3], (1, 2, 3))


def test_cache_and_async_model_loading():
    value = engine()
    model_path = "model.glb"
    assert value.load_model(model_path) is value.load_model(model_path)
    assert value.load_model(model_path, cache=False) is not value.load_model(model_path)
    assert value.load_model_async(model_path).result().name == "model"
    assert asyncio.run(value.async_load_model(model_path)).name == "model"
    value.close()


def test_texture_mesh_and_builders():
    value = engine()
    texture = fl.Texture(value, 2, 3)
    texture.upload(np.zeros((3, 2, 4), dtype=np.uint8))
    with pytest.raises(ValueError):
        texture.upload(np.zeros((2, 3, 4), dtype=np.uint8))
    built = fl.Texture.builder(value).width(4).height(5).format(fl.TextureFormat.RGBA8).build()
    assert (built.width, built.height) == (4, 5)
    mesh = fl.Mesh(value, [[0, 0, 0], [1, 0, 0], [0, 1, 0]], [0, 1, 2])
    assert mesh.vertices.dtype == np.float32
    value.close()


def test_renderer_frame_contract():
    value = engine()
    renderer, view = value.create_renderer(), value.create_view()
    swap_chain = value.create_swap_chain(width=4, height=4, headless=True)
    with pytest.raises(RuntimeError):
        renderer.render(view)
    renderer.render_frame(swap_chain, view)
    assert not renderer._in_frame
    value.close()
