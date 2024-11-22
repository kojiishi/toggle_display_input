#!/usr/bin/env python3
#
# Toggle display input sources
# using the VESA Monitor Control Command Set (MCCS)
# over the Display Data Channel Command Interface Standard (DDC-CI).
#
import argparse

# https://newam.github.io/monitorcontrol/api.html
import monitorcontrol
# https://github.com/newAM/monitorcontrol/issues/170
monitorcontrol.InputSource.USBC1 = 27

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
    def _input_source(self):
        try:
            return self._monitor.get_input_source()
        except monitorcontrol.monitorcontrol.InputSourceValueError:
            # `get_input_source` fails if the current is USB.
            # https://github.com/newAM/monitorcontrol/issues/170
            # https://github.com/newAM/monitorcontrol/issues/258
            return monitorcontrol.InputSource.USBC1

    @_input_source.setter
    def _input_source(self, input_source):
        self._monitor.set_input_source(input_source)

    @staticmethod
    def toggle_all(args):
        is_current_usb_c = None
        monitors = monitorcontrol.get_monitors()
        for monitor in monitors:
            display = Display(monitor)
            with monitor:
                model = display._model
                alt_input_source = alt_input_sources.get(model)
                if alt_input_source is None:
                    if args.verbose: print(f'{model}: No changes')
                    continue

                if is_current_usb_c is None:
                    is_current_usb_c = display._input_source == monitorcontrol.InputSource.USBC1

                if is_current_usb_c:
                    print(f'{model}: Switch to {alt_input_source}')
                    new_input_source = alt_input_source
                else:
                    print(f'{model}: Switch to USB-C')
                    new_input_source = monitorcontrol.InputSource.USBC1
                if not args.dryrun:
                    display._input_source = new_input_source

    @staticmethod
    def run_by_ddm():
        import subprocess
        ddm = "C:/Program Files/Dell/Dell Display Manager 2/DDM"
        proc = subprocess.run([ddm, "/Console", "start", "/ReadActiveInput"], capture_output=True, text=True)
        print(proc)

    @staticmethod
    def toggle_cmd():
        parser = argparse.ArgumentParser()
        parser.add_argument('-n', '--dryrun', action='store_true')
        parser.add_argument('-v', '--verbose', action='count', default=0)
        args = parser.parse_args()
        Display.toggle_all(args)

if __name__ == '__main__':
    Display.toggle_cmd()