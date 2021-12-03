import logging
import sys
import json
import traceback

# init
logging.basicConfig()
logging.root.setLevel(logging.NOTSET)

# reduce verbosity of certain noisy logs
logging.getLogger("oauth2client").setLevel(logging.ERROR)  # too verbose.
logging.getLogger("googleapiclient").setLevel(logging.ERROR)  # too verbose.
logging.getLogger("google_auth_httplib2").setLevel(logging.ERROR)  # too verbose.
logging.getLogger("urllib3").setLevel(logging.ERROR)  # too verbose.


# build custom formatter (GCP will parse JSON log lines from Cloud Run into structured data)
class JsonFormatter(logging.Formatter):
    def format(self, log):
        return json.dumps({
            "level"    : log.levelname,
            "message"  : log.msg,
            "timestamp": self.formatTime(log, self.datefmt),
            "traceback": traceback.format_exc() if log.exc_info else [],
            "log_context": getattr(log, 'context', {})
        })

def add_json_log_streaming(logger):
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = JsonFormatter(datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


