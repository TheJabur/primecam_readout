#!/usr/bin/env python3

def calc_temp(raw: int) -> float:
    """Convert raw 16-bit ADC value to Celsius per UG580 Eq 2-7."""
    return round(raw * 501.3743 / 65536 - 273.6777, 4)

def board_temps() -> dict:
    ps_path = "/sys/bus/iio/devices/iio:device0/in_temp0_ps_temp_raw"
    pl_path = "/sys/bus/iio/devices/iio:device0/in_temp2_pl_temp_raw"

    with open(ps_path, "r") as f:
        ps_raw = int(f.read().strip())
    with open(pl_path, "r") as f:
        pl_raw = int(f.read().strip())

    return {
        'ps_processor': calc_temp(ps_raw),
        'pl_fabric': calc_temp(pl_raw)
    }

if __name__ == "__main__":
    temps = board_temps()
    print(f"PS Processor: {temps['ps_processor']} °C")
    print(f"PL Fabric:    {temps['pl_fabric']} °C")