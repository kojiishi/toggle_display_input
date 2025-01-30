#!/usr/bin/env python3
#
# Toggle display input sources
# using the VESA Monitor Control Command Set (MCCS)
# over the Display Data Channel Command Interface Standard (DDC-CI).
#
import argparse
import configparser
import json
import os
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

    @property
    def _vcp_capabilities(self) -> dict:
        if self._vcp_capabilities_cache is None:
            self._vcp_capabilities_cache = self._monitor.get_vcp_capabilities()
        return self._vcp_capabilities_cache

    @property
    def _model(self) -> str:
        return self._vcp_capabilities["model"]

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
        monitors = monitorcontrol.get_monitors()
        displays = [Display(monitor) for monitor in monitors]

        filtered_displays = Display.filter_by_cached_models(
            displays, verbose=args.verbose
        )
        if filtered_displays is not None:
            displays = filtered_displays
            models = None
        else:
            models = []

        if args.target == "usb":
            is_current_primary = False
        elif args.target == "alt":
            is_current_primary = True
        elif args.target is None:
            is_current_primary = None
        else:
            raise ValueError(
                'The target "{}" must be "usb" or "alt".'.format(args.target)
            )

        for display in displays:
            with display._monitor:
                if args.verbose > 1:
                    print(display._vcp_capabilities)
                model = display._model
                if models is not None:
                    models.append(model)
                alt_input_source = alt_input_sources.get(model)
                if alt_input_source is None:
                    if args.verbose:
                        print(f"{model}: No changes")
                    continue

                if is_current_primary is None:
                    is_current_primary = display._input_source == primary_input_source
                if is_current_primary:
                    new_input_source = alt_input_source
                else:
                    new_input_source = primary_input_source
                print(f"{model}: Switch to {new_input_source}")
                if not args.dryrun:
                    display._input_source = new_input_source

        if models is not None:
            if args.verbose > 1:
                print(f"Saving models {models} to {Display.models_cache_path()}")
            Display.save_models_cache(models)

    @staticmethod
    def filter_by_cached_models(
        displays: List["Display"], verbose: int = 0
    ) -> List["Display"] | None:
        models = Display.load_models_cache()
        if len(displays) != len(models):
            return None
        filtered = []
        for display, model in zip(displays, models):
            if alt_input_sources.get(model) is not None:
                filtered.append(display)
            elif verbose > 1:
                print(f'Skipped "{model}" by the cached model.')
        return filtered

    @staticmethod
    def load_models_cache() -> List[str]:
        config = configparser.ConfigParser()
        config.read(Display.models_cache_path())
        try:
            models_str = config.get("DEFAULT", "models")
            return json.loads(models_str)
        except configparser.NoOptionError:
            return []

    @staticmethod
    def save_models_cache(models: List[str]) -> None:
        config = configparser.ConfigParser()
        config.set("DEFAULT", "models", json.dumps(models))
        path = Display.models_cache_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as file:
            config.write(file)

    @staticmethod
    def models_cache_path() -> str:
        return os.path.join(
            platformdirs.user_cache_dir("display", "kojii"), "display.toml"
        )

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
        Display.toggle_all(args)


if __name__ == "__main__":
    Display.toggle_cmd()
