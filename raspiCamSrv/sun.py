""" Module for calculation of sun path properties

    - Sunrise / Sunset times
      (Based on code from https://en.wikipedia.org/wiki/Sunrise_equation)

    - Solar position (azimuth, elevation) dependent on time of day
    - Time(s) when sun has a specific azimuth (e.g. for controlling camera direction)
    
    All calculations are based on the local time of the configured timezone, 
    which is determined by the longitude and the timezone key. The timezone key is used to determine the UTC offset and daylight saving time rules for the location. The calculations take into account the elevation of the location, which affects the sunrise and sunset times. The solar position is calculated using standard astronomical formulas, and the times for specific azimuths are found using a numerical root-finding method (bisection).

    
"""

import logging
from datetime import datetime, timedelta, timezone, tzinfo
from math import acos, asin, ceil, cos, degrees, fmod, radians, sin, sqrt
from time import time
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class Sun():
    def __init__(self, latitude: float, longitude: float, elevation: float, timezone: str):
        """Constructor for sun class

        Args:
            - `latitude (float)`    : Latitude
            - `longitude (float)`   : Longitude
            - `elevation (float)`   : Elevation
            - `timezone (str)`      : Time Zone
        """
        logger.debug('Sun - Creating Sun object with latitude=%s, longitude=%s, elevation=%s, timezone=%s', latitude, longitude, elevation, timezone)
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
        logger.debug(f'Latitude               f       = {self._deg2human(f)}')
        logger.debug(f'Longitude              l_w     = {self._deg2human(l_w)}')
        logger.debug(f'Now                    ts      = {self._ts2human(current_timestamp, debugtz)}')

        J_date = self._ts2j(current_timestamp)
        logger.debug(f'Julian date            j_date  = {J_date:.3f} days')

        # Julian day
        # TODO: ceil ?
        n = ceil(J_date - (2451545.0 + 0.0009) + 69.184 / 86400.0)
        logger.debug(f'Julian day             n       = {n:.3f} days')

        # Mean solar time
        J_ = n + 0.0009 - l_w / 360.0
        logger.debug(f'Mean solar time        J_      = {J_:.9f} days')

        # Solar mean anomaly
        # M_degrees = 357.5291 + 0.98560028 * J_  # Same, but looks ugly
        M_degrees = fmod(357.5291 + 0.98560028 * J_, 360)
        M_radians = radians(M_degrees)
        logger.debug(f'Solar mean anomaly     M       = {self._deg2human(M_degrees)}')

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

        logger.debug(f'Equation of the center C       = {self._deg2human(C_degrees)}')

        # Ecliptic longitude
        # L_degrees = M_degrees + C_degrees + 180.0 + 102.9372  # Same, but looks ugly
        L_degrees = fmod(M_degrees + C_degrees + 180.0 + 102.9372, 360)
        logger.debug(f'Ecliptic longitude     L       = {self._deg2human(L_degrees)}')

        Lambda_radians = radians(L_degrees)

        # Solar transit (julian date)
        J_transit = 2451545.0 + J_ + 0.0053 * sin(M_radians) - 0.0069 * sin(2 * Lambda_radians)
        logger.debug(f'Solar transit time     J_trans = {self._j2human(J_transit, debugtz)}')

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

        logger.debug(f'Hour angle             w0      = {self._deg2human(w0_degrees)}')

        j_rise = J_transit - w0_degrees / 360
        j_set = J_transit + w0_degrees / 360

        logger.debug(f'Sunrise                j_rise  = {self._j2human(j_rise, debugtz)}')
        logger.debug(f'Sunset                 j_set   = {self._j2human(j_set, debugtz)}')
        logger.debug(f'Day length                       {w0_degrees / (180 / 24):.3f} hours')

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

    def _day_of_year(self, dt: datetime) -> int:
        """Day number in the year (1. January = 1)."""
        return dt.timetuple().tm_yday

    def _equation_of_time(self, N: int) -> float:
        """Equation of time in minutes for day number N.

        Approximation formula according to Spencer (1971).
        """
        B = radians(360 / 365 * (N - 81))
        E = 9.87 * sin(2 * B) - 7.53 * cos(B) - 1.5 * sin(B)
        return E  # Minuten

    def _declination(self, N: int) -> float:
        """Solar declination in degrees for day number N."""
        return -23.45 * cos(radians(360 / 365 * (N + 10)))

    def solar_position(
        self,
        dt: datetime,
        log: bool = True,
    ) -> dict:
        """Calculate solar azimuth and elevation.

        Parameters
        ----------
        dt          : datetime  - Local date/time

        Returns
        -------
        dict with:
            azimuth       - Azimuth in degrees (0 = North, 90 = East, 180 = South, 270 = West)
            elevation     - Sun elevation in degrees (negative = below horizon)
            hour_angle    - Hour angle in degrees
            declination   - Declination in degrees
            solar_time    - True solar time as a string
        """
        if log:
            logger.debug("sun.solar_position - Calculating solar position for datetime: %s", dt)
        dt = dt.astimezone(ZoneInfo(self._timezone))
        N = self._day_of_year(dt)
        local_time_hours = dt.hour + dt.minute / 60 + dt.second / 3600
        utc_offset = dt.utcoffset().total_seconds() / 3600

        # Time correction: longitude correction + equation of time
        ref_longitude = utc_offset * 15  # Reference meridian of the timezone
        longitude_correction = (self._longitude - ref_longitude) * 4 / 60  # Hours
        E_hours = self._equation_of_time(N) / 60

        # True solar time (TST)
        solar_time = local_time_hours + longitude_correction + E_hours

        # Hour angle H (0 = noon, negative = morning, positive = afternoon)
        H = (solar_time - 12) * 15  # Degrees

        # Declination
        delta = self._declination(N)

        # Auxiliary values in radians
        phi = radians(self._latitude)
        delta_r = radians(delta)
        H_r = radians(H)

        # Solar elevation
        sin_alpha = (
            sin(phi) * sin(delta_r)
            + cos(phi) * cos(delta_r) * cos(H_r)
        )
        sin_alpha = max(-1.0, min(1.0, sin_alpha))
        alpha = degrees(asin(sin_alpha))

        # Azimuth
        cos_alpha = cos(radians(alpha))
        if cos_alpha < 1e-10:
            azimuth = 0.0
        else:
            cos_A = (sin(delta_r) - sin(phi) * sin_alpha) / (
                cos(phi) * cos_alpha
            )
            cos_A = max(-1.0, min(1.0, cos_A))
            A = degrees(acos(cos_A))
            # Afternoon: Azimuth > 180
            azimuth = 360 - A if H > 0 else A

        # True solar time as a readable string
        solar_h = int(solar_time) % 24
        solar_m = int((solar_time - int(solar_time)) * 60)
        solar_s = int(((solar_time - int(solar_time)) * 60 - solar_m) * 60)
        solar_time_str = f"{solar_h:02d}:{solar_m:02d}:{solar_s:02d}"

        if log:
            logger.debug("sun.solar_position - Calculated solar position: azimuth=%.2f°, elevation=%.2f°, hour_angle=%.2f°, declination=%.2f°, solar_time=%s", azimuth, alpha, H, delta, solar_time_str)
        return {
            "azimuth": round(azimuth, 2),
            "elevation": round(alpha, 2),
            "hour_angle": round(H, 2),
            "declination": round(delta, 2),
            "solar_time": solar_time_str,
        }


    def _get_az(self, base: datetime, minutes_from_midnight: float) -> float:
        """Azimuth at a specific minute of the day."""
        dt = base + timedelta(minutes=minutes_from_midnight)
        return self.solar_position(dt, log=False)["azimuth"]

    def _az_diff(self, base: datetime, minutes: float, target_azimuth: float) -> float:
        """Differenz zwischen aktuellem und Ziel-Azimut, zirkulaer normiert."""
        diff = self._get_az(base, minutes) - target_azimuth
        # Zirkulaere Normierung: -180 bis +180
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
        return diff

    def _bisect(self, base: datetime, t_lo: float, t_hi: float, target_azimuth: float, tol: float = 0.5) -> float | None:
        """Bisektionsverfahren zur Nullstellensuche."""
        f_lo = self._az_diff(base, t_lo, target_azimuth)
        f_hi = self._az_diff(base, t_hi, target_azimuth)
        if f_lo * f_hi > 0:
            return None
        for _ in range(40):  # max. 40 Iterations -> about 0.001 Min. Precision
            t_mid = (t_lo + t_hi) / 2
            f_mid = self._az_diff(base, t_mid, target_azimuth)
            if abs(t_hi - t_lo) < tol / 60: 
                return t_mid
            if f_lo * f_mid <= 0:
                t_hi, f_hi = t_mid, f_mid
            else:
                t_lo, f_lo = t_mid, f_mid
        return (t_lo + t_hi) / 2

    def find_times_for_azimuth(
        self,
        date: datetime,
        target_azimuth: float,
        min_elevation: float = 0.0,
    ) -> list[dict]:
        """ Calculate the time(s) when the sun has a specific azimuth.
        This method uses a numerical root-finding approach (bisection method)
        to find the time(s) when the sun's azimuth matches the target value.
        Method: Numerical root-finding (bisection method)
        The sign behavior of (azimuth(t) - target) is used to narrow down
        the roots to hour- or minute-level accuracy.

        Parameters
        ----------
        date           : datetime  - Date (time is ignored)
        target_azimuth : float     - Target azimuth in degrees (0-360)
        min_elevation  : float     - Minimum sun elevation (default: 0 = above horizon)

        Returns
        -------
        List of dicts with:
            time       - datetime object
            time_str   - Time as HH:MM:SS
            azimuth    - Actual azimuth at the time
            elevation  - Sun elevation in degrees
            side       - "Morning" or "Afternoon"
        """
        logger.debug("sun.find_times_for_azimuth - Finding times for target azimuth %s° on date %s with min elevation %s°", target_azimuth, date, min_elevation)    
        results = []
        date = date.astimezone(ZoneInfo(self._timezone))
        base = date.replace(hour=0, minute=0, second=0, microsecond=0)
        utc_offset = date.utcoffset().total_seconds() / 3600

        # Sampling every 15 minutes for the entire day
        step = 15  # Minutes
        samples = [(t, self._az_diff(base, t, target_azimuth)) for t in range(0, 1440 + step, step)]

        # Look for sign changes -> potential roots
        found_times = set()
        for i in range(len(samples) - 1):
            t0, d0 = samples[i]
            t1, d1 = samples[i + 1]
            if d0 == 0.0:
                # Exact match at t0
                found_times.add(round(t0 * 60))  # Round to nearest second
            elif d1 == 0.0:
                # Exact match at t1
                found_times.add(round(t1 * 60))  # Round to nearest second
            else:
                if d0 * d1 < 0:
                    t_exact = self._bisect(base, t0, t1, target_azimuth)
                    if t_exact is not None:
                        # Round to the nearest second
                        t_rounded_sec = round(t_exact * 60)
                        if t_rounded_sec not in found_times:
                            found_times.add(t_rounded_sec)

        # Prepare results
        for t_sec in sorted(found_times):
            dt_result = base + timedelta(seconds=t_sec)
            pos = self.solar_position(dt_result, log=False)
            logger.debug("sun.find_times_for_azimuth - Found potential time: %s with azimuth %.2f° and elevation %.2f°", dt_result, pos["azimuth"], pos["elevation"])

            if pos["elevation"] < min_elevation:
                continue

            if abs(pos["azimuth"] - target_azimuth) > 0.5:
                continue

            h = dt_result.hour
            m = dt_result.minute
            s = dt_result.second

            results.append({
                "time": dt_result,
                "time_str": f"{h:02d}:{m:02d}:{s:02d}",
                "azimuth": round(pos["azimuth"], 2),
                "elevation": round(pos["elevation"], 2),
                "side": "Morning" if pos["hour_angle"] < 0 else "Afternoon",
            })
        logger.debug("sun.find_times_for_azimuth - Found %s", results)
        return results

if __name__ == "__main__":
    # Example usage
    latitude = 48.85827
    longitude = 2.29451
    elevation = 52.0
    tz = "Europe/Paris"
    dt_str = "2026-03-24 13:05"
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    print(f"latitude: {latitude}, longitude: {longitude}, elevation: {elevation}m")
    print(f"Timezone: {tz}")
    print(f"Time: {dt}")
    sun = Sun(latitude=latitude, longitude=longitude, elevation=elevation, timezone=tz)
    sunrise, sunset = sun.sunrise_sunset(dt)
    print(f"Sunrise: {sunrise}, Sunset: {sunset}")
    print("\n  Solar position:")
    pos = sun.solar_position(dt)
    print(pos)
    azimuth = pos["azimuth"]
    print(f"\n  Times when sun has azimuth {azimuth}°:")
    times = sun.find_times_for_azimuth(date=dt, target_azimuth=azimuth, min_elevation=0.0)
    for t in times:
        print(t)