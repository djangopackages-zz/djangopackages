from datetime import datetime
import time

from django.db import models


def ts_now():
    return int(time.mktime(datetime.utcnow().timetuple()))

class PyPIUpdateLog(models.Model):
    """
    Records our periodic fetches of updated data from PyPI.
    """
    # Seconds since epoch at which we asked for the changelog
    changelog_pulled_ts = models.IntegerField(default=ts_now)

    @classmethod
    def last_update_ts(cls):
        """Returns the most recent update timestamp."""
        last = cls.objects.order_by('-changelog_pulled_ts')[0]
        return last.changelog_pulled_ts
