import os
import sys
import time
from pathlib import Path

# Path to Zynq UltraScale+ SYSMON IIO device
IIO_PATH = Path("/sys/bus/iio/devices/iio:device0")
LOG_FILE = Path("/home/xilinx/primecam_readout/logs/zcu111_telemetry.csv") # Use non-volatile storage


def read_iio_val(param_name: str) -> float:
    """Read raw IIO parameter and apply scaling/offset if present."""
    try:
        raw_p = IIO_PATH / f"{param_name}_raw"
        scale_p = IIO_PATH / f"{param_name}_scale"
        offset_p = IIO_PATH / f"{param_name}_offset"

        if not raw_p.exists():
            # Fallback to direct input if pre-scaled by kernel
            input_p = IIO_PATH / f"{param_name}_input"
            if input_p.exists():
                return float(input_p.read_text().strip()) / 1000.0
            return float("nan")

        raw = float(raw_p.read_text().strip())
        offset = float(offset_p.read_text().strip()) if offset_p.exists() else 0.0
        scale = float(scale_p.read_text().strip()) if scale_p.exists() else 1.0

        # SYSMON temperature calculation standard
        return (raw + offset) * scale / 1000.0
    except Exception:
        return float("nan")


def get_mem_available_mb() -> float:
    """Read available memory directly from /proc/meminfo."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if "MemAvailable:" in line:
                    return float(line.split()[1]) / 1024.0
    except Exception:
        pass
    return float("nan")


def main():
    write_header = not LOG_FILE.exists()

    print(f"Starting telemetry logger. Output: {LOG_FILE}")

    # Open log file in append mode with minimal buffer
    with open(LOG_FILE, "a", buffering=1) as f:
        if write_header:
            f.write(
                "timestamp,ps_temp_c,pl_temp_c,vccint_v,vccaux_v,mem_avail_mb\n"
            )
            f.flush()
            os.fsync(f.fileno())

        while True:
            t_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

            # IIO Channel mappings (adjust prefixes for your kernel version if needed)
            ps_temp = read_iio_val("in_temp0_ps_temp")
            pl_temp = read_iio_val("in_temp1_remote_temp")
            vccint = read_iio_val("in_voltage2_vccint")
            vccaux = read_iio_val("in_voltage4_vccaux")
            mem_avail = get_mem_available_mb()

            log_line = f"{t_now},{ps_temp:.2f},{pl_temp:.2f},{vccint:.3f},{vccaux:.3f},{mem_avail:.1f}\n"

            f.write(log_line)

            # CRITICAL: Force OS to flush buffer to flash memory instantly
            f.flush()
            os.fsync(f.fileno())

            time.sleep(1.0)


if __name__ == "__main__":
    main()