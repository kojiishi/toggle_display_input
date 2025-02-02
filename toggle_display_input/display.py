#!/usr/bin/env python3
#
# Toggle display input sources
# using the VESA Monitor Control Command Set (MCCS)
# over the Display Data Channel Command Interface Standard (DDC-CI).
#
import argparse
import json
from pathlib import Path
import platformdirs
from typing import List
from typing import TypeAlias

# https://newam.github.io/monitorcontrol/api.html
import monitorcontrol

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
    def toggle_all(args):
        displays = Display.get_all()
        cache = Display.Cache(displays, verbose=args.verbose)
        for display in displays:
            # Check the `_model` before to avoid unnecessary `with`.
            if display._model is not None and display._model not in alt_input_sources:
                if args.verbose > 1:
                    print(f"{display._model}: No changes (cached)")
                continue
            with display._monitor:
                if args.verbose > 1:
                    print(display.vcp_capabilities)
                model = display.model
                alt_input_source = alt_input_sources.get(model)
                if alt_input_source is None:
                    if args.verbose:
                        print(f"{model}: No changes")
                    continue

                if args.is_current_primary is None:
                    args.is_current_primary = (
                        display.input_source == primary_input_source
                    )
                if args.is_current_primary:
                    new_input_source = alt_input_source
                else:
                    new_input_source = primary_input_source
                print(f"{model}: Switch to {new_input_source}")
                if not args.dryrun:
                    display.input_source = new_input_source

        if Display._is_cache_changed:
            cache.save()

    class Cache:
        def __init__(
            self,
            displays: List["Display"],
            path: Path = Path(platformdirs.user_cache_dir("display")) / "display.json",
            verbose: int = 0,
        ):
            self.displays = displays
            self.path = path
            self.verbose = verbose
            try:
                with open(self.path, "r") as fp:
                    cache = json.load(fp)
            except FileNotFoundError:
                return
            if self.verbose > 1:
                print(f"Cache loaded from <{self.path}>\n{self.read()}")
            for display, model in zip(self.displays, cache["models"]):
                display._model = model

        def save(self) -> None:
            cache = {
                "models": [display._model for display in self.displays],
            }
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w") as fp:
                json.dump(cache, fp)
            if self.verbose > 1:
                print(f"Cache saved to <{self.path}>\n{self.read()}")

        def read(self) -> str:
            with open(self.path, "r") as fp:
                return fp.read()

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
        parser.add_argument("-n", "--dryrun", action="store_true")
        parser.add_argument("-v", "--verbose", action="count", default=0)
        parser.add_argument("target", nargs="?", help="usb|alt")
        args = parser.parse_args()
        args.is_current_primary = Display.parse_target(args.target)
        Display.toggle_all(args)


if __name__ == "__main__":
    Display.toggle_cmd()
