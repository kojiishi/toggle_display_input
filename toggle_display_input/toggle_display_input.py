# https://newam.github.io/monitorcontrol/api.html
import monitorcontrol
# https://github.com/newAM/monitorcontrol/issues/170
monitorcontrol.InputSource.USBC1 = 27

alt_input_sources = {
    "U2723QX": monitorcontrol.InputSource.DP1,
    "P3223QE": monitorcontrol.InputSource.HDMI1,
}

def run():
    is_current_usb_c = None
    monitors = monitorcontrol.get_monitors()
    print(monitors)
    for monitor in monitors:
        with monitor:
            vcp_cap = monitor.get_vcp_capabilities()
            model = vcp_cap["model"]
            print(f'Model={model}')
            alt_input_source = alt_input_sources.get(model)
            if alt_input_source is None:
                continue

            if is_current_usb_c is None:
                try:
                    current_input = monitor.get_input_source()
                    is_current_usb_c = current_input == monitorcontrol.InputSource.USBC1
                except monitorcontrol.monitorcontrol.InputSourceValueError:
                    # `get_input_source` fails if the current is USB.
                    # https://github.com/newAM/monitorcontrol/issues/170
                    # https://github.com/newAM/monitorcontrol/issues/258
                    is_current_usb_c = True

            if is_current_usb_c:
                print(f'{model}: Switch to {alt_input_source}')
                monitor.set_input_source(alt_input_source)
            else:
                print(f'{model}: Switch to USB-C')
                monitor.set_input_source(monitorcontrol.InputSource.USBC1)

def run_by_ddm():
    import subprocess
    ddm = "C:/Program Files/Dell/Dell Display Manager 2/DDM"
    proc = subprocess.run([ddm, "/Console", "start", "/ReadActiveInput"], capture_output=True, text=True)
    print(proc)

run()
