""" Module for calculation of sunrise / sunset

    Based on code from https://en.wikipedia.org/wiki/Sunrise_equation
"""

import logging
from datetime import datetime, timedelta, timezone, tzinfo
from math import acos, asin, ceil, cos, degrees, fmod, radians, sin, sqrt
from time import time
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

class Sun():
    def __init__(self, latitude: float, longitude: float, elevation: float, timezone: str):
        """Constructor for sun class

        Args:
            - `latitude (float)`    : Latitude
            - `longitude (float)`   : Longitude
            - `elevation (float)`   : Elevation
            - `timezone (str)`      : Time Zone
        """
        self._latitude = latitude
        self._longitude = longitude
        self._elevation = elevation
        self._timezone = timezone
        
    def _ts2human(self, ts: float, debugtz: tzinfo) -> str:
        return str(datetime.fromtimestamp(ts, debugtz))


    def _j2ts(self, j: float) -> float:
        return (j - 2440587.5) * 86400


    def _ts2j(self, ts: float) -> float:
        return ts / 86400.0 + 2440587.5


    def _j2human(self, j: float, debugtz: tzinfo) -> str:
        ts = self._j2ts(j)
        return f'{ts} = {self._ts2human(ts, debugtz)}'


    def _deg2human(self, deg: float) -> str:
        x = int(deg * 3600.0)
        num = f'∠{deg:.3f}°'
        rad = f'∠{radians(deg):.3f}rad'
        human = f'∠{x // 3600}°{x // 60 % 60}′{x % 60}″'
        return f'{rad} = {human} = {num}'


    def _calc(
            self,
            current_timestamp: float,
            f: float,
            l_w: float,
            elevation: float = 0.0,
            *,
            debugtz: tzinfo = None,
    ) -> tuple:
        log.debug(f'Latitude               f       = {self._deg2human(f)}')
        log.debug(f'Longitude              l_w     = {self._deg2human(l_w)}')
        log.debug(f'Now                    ts      = {self._ts2human(current_timestamp, debugtz)}')

        J_date = self._ts2j(current_timestamp)
        log.debug(f'Julian date            j_date  = {J_date:.3f} days')

        # Julian day
        # TODO: ceil ?
        n = ceil(J_date - (2451545.0 + 0.0009) + 69.184 / 86400.0)
        log.debug(f'Julian day             n       = {n:.3f} days')

        # Mean solar time
        J_ = n + 0.0009 - l_w / 360.0
        log.debug(f'Mean solar time        J_      = {J_:.9f} days')

        # Solar mean anomaly
        # M_degrees = 357.5291 + 0.98560028 * J_  # Same, but looks ugly
        M_degrees = fmod(357.5291 + 0.98560028 * J_, 360)
        M_radians = radians(M_degrees)
        log.debug(f'Solar mean anomaly     M       = {self._deg2human(M_degrees)}')

        # Equation of the center
        C_degrees = 1.9148 * sin(M_radians) + 0.02 * sin(2 * M_radians) + 0.0003 * sin(3 * M_radians)
        # The difference for final program result is few milliseconds
        # https://www.astrouw.edu.pl/~jskowron/pracownia/praca/sunspot_answerbook_expl/expl-4.html
        # e = 0.01671
        # C_degrees = \
        #     degrees(2 * e - (1 / 4) * e ** 3 + (5 / 96) * e ** 5) * sin(M_radians) \
        #     + degrees(5 / 4 * e ** 2 - (11 / 24) * e ** 4 + (17 / 192) * e ** 6) * sin(2 * M_radians) \
        #     + degrees(13 / 12 * e ** 3 - (43 / 64) * e ** 5) * sin(3 * M_radians) \
        #     + degrees((103 / 96) * e ** 4 - (451 / 480) * e ** 6) * sin(4 * M_radians) \
        #     + degrees((1097 / 960) * e ** 5) * sin(5 * M_radians) \
        #     + degrees((1223 / 960) * e ** 6) * sin(6 * M_radians)

        log.debug(f'Equation of the center C       = {self._deg2human(C_degrees)}')

        # Ecliptic longitude
        # L_degrees = M_degrees + C_degrees + 180.0 + 102.9372  # Same, but looks ugly
        L_degrees = fmod(M_degrees + C_degrees + 180.0 + 102.9372, 360)
        log.debug(f'Ecliptic longitude     L       = {self._deg2human(L_degrees)}')

        Lambda_radians = radians(L_degrees)

        # Solar transit (julian date)
        J_transit = 2451545.0 + J_ + 0.0053 * sin(M_radians) - 0.0069 * sin(2 * Lambda_radians)
        log.debug(f'Solar transit time     J_trans = {self._j2human(J_transit, debugtz)}')

        # Declination of the Sun
        sin_d = sin(Lambda_radians) * sin(radians(23.4397))
        # cos_d = sqrt(1-sin_d**2) # exactly the same precision, but 1.5 times slower
        cos_d = cos(asin(sin_d))

        # Hour angle
        some_cos = (sin(radians(-0.833 - 2.076 * sqrt(elevation) / 60.0)) - sin(radians(f)) * sin_d) / (cos(radians(f)) * cos_d)
        try:
            w0_radians = acos(some_cos)
        except ValueError:
            return None, None, some_cos > 0.0
        w0_degrees = degrees(w0_radians)  # 0...180

        log.debug(f'Hour angle             w0      = {self._deg2human(w0_degrees)}')

        j_rise = J_transit - w0_degrees / 360
        j_set = J_transit + w0_degrees / 360

        log.debug(f'Sunrise                j_rise  = {self._j2human(j_rise, debugtz)}')
        log.debug(f'Sunset                 j_set   = {self._j2human(j_set, debugtz)}')
        log.debug(f'Day length                       {w0_degrees / (180 / 24):.3f} hours')

        return self._j2ts(j_rise), self._j2ts(j_set), None
    
    def sunTimezone(self) -> str:
        """## Return the timezone key used for sun calculations

        ### Returns:
            - `str`: Timezone key
        """
        return self._timezone
    
    def sunrise_sunset(self, time: datetime) -> tuple[datetime, datetime]:
        """Determine sunrise and sunset for a specific date

        Args:
            - `time (datetime)`: Date for which to determine sunrise

        Returns:
            - `datetime`: time of sunrise
        """
        timeTS = datetime.timestamp(time)
        sunriseTS, sunsetTS, err = self._calc(
                timeTS, 
                self._latitude, 
                self._longitude,
                self._elevation,
                debugtz=ZoneInfo(self._timezone)
        )
        sunrise = datetime.fromtimestamp(sunriseTS, ZoneInfo(self._timezone))
        sunset = datetime.fromtimestamp(sunsetTS, ZoneInfo(self._timezone))
        return sunrise, sunset