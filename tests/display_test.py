from toggle_display_input import Display

import pytest


def test_parse_target() -> None:
    assert Display.parse_target("usb") == False
    assert Display.parse_target("alt") == True
    assert Display.parse_target(None) is None
    with pytest.raises(ValueError):
        Display.parse_target("")
    with pytest.raises(ValueError):
        Display.parse_target("xyz")
