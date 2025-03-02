from display import Display

from pathlib import Path
import tempfile

import monitorcontrol
import pytest


class MockMonitor:
    def __init__(self):
        self.enter_count = 0

    def __enter__(self):
        self.enter_count += 1

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class MockDisplay:
    def __init__(self, model, input_source, _model=None):
        self.model = model
        self.input_source = input_source
        self._model = _model
        self._monitor = MockMonitor()


@pytest.mark.parametrize("cached", [False, True])
def test_toggle_all(cached: bool) -> None:
    # Create the mock data.
    displays = [
        MockDisplay("P2415Q", 1),
        MockDisplay("", 1),
        MockDisplay("U2723QX", 27),
        MockDisplay("P3223QE", 27),
    ]
    if cached:
        for display in displays:
            display._model = display.model

    # Toggle to switch them to alternative inputs.
    Display.toggle_all(displays)
    assert [display.input_source for display in displays] == [
        1,
        1,
        monitorcontrol.InputSource.DP1,
        monitorcontrol.InputSource.HDMI1,
    ]
    assert [display._monitor.enter_count for display in displays] == (
        [0, 0, 1, 1] if cached else [1, 1, 1, 1]
    )

    # Toggle again to switch them back to primary inputs.
    Display.toggle_all(displays)
    assert [display.input_source for display in displays] == [1, 1, 27, 27]
    assert [display._monitor.enter_count for display in displays] == (
        [0, 0, 2, 2] if cached else [2, 2, 2, 2]
    )


def test_parse_target() -> None:
    assert Display.parse_target("usb") == False
    assert Display.parse_target("alt") == True
    assert Display.parse_target(None) is None
    with pytest.raises(ValueError):
        Display.parse_target("")
    with pytest.raises(ValueError):
        Display.parse_target("xyz")


def test_cache() -> None:
    tmp_dir = tempfile.TemporaryDirectory()
    path = Path(tmp_dir.name) / "test_cache.json"
    path.unlink(missing_ok=True)

    displays = [Display(None), Display(None)]
    cache = Display.Cache(displays, path=path)
    assert displays[0]._model is None
    assert displays[1]._model is None

    displays[0]._model = "model0"
    displays[1]._model = "model1"
    cache.save()
    assert path.exists()

    displays = [Display(None), Display(None)]
    assert displays[0]._model is None
    assert displays[1]._model is None
    cache = Display.Cache(displays, path=path)
    assert displays[0]._model == "model0"
    assert displays[1]._model == "model1"

    path.unlink(missing_ok=True)
    tmp_dir.cleanup()
