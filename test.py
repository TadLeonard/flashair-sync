import os
import arrow
import tqdm

from urllib import parse
from tfatool.info import Config, WifiMode, DriveMode
from tfatool.info import Upload, WriteProtectMode
from tfatool.config import config
from tfatool import command, upload, util, sync, session


def test_config_construction():
    params = {Config.wifi_ssid: "chiquita"}
    cfg = config(params)
    assert cfg == {"MASTERCODE": "beefbeefbeef", "APPSSID": "chiquita"}


def test_invalid_timeout_value():
    params = {Config.wifi_timeout: 15}  # 15 secs is too short
    try:
        assert config(params)["APPAUTOTIME"] == 15000
    except AssertionError:
        pass
    else:
        assert False, "expected failed assertion"


def test_valid_timeout_value():
    params = {Config.wifi_timeout: 120.5201}
    assert config(params)["APPAUTOTIME"] == 120520


def test_full_config():
    params = {Config.wifi_timeout: 60,
              Config.app_info: "some info is fun",
              Config.wifi_mode: WifiMode.station,
              Config.wifi_key: "supersecret",
              Config.wifi_ssid: "chiquita",
              Config.passthrough_key: "verysecret",
              Config.passthrough_ssid: "officewifi",
              Config.bootscreen_path: "/DCIM/img.jpg",
              Config.mastercode: "BEEFBEEFBEEF",
              Config.clear_mastercode: ...,
              Config.timezone: -5,
              Config.drive_mode: DriveMode.disable,
             }
    assert config(params) == {
                'APPSSID': 'chiquita', 'CIPATH': '/DCIM/img.jpg',
                'BRGNETWORKKEY': 'verysecret', 'WEBDAV': 0,
                'APPINFO': 'some info is fun', 'APPAUTOTIME': 60000,
                'APPMODE': 2, 'APPNETWORKKEY': 'supersecret', 'TIMEZONE': -20,
                'BRGSSID': 'officewifi', 'CLEARCODE': 1,
                'MASTERCODE': 'beefbeefbeef'}


def test_command_cgi_query():
    req = command._prep_get(command.Operation.list_files, DIR="/DCIM/WOMP")
    _, query = parse.splitquery(req.url)
    query_map = parse.parse_qs(query)
    assert query_map == {"DIR": ["/DCIM/WOMP"], "op": ["100"]}


def test_command_cgi_url():
    req = command._prep_get(command.Operation.list_files, DIR="/DCIM/WOMP",
                            url="http://192.168.0.1")
    print(req.url)
    url, _ = parse.splitquery(req.url)
    assert url == "http://192.168.0.1/command.cgi"


def test_datetime_encode_decode():
    ctime = os.stat("README.md").st_ctime
    dtime = arrow.get(ctime)
    dtime = dtime.to("local")

    # encode to FAT32 time
    encoded = upload._encode_time(ctime)

    # decode to arrow datetime
    decoded = command._decode_time(encoded >> 16, encoded & 0xFFFF)

    # accurate down to the second
    for attr in "year month day hour minute".split():
        assert getattr(dtime, attr) == getattr(decoded, attr)

    # seconds are encoded so that they're +- 1
    assert abs(decoded.second - (dtime.second + dtime.microsecond / 10**6)) < 2


def test_datetime_str_encode():
    datetime_val = 0x00340153  # a 32-bit encoded date
    as_string = upload._str_encode_time(datetime_val)
    assert as_string == "0x00340153"


def test_upload_post_url():
    docs_url = "http://flashair/upload.cgi?WRITEPROTECT=ON"  # from docs
    wp = upload.prep_post(**{Upload.write_protect: WriteProtectMode.on})
    assert docs_url == wp.url


def test_upload_post_custom_url():
    docs_url = "http://10.10.3.1/upload.cgi?WRITEPROTECT=ON"  # from docs
    special_session = session.Session(url="10.10.3.1")
    wp = upload.prep_post(**{Upload.write_protect: WriteProtectMode.on},
                          session=special_session)
    assert docs_url == wp.url


def test_datetime_from_month_year():
    dt = util.parse_datetime("11-2015")
    assert dt.year == 2015
    assert dt.month == 11
    assert dt.day == 1
    assert dt.hour == 0
    assert dt.minute == 0
    assert dt.second == 0


def test_datetime_from_year_month():
    dt = util.parse_datetime("2015-11")
    assert dt.year == 2015
    assert dt.month == 11
    assert dt.day == 1
    assert dt.hour == 0
    assert dt.minute == 0
    assert dt.second == 0


def test_datetime_from_year_month_hour_min():
    dt = util.parse_datetime("2015-11 4:11")
    assert dt.year == 2015
    assert dt.month == 11
    assert dt.day == 1
    assert dt.hour == 4
    assert dt.minute == 11
    assert dt.second == 0


def test_datetime_from_month_year_hour_min_sec():
    dt = util.parse_datetime("11-2015 4:11:12")
    assert dt.year == 2015
    assert dt.month == 11
    assert dt.day == 1
    assert dt.hour == 4
    assert dt.minute == 11
    assert dt.second == 12


def test_datetime_from_time_first():
    dt = util.parse_datetime("11:22 2015-04-02")
    assert dt.year == 2015
    assert dt.month == 4
    assert dt.day == 2
    assert dt.hour == 11
    assert dt.minute == 22


def test_datetime_time_only():
    dt = util.parse_datetime("11:22")
    now = arrow.now()
    assert dt.year == now.year
    assert dt.month == now.month
    assert dt.day == now.day
    assert dt.hour == 11
    assert dt.minute == 22
    assert dt.second == 0


def test_datetime_date_only():
    dt = util.parse_datetime("2015-04-1")
    assert dt.second == 0
    assert dt.minute == 0
    assert dt.year == 2015
    assert dt.month == 4
    assert dt.day == 1


def test_datetime_year_only():
    dt = util.parse_datetime("2015")
    assert dt.year == 2015
    assert dt.month == dt.day == 1


def test_datetime_month_day_only():
    dt = util.parse_datetime("4/11")
    assert dt.year == arrow.now().year
    assert dt.month == 4
    assert dt.day == 11
    assert dt.second == 0
    assert dt.minute == 0
    assert dt.hour == 0


def test_pbar_safe_update():
    pbar = tqdm.tqdm(total=10)
    sync._update_pbar(pbar, 1)
    sync._update_pbar(pbar, -1)  # no crash
    sync._update_pbar(pbar, 0)  # no crash

