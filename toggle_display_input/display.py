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
        self._vcp_capabilities_cache = None
        self._model_cache = None

    _is_cache_changed = False

    @staticmethod
    def get_all() -> List["Display"]:
        monitors = monitorcontrol.get_monitors()
        return [Display(monitor) for monitor in monitors]

    @property
    def _vcp_capabilities(self) -> dict:
        if self._vcp_capabilities_cache is None:
            self._vcp_capabilities_cache = self._monitor.get_vcp_capabilities()
        return self._vcp_capabilities_cache

    @property
    def _model(self) -> str:
        if self._model_cache is None:
            self._model_cache = self._vcp_capabilities["model"]
            Display._is_cache_changed = True
        return self._model_cache

    @property
    def _input_source(self) -> InputSource:
        try:
            return self._monitor.get_input_source()
        except monitorcontrol.monitorcontrol.InputSourceValueError as e:
            # `get_input_source` fails if the current is USB.
            # https://github.com/newAM/monitorcontrol/issues/170
            # https://github.com/newAM/monitorcontrol/issues/258
            return e.value

    @_input_source.setter
    def _input_source(self, input_source: InputSource) -> None:
        self._monitor.set_input_source(input_source)

    @staticmethod
    def toggle_all(args):
        displays = Display.get_all()
        Display.load_cache(displays, verbose=args.verbose)
        for display in displays:
            # Check the `_model_cache` before to avoid unnecessary `with`.
            if (
                display._model_cache is not None
                and alt_input_sources.get(display._model_cache) is None
            ):
                if args.verbose > 1:
                    print(f"{display._model_cache}: No changes (cached)")
                continue
            with display._monitor:
                if args.verbose > 1:
                    print(display._vcp_capabilities)
                model = display._model
                alt_input_source = alt_input_sources.get(model)
                if alt_input_source is None:
                    if args.verbose:
                        print(f"{model}: No changes")
                    continue

                if args.is_current_primary is None:
                    args.is_current_primary = (
                        display._input_source == primary_input_source
                    )
                if args.is_current_primary:
                    new_input_source = alt_input_source
                else:
                    new_input_source = primary_input_source
                print(f"{model}: Switch to {new_input_source}")
                if not args.dryrun:
                    display._input_source = new_input_source

        if Display._is_cache_changed:
            Display.save_cache(displays, verbose=args.verbose)

    @staticmethod
    def load_cache(displays: List["Display"], verbose: int = 0) -> None:
        path = Display.cache_path()
        try:
            with open(path, "r") as fp:
                cache = json.load(fp)
        except FileNotFoundError:
            return
        if verbose > 1:
            print(f"Cache loaded from {path}")
        for display, model in zip(displays, cache["models"]):
            display._model_cache = model

    @staticmethod
    def save_cache(displays: List["Display"], verbose: int = 0) -> None:
        cache = {
            "models": [display._model_cache for display in displays],
        }
        path = Display.cache_path(ensure_exists=True)
        with open(path, "w") as fp:
            json.dump(cache, fp)
        if verbose > 1:
            print(f"Cache saved to {path}")
            with open(path, "r") as fp:
                print(fp.read())

    @staticmethod
    def cache_path(ensure_exists: bool = False) -> Path:
        return Path(platformdirs.user_cache_dir("display", ensure_exists=ensure_exists)) / "display.json"

    @staticmethod
    def run_by_ddm():
        import subprocess

        ddm = "C:/Program Files/Dell/Dell Display Manager 2/DDM"
        proc = subprocess.run(
            [ddm, "/Console", "start", "/ReadActiveInput"],
            capture_output=True,
            text=True,
        )
        print(proc)

    @staticmethod
    def toggle_cmd():
        parser = argparse.ArgumentParser()
        parser.add_argument("-n", "--dryrun", action="store_true")
        parser.add_argument("-v", "--verbose", action="count", default=0)
        parser.add_argument("target", nargs="?", help="usb|alt")
        args = parser.parse_args()

        if args.target == "usb":
            args.is_current_primary = False
        elif args.target == "alt":
            args.is_current_primary = True
        elif args.target is None:
            args.is_current_primary = None
        else:
            raise ValueError(f'The target "{args.target}" must be "usb" or "alt".')

        Display.toggle_all(args)


if __name__ == "__main__":
    Display.toggle_cmd()
