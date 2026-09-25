import os
import sys
import time
from pathlib import Path

# Try importing PYNQ
try:
    from pynq import Device
    dev = Device.active_device
    vccint_sensor = dev.sensors.get("vccint") if (hasattr(dev, "sensors") and dev.sensors) else None
except Exception:
    vccint_sensor = None

# Path to Zynq UltraScale+ SYSMON IIO device
IIO_PATH = Path("/sys/bus/iio/devices/iio:device0")
LOG_FILE = Path("/home/xilinx/primecam_readout/logs/zcu111_telemetry.csv") # Use non-volatile storage
# ina226_u65 on ZCU111 maps to vccint
INA226_VCCINT_PATH = Path("/sys/class/hwmon/hwmon10") 


def read_sysfs_float(path: Path) -> float:
    """Read a single float from sysfs."""
    try:
        if path.exists():
            return float(path.read_text().strip())
    except Exception:
        pass
    return float("nan")


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


def get_vccint_ina226():
    """Read VCCINT voltage, current, power directly from INA226 hwmon sysfs."""
    v_in = read_sysfs_float(INA226_VCCINT_PATH / "in1_input") / 1000.0   # mV -> V
    i_in = read_sysfs_float(INA226_VCCINT_PATH / "curr1_input") / 1000.0 # mA -> A
    p_in = read_sysfs_float(INA226_VCCINT_PATH / "power1_input") / 1e6   # uW -> W
    
    # Fallback to in0_input if in1_input isn't present
    if float("nan") in (v_in, i_in):
        if (INA226_VCCINT_PATH / "in0_input").exists():
            v_in = read_sysfs_float(INA226_VCCINT_PATH / "in0_input") / 1000.0

    return v_in, i_in, p_in


def get_vccint_pynq_fallback():
    """Fallback reader for PYNQ sensor object structure."""
    if not vccint_sensor:
        return float("nan"), float("nan"), float("nan")
    
    val = float("nan")
    # PYNQ sensors typically expose .value or ['value']
    if hasattr(vccint_sensor, "value"):
        val = float(vccint_sensor.value)
    elif hasattr(vccint_sensor, "get_value"):
        val = float(vccint_sensor.get_value())
    
    return val, float("nan"), float("nan")


def main():
    write_header = not LOG_FILE.exists()

    print(f"Starting telemetry logger. Output: {LOG_FILE}")

    with open(LOG_FILE, "a", buffering=1) as f:
        if write_header:
            f.write(
                "timestamp,ps_temp_c,pl_temp_c,sysmon_vccint_v,vccint_v,vccint_i_a,vccint_p_w,vccaux_v,mem_avail_mb\n"
            )
            f.flush()
            os.fsync(f.fileno())

        while True:
            t_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

            # 1. On-die SYSMON
            ps_temp = read_iio_val("in_temp0_ps_temp")
            pl_temp = read_iio_val("in_temp1_remote_temp")
            sysmon_vccint = read_iio_val("in_voltage2_vccint")
            vccaux = read_iio_val("in_voltage4_vccaux")
            mem_avail = get_mem_available_mb()

            # 2. Direct INA226 HWMon reading for VCCINT
            vccint_v, vccint_i, vccint_p = get_vccint_ina226()

            # Fallback to PYNQ if INA226 sysfs path fails
            if any(map(lambda x: x != x, [vccint_v, vccint_i])): # Check for NaN
                pv_v, pv_i, pv_p = get_vccint_pynq_fallback()
                vccint_v = pv_v if vccint_v != vccint_v else vccint_v

            log_line = (
                f"{t_now},{ps_temp:.2f},{pl_temp:.2f},{sysmon_vccint:.3f},"
                f"{vccint_v:.3f},{vccint_i:.3f},{vccint_p:.3f},{vccaux:.3f},{mem_avail:.1f}\n"
            )

            f.write(log_line)
            f.flush()
            os.fsync(f.fileno())

            time.sleep(1.0)


if __name__ == "__main__":
    main()