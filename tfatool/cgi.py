import logging
import requests
from functools import partial
from enum import Enum
from urllib.parse import urljoin
from .info import URL


logger = logging.getLogger(__name__)
session = requests.session()


class Entrypoint(str, Enum):
    command = "command.cgi"
    config = "config.cgi"
    upload = "upload.cgi"
    thumbnail = "thumbnail.cgi"


# The requests.PreparedRequest object creation is separated out
# to ease unit testing of CGI functions
# If we just use requests.get and requests.post functions,
# the URL construction is done behind the scenes and we can't test it

def request(method, entrypoint: Entrypoint, url=URL,
            req_kwargs=None, send_kwargs=None, **params):
    prepared_req = prep_request(method, entrypoint, url=url,
                                req_kwargs=req_kwargs, **params)
    send_kwargs = send_kwargs or {}
    return send(prepared_request, **send_kwargs)


def prep_request(method, entrypoint, url=URL, req_kwargs=None, **params):
    resource = urljoin(url, entrypoint)
    req_kwargs = req_kwargs or {}
    request = requests.Request(method, resource, params=params, **req_kwargs)
    prepped = session.prepare_request(request)
    logger.debug("Request: {}".format(prepped.url))
    return prepped


def send(prepped_request, **send_kwargs):
    response = session.send(prepped_request, **send_kwargs)
    logger.debug("Response: {}".format(response))
    return response


prep_get = partial(prep_request, "GET")
get = partial(request, "GET")
prep_post = partial(prep_request, "POST")
post = partial(request, "POST")
