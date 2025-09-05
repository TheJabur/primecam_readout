import requests
import json
import logging
from logging.handlers import TimedRotatingFileHandler


class PIDConfigException(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class APIError(Exception):
    def __init__(self, jsonData: dict):
        # This is not exactly how described in the API.
        # Lets see, if it works for you.
        if "details" in jsonData["error"]:
            # This assumes we got an details array.
            details = jsonData["error"][details]
        else:
            details = [jsonData["error"]]
        errors = []
        for entry in details:
            errors.append(f"Code: {entry['code']}, Reason: {entry['name']}")
        self._error_messages = errors
        self.query = jsonData["error"]["query"]
        self.query_data = jsonData["error"]["query_data"]
        self.data = jsonData["error"]["data"]
        message = f"{jsonData['error']['name']}: {jsonData['error']['description']}, due to the following errors{''.join(errors)}"
        super().__init__(message)


class BlueFTController:
    """
    A class used to remote control the BlueFors Controller software.


    Attributes
    ----------
    ip : str
        The IP address of the BlueFors Controller server.
    key : str
        The key used for the requests.
    port : int
        The port used for the requests.
    mixing_chamber_channel_id : int
        The channel ID of the mixing chamber.
    mixing_chamber_heater : str
        The heater mapping for the mixing chamber.
    debug : bool
        A flag used to set the log level.
    logger : logging.Logger
        The logger used to log messages.

    Methods
    -------
    _setup_logging():
        Sets up the logger for this class.
    _get_synchronization_status(data: str) -> bool:
        Gets the synchronization status from a data response.
    _get_value_request(device: str, target: str) -> requests.Response:
        Gets the values currently in the Controller config for the given device.
    _get_value_from_data_response(data: str, device: str, target : str) -> Union[float, bool]:
        Gets the value from a data response.
    _set_value_request(device: str, target: str, value: float) -> dict:
        Sets a given target value for a given target device.
    _apply_values_request(device: str) -> dict:
        Applies all changed values for the target device to the device.
    get_channel_data(channel: int, target_value: str) -> dict:
        Gets the specified data from a given channel.
    get_channel_temperature(channel: int) -> float:
        Gets the temperature of the given channel.
    get_channel_resistance(channel: int) -> float:
        Gets the resistance of the given channel.
    get_mxc_temperature() -> float:
        Gets the temperature of the mixing chamber sensor.
    get_mxc_resistance() -> float:
        Gets the resistance of the mixing chamber sensor.
    get_mxc_heater_value(target: str):
        Gets the target value of the mixing chamber heater.
    check_heater_value_synced(target: str) -> bool:
        Checks if the value of the mixing chamber heater is synced.
    set_mxc_heater_value(target: str, value) -> bool:
        Sets the value of the mixing chamber heater.
    get_mxc_heater_status() -> bool:
        Gets the status of the mixing chamber heater.
    set_mxc_heater_status(newStatus: bool) -> bool:
        Sets the status of the mixing chamber heater.
    toggle_mxc_heater(status: str) -> bool:
        Toggles the heater switch.
    get_mxc_heater_power() -> float:
        Gets the power of the mixing chamber heater.
    set_mxc_heater_power(power: float) -> bool:
        Sets the power of the mixing chamber heater.
    get_mxc_heater_setpoint() -> float:
        Gets the setpoint of the mixing chamber heater.
    set_mxc_heater_setpoint(temperature: float) -> bool:
        Sets the setpoint of the mixing chamber heater.
    get_mxc_heater_mode() -> bool:
        Gets the pid mode of the mixing chamber heater.
    set_mxc_heater_mode(toggle: bool) -> bool:
        Sets the pid mode of the mixing chamber heater.
    """

    def __init__(
        self,
        ip: str,
        mixing_chamber_channel_id: int = None,
        port: int = 49098,
        key: str = None,
        debug: bool = False,
    ):
        """
        Constructs all the necessary attributes for the BlueFTController object.

        Parameters
        ----------
            ip : str
                The IP address of the BlueFors Temperature Controller.
            mixing_chamber_channel_id : int
                The channel ID of the mixing chamber (defualt is None).
            port : int, optional
                The port used for the requests (default is 49099).
            key : str, optional
                The key used for the requests (default is None).
            debug : bool, optional
                A flag used to set the log level (default is False).
        """
        self.ip = ip
        self.key = key
        self.port = port
        self.mixing_chamber_channel_id = mixing_chamber_channel_id
        self.mixing_chamber_heater = "mapper.heater_mappings_bftc.device.sample"
        self.debug = debug
        self._setup_logging()
        self._has_mxc = True if mixing_chamber_channel_id is not None else False

    def _setup_logging(self):
        """
        Set up the logger for this class.

        This method creates a logger with the name of the current module and sets the log level based on the `debug` attribute.
        It also creates a `TimedRotatingFileHandler` that rotates the log file at midnight every day and a formatter that includes the timestamp, log level, function name, line number, and message in each log message.
        The file handler and formatter are added to the logger.

        """
        # Create a logger
        self.logger = logging.getLogger(__name__)
        log_level = logging.DEBUG if self.debug else logging.INFO

        # Create a file handler and set level to debug
        file_handler = TimedRotatingFileHandler(
            "bluefors.log", when="W6", interval=1, backupCount=4, encoding="utf-8"
        )
        file_handler.setLevel(log_level)

        # Create a formatter and set the format for log messages
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)-6s - %(funcName)s() L%(lineno)-4d - %(message)s"
        )
        file_handler.setFormatter(formatter)
        # Add the file handler to the logger
        self.logger.addHandler(file_handler)

    def _get_value_from_data_response(self, data: str, device: str, target: str):
        """
        This is a helper function to get the value from a data response.

        Parameters
        ----------
        data : str
            The data response from which to extract the value.
        device : str
            The device identifier used in the data response.
        target : str
            The target identifier used in the data response.

        Returns
        -------
        value : float or bool
            The extracted value from the data response. If the synchronization status cannot be verified, returns False.

        Warns
        ------
        UserWarning
            If the synchronization status cannot be verified, a warning is logged.

        """
        try:
            if not self._get_synchronization_status(data, device=device, target=target):
                print("Warning: The obtained value is not synchronized!")
            return data["data"][f"{device}.{target}"]["content"]["latest_valid_value"]["value"]
        except:
            self.logger.warn(f"Could not verify synchronization status")
            return False

    def _get_synchronization_status(self, data: str, device: str, target: str):
        """
        Get the synchronization status from a data response.

        Parameters
        ----------
        data : str
            The data response from which to extract the synchronization status.
        device : str
            The device identifier used in the data response.
        target : str
            The target identifier used in the data response.

        Returns
        -------
        bool
            True if the data is synchronized, False otherwise or if the synchronization status cannot be verified.

        Warns
        ------
        UserWarning
            If the synchronization status cannot be verified, a warning is logged.

        """
        try:
            return (
                data["data"][f"{device}.{target}"]["content"]["latest_valid_value"]["status"]
                == "SYNCHRONIZED"
            )
        except:
            self.logger.warn(f"Could not verify synchronization status")
            return False

    # general functions
    def _get_value_request(self, device: str, target: str):
        """
        Get the values currently in the Controller config for the given device.

        Parameters
        ----------
        device : str
            The device identifier used in the request.
        target : str
            The target identifier used in the request.

        Raises
        ------
        PIDConfigException
            If no key is provided for the value request.

        Returns
        -------
        response : requests.Response
            The response from the server.

        """
        if self.key == None:
            raise PIDConfigException("No key provided for value request.")
        requestPath = f"https://{self.ip}:{self.port}/values/{device.replace('.','/')}/{target}/?prettyprint=1&key={self.key}"
        self.logger.debug(f"GET: {requestPath}")
        # Let's see if the request was successful, if not, we return a NaN and logg an error
        try:
            response = requests.get(
                requestPath, verify=False
            )  # The server has a self-signed certificate
            response.raise_for_status()
        except (
            requests.exceptions.BaseHTTPError,
            requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
        ) as err:
            self.logger.error(f"Error: {err}")
            # We return data, that indicates NaN and has an ERROR status (and is also otherwse not valid...)
            entry = {
                "data": {
                    "content": {
                        "latest_valid_value": {"value": float("nan"), "status": "ERROR"}
                    }
                }
            }
            return entry
        except Exception as e:
            print(e)
            print(type(e))
            return None
        # Potentially do some type of processing here, depending on what users want.
        return response.json()

    def _set_value_request(self, device: str, target: str, value: float):
        """
        Set a given target value for a given target device.

        This method sends a POST request to the server to set the value of a target on a device.
        The request includes a JSON body with the device, target, and value, and the server's response is returned.

        Parameters
        ----------
        device : str
            The device identifier used in the request.
        target : str
            The target identifier used in the request.
        value : float
            The value to set for the target.

        Raises
        ------
        PIDConfigException
            If no key is provided for the value request.

        Returns
        -------
        response : dict
            The JSON response from the server.

        """
        if self.key == None:
            raise PIDConfigException("No key provided for value request.")
        ## This is a two step process. First, we need to set the value and then we need to call the setter method.
        # This is the body for the setting request.
        request_body = {"data": {f"{device}.{target}": {"content": {"value": value}}}}
        requestPath = (
            f"https://{self.ip}:{self.port}/values/?prettyprint=1&key={self.key}"
        )
        self.logger.debug(f"POST: {requestPath} - Body: {request_body}")
        response = requests.post(
            requestPath,
            data=json.dumps(request_body),
            headers={"Content-Type": "application/json"},
            verify=False,  # Again, self-signed certificate of the server
        )
        response.raise_for_status()

        return response.json()

    def _apply_values_request(self, device: str):
        """
        This method applies all changed values for the target device to the device.
        This is only necessary for some devices, such as the temperature controller,
        where the control unit does not have direct access to the device, but needs
        to update configurations

        Raises
        ------
        PIDConfigException
            If no key is provided for the value request.

        Returns
        -------
        response : dict
            The JSON response from the server.

        """
        if self.key == None:
            raise PIDConfigException("No key provided for value request.")
        # Now we need to call the setter method.
        request_body = {"data": {f"{device}.write": {"content": {"call": 1}}}}
        requestPath = (
            f"https://{self.ip}:{self.port}/values/?prettyprint=1&key={self.key}"
        )
        self.logger.debug(f"POST: {requestPath} - Body: {request_body}")
        response = requests.post(
            requestPath,
            data=json.dumps(request_body),
            headers={"Content-Type": "application/json"},
            verify=False
        )
        response.raise_for_status()

    def get_channel_data(self, channel: int, target_value: str):
        """
        Get the specified data from a given channel

        Parameters
        ----------
        channel : int
            The channel from which to retrieve the data.
        target_value : str
            The target value to retrieve from the channel.

        Returns
        -------
        response : dict
            The JSON response from the server.

        Raises
        ------
        KeyError
            If the response does not contain the expected data.

        """
        device_id = f"mapper.heater_mappings_bftc.device.c{channel}"
        self.logger.info(f"Requesting value: {target_value}  from channel {channel}")
        data = self._get_value_request(device_id, target_value)
        try:
            return self._get_value_from_data_response(
                data, device=device_id, target=target_value
            )
        except KeyError as e:
            raise APIError(data)

    def get_channel_temperature(self, channel: int) -> float:
        """
        Get the temperature of the given channel

        Parameters
        ----------
        channel : int
            The channel from which to retrieve the temperature.

        Returns
        -------
        float
            The temperature of the given channel.

        """
        return float(self.get_channel_data(channel, "temperature"))

    def get_channel_resistance(self, channel: int) -> float:
        """
        Get the temperature of the given channel

        Parameters
        ----------
        channel : int
            The channel from which to retrieve the resistance.

        Returns
        -------
        float
            The resistance of the given channel.

        """
        return float(self.get_channel_data(channel, "resistance"))

    def get_mxc_temperature(self) -> float:
        """
        Get the temperature of the mixing chamber sensor

        Parameters
        ----------
        channel : int
            The channel from which to retrieve the resistance.

        Returns
        -------
        float
            The resistance of the given channel.

        """
        if self._has_mxc:       
            return self.get_channel_temperature(self.mixing_chamber_channel_id)
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def get_mxc_resistance(self) -> float:
        """
        Get the resistance of the mixing chamber sensor

        Returns
        -------
        float
            The resistance of the mixing chamber sensor.

        """
        if self._has_mxc:       
            return self.get_channel_resistance(self.mixing_chamber_channel_id)
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def get_mxc_heater_value(self, target: str):
        """
        Get the target value of the mixing chamber heater

        Parameters
        ----------
        target : str
            The target value to retrieve from the heater.

        Returns
        -------
        float
            The value of the mixing chamber heater.

        Raises
        ------
        KeyError
            If the response does not contain the expected data.

        """
        if self._has_mxc:
        
            data = self._get_value_request(self.mixing_chamber_heater, target)
            try:
                return self._get_value_from_data_response(
                    data, device=self.mixing_chamber_heater, target=target
                )
            except KeyError as e:
                raise APIError(data)
            
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def check_heater_value_synced(self, target: str) -> bool:
        """
        Check if the value of the mixing chamber heater is synced

        Returns
        -------
        bool
            The synchronization status of the target in the mixing chamber heater.

        """
        data = self._get_value_request(self.mixing_chamber_heater, target)
        try:
            return self._get_synchronization_status(
                data, device=self.mixing_chamber_heater, target=target
            )
        except KeyError as e:
            raise APIError(data)

    def set_mxc_heater_value(self, target: str, value):
        """
        Set the value of the mixing chamber heater

        Parameters
        ----------
        target : str
            The target value to retrieve from the heater.

        Returns
        -------
        float
            The value of the mixing chamber heater.

        Raises
        ------
        KeyError
            If the response does not contain the expected data.

        """
        if self._has_mxc:
            self.logger.info(f"Mixing Chamber Heater: Setting {target} to {value}")
            # Set the value
            self._set_value_request(self.mixing_chamber_heater, target, value)
            # Apply the value (otherwise it doesn't get synced to the temperature controller)
            self.logger.info(f"Mixing Chamber Heater: Applying settings")
            self._apply_values_request(self.mixing_chamber_heater)
            synced = self.check_heater_value_synced(target)
            self.logger.info(f"Mixing Chamber Heater: Settings applied and synced")
            return synced
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def get_mxc_heater_status(self) -> bool:
        """
        Get the status of the mixing chamber heater

        Returns
        -------
        bool
            The status of the mixing chamber heater. True if the heater is active, False otherwise.

        """
        if self._has_mxc:
            return self.get_mxc_heater_value("active") == "1"
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def set_mxc_heater_status(self, newStatus: bool) -> bool:
        """
        Get the status of the mixing chamber heater

        Parameters
        ----------
        newStatus : bool
            The new status to set for the heater.

        Returns
        -------
        bool
            True if the status was set successfully, False otherwise.

        """
        if self._has_mxc:
            newValue = "1" if newStatus else "0"
            return self.set_mxc_heater_value("active", newValue)
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def toggle_mxc_heater(self, status: str) -> bool:
        """
        Toggle the heater switch

        Parameters
        ----------
        status : str
            The new status to set for the heater. Must be "on" or "off".

        Returns
        -------
        bool
            True if the status was toggled successfully, False otherwise.

        Raises
        ------
        PIDConfigException
            If an invalid status is provided.

        """
        if self._has_mxc:
            if status == "on":
                newValue = True
            elif status == "off":
                newValue = False
            else:
                raise PIDConfigException("Invalid status provided, must be 'on' or 'off'")
            return self.set_mxc_heater_value(newValue)
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def get_mxc_heater_power(self) -> float:
        """
        Get the power of the mixing chamber heater in microwatts

        Returns
        -------
        float
            The power of the mixing chamber heater.

        """
        if self._has_mxc:
            return float(self.get_mxc_heater_value("power")) * 1000000.0
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def set_mxc_heater_power(self, power: float) -> bool:
        """
        Set the power of the mixing chamber heater
        The provided power is in microwatts

        Parameters
        ----------
        power : float
            The power to set for the heater.

        Returns
        -------
        bool
            True if the power was set successfully, False otherwise.

        """
        if self._has_mxc:
            # Sanity check, should be in microwatts
            if power < 0 or power > 1000:
                raise PIDConfigException(
                    "Power should be in the range of 0 to 1000 microwatts"
                )
            return self.set_mxc_heater_value("power", power / 1000000.0)
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def get_mxc_heater_setpoint(self) -> float:
        """
        Get the setpoint of the mixing chamber heater

        Returns
        -------
        float
            The set point of the mixing chamber heater.

        """
        if self._has_mxc:
            return float(self.get_mxc_heater_value("setpoint"))
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def set_mxc_heater_setpoint(self, temperature: float) -> bool:
        """
        Set the setpoint of the mixing chamber heater in milli Kelvin
        temperature: float

        Parameters
        ----------
        setpoint : float
            The setpoint to set for the heater.

        Returns
        -------
        bool
            True if the setpoint was set successfully, False otherwise.

        """
        if self._has_mxc:
            return self.set_mxc_heater_value("Setpoint", temperature / 1000.0)
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def get_mxc_heater_mode(self) -> bool:
        """
        Get the pid mode of the mixing chamber heater

        Returns
        -------
        bool
            the pid mode of the mixing chamber heater. True if the pid mode is active, False otherwise.
        """
        if self._has_mxc:
            return self.get_mxc_heater_value("pid_mode") == "1"
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')

    def set_mxc_heater_mode(self, toggle: bool) -> bool:
        """
        Set the pid mode of the mixing chamber heater

        Parameters
        ----------
        setpoint : bool
            The mode to set for the heater.

        Returns
        -------
        bool
            True if the mode was set successfully, False otherwise.

        """
        if self._has_mxc:
            newValue = "1" if toggle else "0"
            return self.set_mxc_heater_value("pid_mode", newValue)
        
        else:
            raise Exception('Mixing chamber channel ID not configured.')