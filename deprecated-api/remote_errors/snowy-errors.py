"""
An exception log handler that posts logs to SnowyEvening issue tracker

Hi there! I'm an example django logging handler for logging errors from django
applications and websites to your account at Snowy-Evening.com.

If you don't have one yet, sign up for a new account at Snowy-Evening.com
and select a plan that enables the remote error logging feature.

Each project will have a unique API Key and Project ID. You will need
both of those pieces for this. They can be found on the Edit Project page.

To use this you will need to register SnowyEveningHandler in settingss.py.
An example configuration is as below:

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse'
            }
        },
        'handlers': {
            'snowy_evening': {
                'level': 'ERROR',
                'filters': ['require_debug_false'],
                'class' : 'path.to.SnowyEveningHandler'
            }
        },
        'loggers': {
            'django.request': {
                'handlers': ['snowy_evening'],
                'level': 'ERROR',
                'propagate': True,
            },
        }
    }

Author: Konrad Lindenbach
Copyright: 2014, Konrad Lindenbach
License: You're free to use this code in any project. You can modify it
         and redistribute it. No warranty is offered for this code.
"""

import logging
import urllib
import json
from time import gmtime, strftime
from hashlib import sha1

from django.views.debug import ExceptionReporter


class SnowyEveningHandler(logging.Handler):

    """
    An exception log handler that posts logs to SnowyEvening issue tracker
    """

    API_KEY = "" # Your API Key here
    APPLICATION = "Test Project"
    BUILD = "Build 55"
    PROJECT_ID = "" #Your Project ID here
    SNOWY_ERROR_URL = "https://snowy-evening.com/api/integration/error_log/"
    VERSION = "1.0"
    VERSION_COMPLETE = "1.0 Beta 1 Build 55"

    def emit(self, record):

        if record.exc_info:
            exc_info = record.exc_info
            reporter = ExceptionReporter(record.request, *exc_info)

            # Create the SnowyEvening stack trace
            frames = [
                {
                    "file" : i['filename'],
                    "line" : i['lineno'],
                    "function" : i['function']
                }
                for i in reporter.get_traceback_frames()[::-1]
            ]

            error_type = exc_info[0].__name__
            error_message = exc_info[0].__name__ + ": " + unicode(exc_info[1])
            file_path = frames[0]['file']
            line = str(frames[0]['line'])
        else:
            exc_info = (None, record.getMessage(), None)
            reporter = ExceptionReporter(record.request, *exc_info)
            frames = []
            error_type = "Logger"
            error_message = "Logger: " + record.getMessage()
            file_path = record.pathname
            line = str(record.lineno)

        # Find visitor IP
        x_forwarded_for = record.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            visitor_ip = x_forwarded_for.split(',')[0]
        else:
            visitor_ip = record.request.META.get('REMOTE_ADDR')

        # prepare request
        payload = {
            "application" : self.APPLICATION,
            "version_complete" : self.VERSION_COMPLETE,
            "version" : self.VERSION,
            "build" : self.BUILD,
            "date" : strftime("%Y-%m-%d %H:%M:%S"),
            "gmdate" : strftime("%Y-%m-%d %H:%M:%S", gmtime()),
            "visitor_ip" : visitor_ip,
            "referrer_url" : record.request.META.get("HTTP_REFERER", ""),
            "request_uri" : record.request.path,
            "user_agent" : record.request.META.get("HTTP_USER_AGENT", ""),
            "error_type" : error_type,
            "error_message" : error_message,
            "error_no" : 500,
            "file" : file_path,
            "line" : line,
            "trace" : frames,
            "additional_info" : reporter.get_traceback_text(),
        }

        # Optionally, you may provide a custom hash of the error that Snowy will
        # use to determine if it's a duplicate or not. By default, Snowy hashes
        # the application, error number, and error message and if that hash
        # matches existing errors, we append the error to that issue instead of
        # making a new one.

        # You may provide your own custom hash that we'll check against your
        # existing issues. The hash may be up to 255 characters long.

        # For example, this will require errors come from the same application,
        # file, and exact line.
        payload['hash'] = sha1(self.APPLICATION + file_path + line).hexdigest()

        params = {
            'payload' : json.dumps(payload),
            'api_key' :  self.API_KEY,
            'project_id' : self.PROJECT_ID,
        }

        # post
        urllib.urlopen(self.SNOWY_ERROR_URL, urllib.urlencode(params))
