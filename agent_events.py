import getpass
import platform
from datetime import datetime
import pytz
from tzlocal import get_localzone


class AgentEvents:
    @staticmethod
    def create_event(event_type: str, **kwargs):
        event = {
            "version": 0.1,
            "type": event_type,
            **AgentEvents.get_time_metadata(),
            **AgentEvents.get_user_metadata(),
            **kwargs
        }
        return event


    @staticmethod
    def get_time_metadata():
        now_utc = datetime.now(pytz.utc)
        tz_local = get_localzone()
        now_local = now_utc.astimezone(tz_local)

        time_details = {
            "client_timezone": str(tz_local),
            "client_utc_time": str(now_utc),
            "client_local_time": str(now_local),
        }
        return time_details


    @staticmethod
    def get_user_metadata():
        return {
            "user": getpass.getuser(),
            "client_platform": str(platform.platform()),
        }