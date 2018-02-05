from functools import partial
from . import cgi
from .info import DEFAULT_MASTERCODE
from .info import WifiMode, WifiModeOnBoot, ModeValue, DriveMode, Config
from .session import Session


def config(param_map, mastercode=DEFAULT_MASTERCODE):
    """Takes a dictionary of {Config.key: value} and
    returns a dictionary of processed keys and values to be used in the
    construction of a POST request to FlashAir's config.cgi"""
    pmap = {Config.mastercode: mastercode}
    pmap.update(param_map)
    processed_params = dict(_process_params(pmap))
    return processed_params


def _process_params(params):
    for param, value in params.items():
        assert param in Config, "Invalid param: {}".format(param)
        yield param.value, value_validators[param](value)


def post(param_map, session: Session = Session()):
    """Posts a `param_map` created with `config` to
    the FlashAir config.cgi entrypoint"""
    prepped_request = _prep_post(url=session.url, **param_map)
    return cgi.send(prepped_request)


_prep_post = partial(cgi.prep_post, cgi.Entrypoint.config)


######################################################
# Functions for creating config POST parameter values

value_validators = {}


def _validator(parameter):
    def wrapper(fn):
        value_validators[parameter] = fn
        return fn
    return wrapper


@_validator(Config.wifi_timeout)
def _validate_timeout(seconds: float):
    """Creates an int from 60000 to 4294967294 that represents a
    valid millisecond wireless LAN timeout"""
    val = int(seconds * 1000)
    assert 60000 <= val <= 4294967294, "Bad value: {}".format(val)
    return val


@_validator(Config.app_info)
def _validate_app_info(info: str):
    assert 1 <= len(info) <= 16
    return info


@_validator(Config.wifi_mode)
def _validate_wifi_mode(mode: ModeValue):
    assert mode in WifiMode or mode in WifiModeOnBoot
    return int(mode)


@_validator(Config.wifi_key)
def _validate_wifi_key(network_key: str):
    assert 0 <= len(network_key) <= 63
    return network_key


@_validator(Config.wifi_ssid)
def _validate_wifi_ssid(network_ssid: str):
    assert 1 <= len(network_ssid) <= 32
    return network_ssid


@_validator(Config.passthrough_key)
def _validate_passthrough_key(network_key: str):
    assert 0 <= len(network_key) <= 63
    return network_key


@_validator(Config.passthrough_ssid)
def _validate_passthroughssid(network_ssid: str):
    assert 1 <= len(network_ssid) <= 32
    return network_ssid


@_validator(Config.mastercode)
def _validate_mastercode(code: str):
    assert len(code) == 12
    code = code.lower()
    valid_chars = "0123456789abcdef"
    assert all(c in valid_chars for c in code)
    return code


@_validator(Config.bootscreen_path)
def _validate_bootscreen_path(path: str):
    return path


@_validator(Config.clear_mastercode)
def _validate_clear_mastercode(_):
    return 1


@_validator(Config.timezone)
def _validate_timezone(hours_offset: int):
    """Creates an int from -48 to 36 that represents the timezone
    offset in 15-minute increments as per the FlashAir docs"""
    param_value = int(hours_offset * 4)
    assert -48 <= param_value <= 36
    return param_value


@_validator(Config.drive_mode)
def _validate_drive_mode(mode: DriveMode):
    assert mode in DriveMode
    return int(mode)
