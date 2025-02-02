from toggle_display_input import Display

from pathlib import Path

import pytest


def test_parse_target() -> None:
    assert Display.parse_target("usb") == False
    assert Display.parse_target("alt") == True
    assert Display.parse_target(None) is None
    with pytest.raises(ValueError):
        Display.parse_target("")
    with pytest.raises(ValueError):
        Display.parse_target("xyz")


def test_cache() -> None:
    path = Path(Path.cwd() / "test_cache.json")
    path.unlink(missing_ok=True)

    displays = [Display(None), Display(None)]
    cache = Display.Cache(displays, path=path)
    assert displays[0]._model_cache is None
    assert displays[1]._model_cache is None

    displays[0]._model_cache = "model0"
    displays[1]._model_cache = "model1"
    cache.save()
    assert path.exists()

    displays = [Display(None), Display(None)]
    cache = Display.Cache(displays, path=path)
    assert displays[0]._model_cache == "model0"
    assert displays[1]._model_cache == "model1"

    path.unlink(missing_ok=True)
