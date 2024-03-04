# Release Notes

[![Up](img/goup.gif)](../README.md)

## V2.1.1

### Known issues

- On Pi Zero, there seems to be issues with parallel live stream on *lores* and video recording or phototaking on *main*.   
Got ```Camera frontend has timed out!``` exception.   
Probably, this feature needs to be deactivated on these platforms. Need to study in more details.

### New Features

- The Camera [Information](./Information.md) screen now shows also information on the Raspberry Pi version and board version.

### Bugfix

- For Raspberry Py systems Pi 4 and earlier, the *Stream Format* for *Live view* is initialized with "YUV420".    
According to the [Picamera2 Manual](./picamera2-manual.pdf) ch. 4.2, p. 16, this format must be used for these systems for the *lowres* stream which is now the default for *Live View*.   
The list of values for the *lowres* stream in the [Config](./Configuration.md) dialog is not restricted to YUV format, however, if an other format is selected, an error message is shown and the parameter remains at "YUV420".
- On Bullseye systems (Pi Zero), the package *picamera2.configuration* does not currently include the class *SensorConfiguration*. Also the *CameraConfiguration* class does not contain the element *sensor*.   
This caused an "Import Error" when starting the server.   
This error is now captured and, if it occurs, the *sensor* element in the configuration is ignored.


## V2.1.0

### New Features

- Added endpoint for photo snapshots ([raspi-cam-srv Issue #5](https://github.com/signag/raspi-cam-srv/issues/5))  
(see [Web Cam](./Webcam.md))

## V2.0.0


### New Features

- Major modification of camera control to allow non-exclusive access to the camera from parallel tasks.   
Phototaking, video recording and photoseries do no longer interrupt the live stream if the required camera configurations are compatible.    
(See [raspiCamSrv Tasks and Background Processes](./Background%20Processes.md))
- Added code generation to the camera module.   
The code used for interaction of **raspiCamSrv** with Picamera2 is logged into a file specific for each server run. This generates executable Python code, suitable to 'replay' the entire camera interaction of a raspiCam Server run.    
This can be used for testing and error analysis.   
(See [Generation of Python Code for Camera](./Troubelshooting.md#generation-of-python-code-for-camera))

### Changes

- The camera configuration for VIDEO is now initialized with the sensor mode with the largest stream size in order to allow simultaneous use of main stream for Photo and Video.

### Refactoring

- General refactoring of "Timelapse series" to "Photo Series".   
Timelapse series are now just a special kind of photo series.
- The folder ```raspi-cam-srv/raspiCamSrv/static/timelapse``` is no longer used.   
Instead, photo series are now stored in folder ```raspi-cam-srv/raspiCamSrv/static/photoseries```   
This folder will be automatically created at the first server start.   
If you have stored photoseries under the ```timelapse``` folder, you can move them to the ```photoseries``` folder and then delete the ```timelapse``` folder.   
For each series, you need to exchange ```/timelapse/``` with ```/photoseries/``` in the ```*_cfg.json``` files
