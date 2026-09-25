import os
import sys
import time
from pathlib import Path

# Try importing PYNQ to read PMBus/INA226 rail metrics directly
try:
    from pynq import Device
    PYNQ_AVAILABLE = True
    dev = Device.active_device
    vccint_sensor = dev.sensors.get("vccint") if (hasattr(dev, "sensors") and dev.sensors) else None
except Exception:
    PYNQ_AVAILABLE = False
    vccint_sensor = None

# Path to Zynq UltraScale+ SYSMON IIO device
IIO_PATH = Path("/sys/bus/iio/devices/iio:device0")
LOG_FILE = Path("/home/xilinx/primecam_readout/logs/zcu111_telemetry.csv") # Use non-volatile storage


def read_iio_val(param_name: str) -> float:
    """Read raw IIO parameter from SYSMON and apply scaling/offset."""
    try:
        raw_p = IIO_PATH / f"{param_name}_raw"
        scale_p = IIO_PATH / f"{param_name}_scale"
        offset_p = IIO_PATH / f"{param_name}_offset"

        if not raw_p.exists():
            input_p = IIO_PATH / f"{param_name}_input"
            if input_p.exists():
                return float(input_p.read_text().strip()) / 1000.0
            return float("nan")

        raw = float(raw_p.read_text().strip())
        offset = float(offset_p.read_text().strip()) if offset_p.exists() else 0.0
        scale = float(scale_p.read_text().strip()) if scale_p.exists() else 1.0

        return (raw + offset) * scale / 1000.0
    except Exception:
        return float("nan")


def get_mem_available_mb() -> float:
    """Read available memory from /proc/meminfo."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemAvailable:" in line:
                    return float(line.split()[1]) / 1024.0
    except Exception:
        pass
    return float("nan")


def read_pynq_sensor_attr(sensor, attr_name: str) -> float:
    """Safely query a PYNQ sensor attribute (voltage, current, power)."""
    if sensor and hasattr(sensor, attr_name):
        try:
            val_func = getattr(sensor, attr_name)
            return float(val_func())
        except Exception:
            pass
    return float("nan")


def main():
    write_header = not LOG_FILE.exists()

    print(f"Starting telemetry logger. Output file: {LOG_FILE}")
    if vccint_sensor:
        print("Successfully bound PYNQ 'vccint' sensor (Voltage, Current, Power).")
    else:
        print("Warning: PYNQ 'vccint' sensor not detected; relying on SYSMON fallbacks.")

    with open(LOG_FILE, "a", buffering=1) as f:
        if write_header:
            # Header includes SYSMON on-die metrics and board-level VCCINT current/power
            f.write(
                "timestamp,ps_temp_c,pl_temp_c,sysmon_vccint_v,vccint_v,vccint_i_a,vccint_p_w,vccaux_v,mem_avail_mb\n"
            )
            f.flush()
            os.fsync(f.fileno())

        while True:
            t_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

            # 1. On-die SYSMON metrics
            ps_temp = read_iio_val("in_temp0_ps_temp")
            pl_temp = read_iio_val("in_temp1_remote_temp")
            sysmon_vccint = read_iio_val("in_voltage2_vccint")
            vccaux = read_iio_val("in_voltage4_vccaux")
            mem_avail = get_mem_available_mb()

            # 2. Board-level VCCINT PMBus/INA226 metrics via PYNQ
            if vccint_sensor:
                vccint_v = read_pynq_sensor_attr(vccint_sensor, "voltage")
                vccint_i = read_pynq_sensor_attr(vccint_sensor, "current")
                vccint_p = read_pynq_sensor_attr(vccint_sensor, "power")
            else:
                vccint_v = sysmon_vccint
                vccint_i = float("nan")
                vccint_p = float("nan")

            log_line = (
                f"{t_now},{ps_temp:.2f},{pl_temp:.2f},{sysmon_vccint:.3f},"
                f"{vccint_v:.3f},{vccint_i:.3f},{vccint_p:.3f},{vccaux:.3f},{mem_avail:.1f}\n"
            )

            f.write(log_line)

            # Flush to storage immediately so entries survive a hang
            f.flush()
            os.fsync(f.fileno())

            time.sleep(1.0)


if __name__ == "__main__":
    main()