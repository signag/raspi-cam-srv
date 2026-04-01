# Photo Series of Type "Timelapse"

[![Up](img/goup.gif)](./PhotoSeries.md)

This screen allows special configurations for Photo Series in the Timelapse domain.    
Of course, every normal Photo Series can be used for Timelapse purposes. However, users often require specific features like specific time slots for multi-day series or automatic exposure adjustment during sunset/sunrise phases (Autoramping / "Timelapse Holy Grail").

This page is dedicated to this kind of configuration settings.   
Currently, raspiCamSrv supports the following *Sun-control Mode*s:

- *Sunrise/Sunset*
<br>limiting photo shooting to configurable periods depending on sunrise and sunset.
- *Azimuth*
<br>taking photos at specific azimuth values over a period of days so that photos are taken with the same horizontal direction of sun.

Usage of this feature requires calculation of sunrise and sunset, depending on date.    
The algorithm (see [Sunrise Equation](#sunrise-equation)) requires information about the geografic coordinates of the camera position.   
These need to be specified on the [Settings](./Settings.md) screen before a Series can be classified as "Sun-controlled".   
It is recommended to [store the configuration](./SettingsConfiguration.md#server-configuration-storage) in order to have these settings available after a server restart.

## Sunrise/Sunset Mode

When this screen is activated after a [new Series](./PhotoSeries.md#creation-of-a-new-series) has been created, it will be initialized with *Sunrise/Sunset* mode:

![Timelapse1](./img/PhotoSeriesTL1.jpg)

- The fields **Series**Name, **Interval** and **Number of Shots** refer to the same parameters as screen [Series](./PhotoSeries.md).
- Activating the checkbox **Sun-controlled Series** will activate selective photo shooting in periods depending on sunrise and/or sunset.
- You can specify the **Number of Days** for which the series shall be active
- The fields **Sunrise** and **Sunset** will show values for the current day.<br>If the series will be running for several days, sunrise and sunset will be calculated individually for every day.
- The system allows the definition of two periods per day during which photos will be shot with the given **Interval**:<br>These are named **Period 1** and **Period 2**
- At least for **Period 1**, you need to specify **Start** and **End**<br>If only one is specified, the system reports an error and does not persist the specified data.<br>**Start** and **End** are specified if the **Reference** is not "Unused".
- The **Reference** specifies whether "Sunrise" or "Sunset" will be used to limit the intended period.
- For each **Period**s **Start** and **End**, you can specify a time **Shift** in Minutes by which the start or the end of the period will be shifted with respect to the selected **Reference**.<br>The **Shift** can be positive or negative.
- After **Submit**, the system will calculate **Todays Values** for **Start** and **End**.
- Also the time for the **Next Shot** will be shown.

When submitting entries with a reasonable interval and Number of Days, the system will recalculate the required **Number of Shots** as well as the expected **End** of the Series, shown on the [Series](./PhotoSeries.md) screen.

![Timelapse2](./img/PhotoSeriesTL2.jpg)

### Example: Single Period for Daylight Photos

![Timelapse3](./img/PhotoSeriesTL3.jpg)

### Example: Two Periods around Sunrise and Sunset

![Timelapse4](./img/PhotoSeriesTL4.jpg)

## Azimuth Mode

When choosing *Sun-Control Mode* "Azimuth", the screen layout will change to

![Timelapse5](./img/PhotoSeriesTLAzimuth1.jpg)

- *Time for Azimuth*
<br>can be used to calculate the azimuth at a specific time.
<br>When its value is not explicitely set, it will be updated with the current date/time. 
- *Azimuth [°]*
<br>is the azimuth at the given time
- *Elevation [°]*
<br>is the elevation of the sun above horizon at the given time
- *Azimuth 1*, ... *Azimuth 4*
<br>Here, you can specify up to 4 azimuth values for which photos shall be taken at every day within the specified number of days from series start.
<br>For each value the *Todays Time* at the current day will be calculated when the sun position will have this azimuth.
<br>The system will also verify that azimuth values are valid for the entire period of the series. If this is not the case, an error message will be shown.
<br>When entering more than one azimuth value, these will be sorted with increasing times.


![Timelapse6](./img/PhotoSeriesTLAzimuth.jpg)

### Series Log File

For photo series using *Azimuth* Mode, the [Series Log File](./PhotoSeries.md#series-log-file) will include the Azimuth value for each photo:

![Timelapse7](./img/PhotoSeriesTLAzimuthLog.jpg)



## Sunrise Equation

The algorithm for the sunrise/sunset equation has been taken from Wikipedia:   
[https://en.wikipedia.org/wiki/Sunrise_equation](https://en.wikipedia.org/wiki/Sunrise_equation)

This article also publishes Python code which has been taken as is (version from August 11, 2024, 14:18) and integrated with minor technical adjustments into the RaspiCamSrv Flask server code.

Comparison of the results from this algorithm with those from the "NOAA Solar Calculator" ([https://gml.noaa.gov/grad/solcalc/](https://gml.noaa.gov/grad/solcalc/)) for the time of writing at the author's location showed a deviation of -2 Minutes for sunrise and +3 Minutes for sunset.   
However, the NOAA Calculator does not seem to take elevation into account.