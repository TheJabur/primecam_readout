import fcntl
import os
import serial
import struct

import time


class SerialDeviceMutex:
    """Advisory file lock keyed by the underlying serial device path.

    serial.Serial does not by itself prevent multiple OS processes (e.g. the
    4 drone processes on a board) from writing/reading a shared serial device
    at the same time, which corrupts command/response framing on the wire.
    `flock` is process-safe (unlike threading.Lock), blocks callers until the
    device is free (forming a queue), and is auto-released if a process dies.
    """

    _lock_dir = "/tmp/primecam_readout_locks"

    def __init__(self, device_path):
        os.makedirs(self._lock_dir, exist_ok=True)
        lock_name = os.path.basename(os.path.realpath(device_path))
        self._lock_path = os.path.join(self._lock_dir, f"{lock_name}.lock")
        self._fd = None

    def acquire(self):
        self._fd = open(self._lock_path, "w")
        fcntl.flock(self._fd, fcntl.LOCK_EX)  # blocks until it's our turn
        return self

    def release(self, exc_type, exc_val, exc_tb):
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        self._fd.close()
        self._fd = None


class Primecamfe:
    """2025 version.
    """

    def __init__(self, comport) -> None:
        """
        Primecam RF Front End control. On initialization this will attempt to connect
        to the provided device and verify it works with this software
        :param comport: Comport or path that the attenuator is connected to.
            eg: COM13 or /dev/ttyACM0  (users can create permanent simlinks to this dev using udevrules in Ubuntu)
        """
        self._ASSERTIONS = True
        self._ENABLE_DEBUG = False
        self._lock = SerialDeviceMutex(comport)
        self.connected = False
        self.comport = comport
        self.ser = None

    def connect(self):
        if self.connected:
            return
        try:
            self.ser = serial.Serial(self.comport, baudrate=115200, timeout=5)
        except serial.SerialException:
            raise ConnectionError("Serial port doesn't exist")
        if self.ser.is_open:
            self.connected = True
            self.ser.write(b"get_id\n")
            resp = self.ser.read_until(b"\n")
            if resp.strip(b"\r\n ") == b"primecam_amp_frontend":
                print("Connected")
            else:
                self.ser.close()
                raise ConnectionError("Primecam RF Frontend Amp Controller didn't respond as expected to an id query")
        else:
            raise ConnectionError("Couldn't open serial port.")

        
    def set_atten(self, addr:int, value : float):
        """
        Sets the attenuator to the provided value.
        :param addr: Channel or address of the attenuator  (0 through 7)
        :param value: Value of the attenuator (0 through 31.75)
        :return: returns bool: True if success/False otherwise.

        If _ENABLE_DEBUG is asserted then a tuple is returned
        """
        self.connect()
        if not self.ser.is_open:
            raise ConnectionError("Not connected to Primecam RF Frontend Amp Controller")
        if self._ASSERTIONS:
            assert value >= 0 and value <= 31.75, "Attenuation out of range (0 through 31.75)"
            assert addr >= 0 and addr <= 7, "Address out of range (0 through 7)"
        atten = int(round(value*4))&0xFF
        address = addr&0xFF
        data = struct.pack('<BB', address, atten)
        self.ser.write(b"set_atten\n")
        self.ser.write(data)
        response = self.ser.read_until(b'\n')
        if response.strip() == b'OK':
            if self._ENABLE_DEBUG:
                return True, "OK", atten
            else:
                return True
        else:
            print(response) if self._ENABLE_DEBUG else None
            msg = response.decode().strip('\n').strip('\r')
            if len(msg) == 0:
                print("Error, device did not respond")
            else:
                return (False, msg) if self._ENABLE_DEBUG else False


    def get_atten(self, addr:int) -> float:
        """
        Returns the attenuator value at the provided address.
        :param addr: Channel or address of the attenuator  (0 through 7)
        :return: The channel's current attenuation setting
        """
        self.connect()
        if not self.ser.is_open:
            raise ConnectionError("Couldn't open serial port.")
        if self._ASSERTIONS:
            assert addr >= 0 and addr <= 7, "Address out of range (0 through 7)"
        self.ser.write(b"get_atten\n")
        data = struct.pack('<B', addr)
        self.ser.write(data)
        response = self.ser.readline()
        rrr = response.decode().strip('\n\r')
        try:
            x = int(rrr)
        except ValueError:
            raise ValueError("Unexpected value returned from microcontroller.")
        return x/4.0


    def close(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.close()

    def open(self):
        if not self.ser.is_open:
            self.ser.open()

    def __enter__(self):
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self._lock.release()




class Transceiver:
    """2024 version.
    """

    def __init__(self, comport) -> None:
        self._ASSERTIONS = True
        self._ENABLE_DEBUG = False
        self._lock = SerialDeviceMutex(comport)
        self.comport = comport
        self.ser = None

    def connect(self):
        if self.ser is not None and self.ser.is_open:
            return
        self.ser = serial.Serial(self.comport, baudrate=115200, timeout=5)
        time.sleep(1.0)
        if self.ser.is_open:
            self.ser.write(b"get_id\n")
            resp = self.ser.read_until(b"\n")
            if resp.strip() == b"transceiver_3.2.1":
                print("Connected")
            else:
                self.ser.close()
                raise ConnectionError("IF Slice didn't respond as expected to an id query")
        else:
            raise ConnectionError("Couldn't open serial port.")

    
    def set_atten(self, addr:int, value : float):
        self.connect()
        if not self.ser.is_open:
            raise ConnectionError("Not connected to IF SLICE")
        if self._ASSERTIONS:
            assert value >= 0 and value <= 31.75, "Attenuation out of range (0 through 31.75)"
            assert addr >= 0 and addr <= 7, "Address out of range (0 through 7)"
        atten = int(round(value*4))&0xFF
        address = addr&0xFF
        data = struct.pack('<BB', address, atten)
        self.ser.write(b"set_atten\n")
        self.ser.write(data)
        response = self.ser.read_until(b'\n')
        if response.strip() == b'OK':
            if self._ENABLE_DEBUG:
                return True, "OK", atten
            else:
                return True, "OK"
        else:
            msg = response.decode().strip('\n').strip('\r')
            if len(msg) == 0:
                print("Error, device did not respond")
            else:
                return False, msg

    def __del__(self):
        if self.ser.is_open:
            self.ser.close()

    def close(self):
        if self.ser.is_open:
            self.ser.close()

    def open(self):
        if not self.ser.is_open:
            self.ser.open()

    def __enter__(self):
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self._lock.release()
