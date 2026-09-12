try:
    from .widget import FilamentWidget
except ImportError as exc:
    raise ImportError("Qt support requires `pip install python-filament[qt]`") from exc

__all__ = ["FilamentWidget"]
