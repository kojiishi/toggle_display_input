#!/usr/bin/env python3
#
# Toggle display input sources
# using the VESA Monitor Control Command Set (MCCS)
# over the Display Data Channel Command Interface Standard (DDC-CI).
#
import argparse
import json
import logging
from pathlib import Path
import sys
from typing import List
from typing import TypeAlias

# https://newam.github.io/monitorcontrol/api.html
import monitorcontrol
import platformdirs

logger = logging.getLogger("display")

InputSource: TypeAlias = monitorcontrol.InputSource | int

# https://github.com/newAM/monitorcontrol/issues/170
primary_input_source = 27
alt_input_sources = {
    "U2723QX": monitorcontrol.InputSource.DP1,
    "P3223QE": monitorcontrol.InputSource.HDMI1,
}


class Display:
    def __init__(self, monitor: monitorcontrol.Monitor):
        self._monitor = monitor
        self._vcp_capabilities = None
        self._model = None

    _is_cache_changed = False

    @staticmethod
    def get_all() -> List["Display"]:
        monitors = monitorcontrol.get_monitors()
        return [Display(monitor) for monitor in monitors]

    @property
    def vcp_capabilities(self) -> dict:
        if self._vcp_capabilities is None:
            self._vcp_capabilities = self._monitor.get_vcp_capabilities()
            logger.debug("vcp_capabilities=%s", self._vcp_capabilities)
        return self._vcp_capabilities

    @property
    def model(self) -> str:
        if self._model is None:
            self._model = self.vcp_capabilities["model"]
            Display._is_cache_changed = True
        return self._model

    @property
    def input_source(self) -> InputSource:
        try:
            return self._monitor.get_input_source()
        except monitorcontrol.monitorcontrol.InputSourceValueError as e:
            # `get_input_source` fails if the current is USB.
            # https://github.com/newAM/monitorcontrol/issues/170
            # https://github.com/newAM/monitorcontrol/issues/258
            return e.value

    @input_source.setter
    def input_source(self, new_input_source: InputSource) -> None:
        self._monitor.set_input_source(new_input_source)

    @staticmethod
    def toggle_all(
        displays: List["Display"],
        is_current_primary: bool | None = None,
        is_dry_run: bool = False,
    ):
        for display in displays:
            # Check the `_model` before to avoid unnecessary `with`.
            model = display._model
            if model is not None and model not in alt_input_sources:
                logger.debug("%s: No changes (cached)", model)
                continue
            with display._monitor:
                model = display.model
                alt_input_source = alt_input_sources.get(model)
                if alt_input_source is None:
                    logger.info("%s: No changes", model)
                    continue

                if is_current_primary is None:
                    is_current_primary = display.input_source == primary_input_source
                if is_current_primary:
                    new_input_source = alt_input_source
                else:
                    new_input_source = primary_input_source
                logger.info("%s: Switch to %s", model, new_input_source)
                if not is_dry_run:
                    display.input_source = new_input_source

    class Cache:
        def __init__(
            self,
            displays: List["Display"],
            path: Path = Path(platformdirs.user_cache_dir("display")) / "display.json",
            load: bool = True,
        ):
            self.displays = displays
            self.path = path
            if load:
                self.load()

        def load(self) -> None:
            try:
                with open(self.path, "r") as fp:
                    cache = json.load(fp)
            except FileNotFoundError:
                return
            logger.debug("Cache loaded from <%s>", self.path)
            for display, model in zip(self.displays, cache["models"]):
                display._model = model

        def save(self) -> None:
            cache = {
                "models": [display._model for display in self.displays],
            }
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w") as fp:
                json.dump(cache, fp)
            logger.debug("Cache saved to <%s>", self.path)

    @staticmethod
    def init_log(verbose: int) -> None:
        if verbose <= 0:
            handler = logging.StreamHandler(sys.stdout)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            return
        logging.basicConfig(level=logging.DEBUG)

    @staticmethod
    def parse_target(target) -> bool | None:
        if target == "usb":
            return False
        if target == "alt":
            return True
        if target is None:
            return None
        raise ValueError(f'The target "{target}" must be "usb" or "alt".')

    @staticmethod
    def toggle_cmd():
        parser = argparse.ArgumentParser()
        parser.add_argument("-f", "--no-cache", action="store_true")
        parser.add_argument("-n", "--dry-run", action="store_true")
        parser.add_argument("-v", "--verbose", action="count", default=0)
        parser.add_argument("target", nargs="?", help="usb|alt")
        args = parser.parse_args()
        Display.init_log(args.verbose)
        is_current_primary = Display.parse_target(args.target)

        displays = Display.get_all()
        cache = Display.Cache(displays, load=not args.no_cache)
        Display.toggle_all(
            displays,
            is_current_primary=is_current_primary,
            is_dry_run=args.dry_run,
        )
        if Display._is_cache_changed:
            cache.save()


if __name__ == "__main__":
    Display.toggle_cmd()
