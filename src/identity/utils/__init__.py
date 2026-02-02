from datetime import datetime


def utc_now():
    return datetime.now(datetime.UTC)
