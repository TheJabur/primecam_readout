import serial.tools.list_ports
import time
import struct

_ASSERTIONS = True
_ENABLE_DEBUG = False


class Transceiver:
    def __init__(self, comport) -> None:
        self.ser = serial.Serial(comport, baudrate=115200, timeout=5)
        time.sleep(.250)
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
        if not self.ser.is_open:
            raise ConnectionError("Not connected to IF SLICE")
        if _ASSERTIONS:
            assert value >= 0 and value <= 31.75, "Attenuation out of range (0 through 31.75)"
            assert addr >= 0 and addr <= 7, "Address out of range (0 through 7)"
        atten = int(round(value*4))&0xFF
        address = addr&0xFF
        data = struct.pack('<BB', address, atten)
        self.ser.write(b"set_atten\n")
        self.ser.write(data)
        response = self.ser.read_until(b'\n')
        if response.strip() == b'OK':
            if _ENABLE_DEBUG:
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


if __name__ == "__main__":
    print("\nRUNNING TEST CASES\n")
    _ASSERTIONS = False
    _RED = "\033[0;31m"
    _GRN = "\033[0;32m"
    _NC = "\033[0m"
    _PASS = _GRN + "PASS" + _NC
    _FAIL = _RED + "*** FAIL ***" + _NC
    t = Transceiver("/dev/ttyACM0")

    print("\nTESTING FOR SUCCESSFUL COMMAND TO SET ATTENUATION")
    for i in range(0, 7+1):

        result = f"tring to set attenuation for {i};\t\t"
        status, msg = t.set_atten(i, 0.0)
        if status and msg == "OK":
            result = result + _PASS
        else:
            result = result + _FAIL
        print(result)

    print("\nTESTING FOR GRACEFUL FAIL DUE TO INVALID ADDRESS 5 through 10")
    for i in range(8, 20):
        result = f"tring to set attenuation for {i};  \t\t"
        status, msg = t.set_atten(i, 0.0)
        if not status and msg == "FAIL, BAD ADDRESS NOT BETWEEN 0 THROUGH 7":
            result = result + _PASS
        else:
            result = result + _FAIL

        print(result)

    print("\nTESTING FOR VALID ATTENUATION SETTINGS")
    i = 1
    for i in range(0, 127+1):
        v = i/4
        result = f"Setting attenuator {1} to {v};\t\t"
        status, msg = t.set_atten(1, v)
        if status and msg == "OK":
            result = result + _PASS
        else:
            result = result + _FAIL
        print(result)

    print("\nTESTING FOR (IN)VALID ATTENUATION SETTINGS")
    for i in range(128, 256):
        v = i/4
        result = f"Setting attenuator {1} to {v}; expecting an error;\t\t"
        status, msg = t.set_atten(1, v)
        if not status and msg == "FAIL, ATTENUATION VALUE IS TOO LARGE":
            result = result + _PASS
        else:
            result = result + _FAIL
        print(result)

    print("\nTESTING FOR CORRECT ROUNDING OF ATTENUATION SETTINGS")
    attenset = [1.0, 1.11, 1.2 , 1.36, 1.44, 1.78, 1.99]
    expected = [1.0, 1.0,  1.25, 1.25, 1.50, 1.75, 2.0]
    _ENABLE_DEBUG = True
    for i in range(len(attenset)):
        result = f"Setting attenuator {1} to {attenset[i]} which should be rounded to {expected[i]};\t\t"
        status, msg, rnd = t.set_atten(1, attenset[i])
        if status and rnd/4 == expected[i]:
            result = result + _PASS
        else:
            result = result + _FAIL
        print(result)
    _ENABLE_DEBUG = False