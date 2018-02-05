import arrow

from operator import attrgetter


def parse_datetime(datetime_input):
    """The arrow library is sadly not good enough to parse
    certain date strings. It even gives unexpected results for partial
    date strings such as '2015-01' or just '2015', which I think
    should be seen as 'the first moment of 2014'.
    This function should overcome those limitations."""
    date_els, time_els = _split_datetime(datetime_input)
    date_vals = _parse_date(date_els)
    time_vals = _parse_time(time_els)
    vals = tuple(date_vals) + tuple(time_vals)
    return arrow.get(*vals)


def _split_datetime(datetime_input):
    dt_input = datetime_input.split(" ")
    if len(dt_input) == 1:
        dt_input.append("")
    date_input, time_input = dt_input
    if ":" in date_input:
        date_input, time_input = time_input, date_input
    if not date_input:
        date_input = arrow.now().format("YYYY-MM-DD")
        sep = "-"
    if not time_input:
        time_input = "00:00:00"

    if "/" in date_input:
        sep = "/"
    elif "-" in date_input:
        sep = "-"
    elif "." in date_input:
        sep = "."
    elif len(date_input) == 4:
        date_input = "{}-01-01".format(date_input)  # assume YYYY
        sep = "-"
    else:
        raise ValueError("Date '{}' can't be understood".format(date_input))
    if time_input and ":" not in time_input:
        raise ValueError("Time '{}' has no ':'-separators".format(time_input))
    d, t = date_input.split(sep), time_input.split(":")
    return tuple(d), tuple(t)


def _parse_date(date_els):
    if len(date_els) == 2:
        # assumed to be year-month or month-year
        a, b = date_els
        if _is_year(a):
            date_vals = a, b, 1  # 1st of month assumed
        elif _is_year(b):
            date_vals = b, a, 1  # 1st of month assumed
        else:
            date_vals = arrow.now().year, a, b  # assumed M/D of this year
    elif len(date_els) == 3:
        # assumed to be year-month-day or month-day-year
        a, b, c = date_els
        if _is_year(a):
            date_vals = a, b, c
        elif _is_year(c):
            date_vals = c, a, b
        else:
            raise ValueError("Date '{}' can't be understood".format(date_els))
    else:
        raise ValueError("Date '{}' can't be understood".format(date_els))
    return map(int, date_vals)


def _parse_time(time_els):
    if len(time_els) == 1:
        time_vals = 0, 0, 0
    elif len(time_els) == 2:
        time_vals = time_els + (0,)  # assumed H:M
    elif len(time_els) == 3:
        time_vals = time_els  # H:M:S
    else:
        raise ValueError("Time '{}' can't be understood".format(time_els))
    return map(int, time_vals)


def _is_year(element):
    return len(element) == 4


def fmt_file_rows(files):
    files = sorted(files, key=attrgetter("datetime"))
    for f in files:
        fname = f.filename
        fdate = f.datetime.format("YYYY-MM-DD")
        ftime = f.datetime.format("HH:mm")
        size = "{:> 3.02f}".format(f.size / 10**6)
        human = f.datetime.humanize()
        yield fname, fdate, ftime, size, human


def get_size_units(nbytes):
    if nbytes >= 10**8:
        units, val = "GB", nbytes / 10**9
    elif nbytes >= 10**5:
        units, val = "MB", nbytes / 10**6
    elif nbytes >= 10**2:
        units, val = "KB", nbytes / 10**3
    else:
        units, val = "B", nbytes
    return val, units
