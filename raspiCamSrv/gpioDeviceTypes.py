
gpioDeviceTypes = [
    {
        "type":"Button",
        "usage":"Input",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_input.html#button",
        "image": "device_button.jpg",
        "params": {
            "pin": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "pull_up": {
                "value": True,
                "type": "boolOrNone"
                },
            "active_state": {
                "value": None,
                "type": "boolOrNone"
                },
            "bounce_time": {
                "value": None,
                "type": "floatOrNone",
                "min": 0.0,
                "max": 10.0
                },
            "hold_time": {
                "value": 1.0,
                "type": "float",
                "min": 0.0,
                "max": 10.0
                },
            "hold_repeat": {
                "value": False,
                "type": "bool"
                }
        },
        "testMethods":[
            "is_pressed",
            "value"
        ],
        "events":[
            "when_pressed",
            "when_released"
        ],
        "control":{
            "bounce_time": 0.0
        }
    },
    {
        "type":"RotaryEncoder",
        "usage":"Input",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_input.html#rotaryencoder",
        "image": "device_RotaryEncoder.jpg",
        "params": {
            "a": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "b": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "bounce_time": {
                "value": None,
                "type": "floatOrNone",
                "min": 0.0,
                "max": 10.0
                },
            "max_steps": {
                "value": 16,
                "type": "int",
                "min": 0,
                "max": 100
                },
            "threshold_steps": {
                "value": (0, 0),
                "type": "tuple(int)"
                },
            "wrap": {
                "value": False,
                "type": "bool"
                }
        },
        "testMethods":[
            "steps",
            "value"
        ],
        "testStepDuration": 3,
        "events":[
            "when_rotated",
            "when_rotated_clockwise",
            "when_rotated_counter_clockwise",
        ],
        "control":{
            "bounce_time": 0.0
        }
    },
    {
        "type":"LightSensor",
        "usage":"Input",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_input.html#lightsensor-ldr",
        "image": "device_LightSensor.jpg",
        "params": {
            "pin": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "queue_len": {
                "value": 5,
                "type": "int",
                "min": 0,
                "max": 100
                },
            "charge_time_limit": {
                "value": 0.01,
                "type": "float",
                "min": 0.0,
                "max": 100.0
                },
            "threshold": {
                "value": 0.1,
                "type": "float",
                "min": 0.0,
                "max": 100.0
                },
            "partial": {
                "value": False,
                "type": "bool"
                }
        },
        "testMethods":[
            "light_detected",
            "value"
        ],
        "events":[
            "when_dark",
            "when_light"
        ],
        "control":{
            "bounce_time": 0.0
        }
    },
    {
        "type":"MotionSensor",
        "usage":"Input",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_input.html#motionsensor-d-sun-pir",
        "image": "device_motionSensor.jpg",
        "params": {
            "pin": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "pull_up": {
                "value": True,
                "type": "boolOrNone"
                },
            "active_state": {
                "value": None,
                "type": "boolOrNone"
                },
            "queue_len": {
                "value": 1,
                "type": "int",
                "min": 0,
                "max": 100
                },
            "sample_rate": {
                "value": 10.0,
                "type": "float",
                "min": 0.0,
                "max": 1000.0
                },
            "threshold": {
                "value": 0.5,
                "type": "float",
                "min": 0.0,
                "max": 1000.0
                },
            "partial": {
                "value": False,
                "type": "bool"
                }
        },
        "testMethods":[
            "motion_detected",
            "value"
        ],
        "events":[
            "when_motion",
            "when_no_motion"
        ],
        "control":{
            "bounce_time": 0.0
        }
    },
    {
        "type":"LineSensor",
        "usage":"Input",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_input.html#linesensor-trct5000",
        "image": "device_LineSensor.jpg",
        "params": {
            "pin": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "pull_up": {
                "value": False,
                "type": "boolOrNone"
                },
            "active_state": {
                "value": None,
                "type": "boolOrNone"
                },
            "queue_len": {
                "value": 5,
                "type": "int",
                "min": 0,
                "max": 100
                },
            "sample_rate": {
                "value": 100.0,
                "type": "float",
                "min": 0.0,
                "max": 1000.0
                },
            "threshold": {
                "value": 0.5,
                "type": "float",
                "min": 0.0,
                "max": 100.0
                },
            "partial": {
                "value": False,
                "type": "bool"
                }
        },
        "testMethods":[
            "value"
        ],
        "events":[
            "when_line",
            "when_no_line"
        ],
        "control":{
            "bounce_time": 0.0
        }
    },
    {
        "type":"DistanceSensor",
        "usage":"Input",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_input.html#distancesensor-hc-sr04",
        "image": "device_DistanceSensor.jpg",
        "params": {
            "echo": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "trigger": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "queue_len": {
                "value": 9,
                "type": "int",
                "min": 0,
                "max": 99
                },
            "max_distance": {
                "value": 1.0,
                "type": "float",
                "min": 0.0,
                "max": 100.0
                },
            "threshold_distance": {
                "value": 0.3,
                "type": "float",
                "min": 0.0,
                "max": 100.0
                },
            "partial": {
                "value": False,
                "type": "bool"
                }
        },
        "testMethods":[
            "distance",
            "value"
        ],
        "events":[
            "when_in_range",
            "when_out_of_range"
        ],
        "eventSettings":{
            "threshold_distance": 0.0
        },
        "control":{
            "bounce_time": 0.0
        }
    },
    {
        "type":"LED",
        "usage":"Output",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_output.html#led",
        "image": "device_LED.jpg",
        "params": {
            "pin": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "active_high": {
                "value": True,
                "type": "bool"
                },
            "initial_value": {
                "value": False,
                "type": "boolOrNone"
                }
        },
        "testMethods":[
            "on",
            "value"
        ],
        "testDuration": 2,
        "actionTargets":[
            {
                "method": "on",
                "params": {},
                "control": {"duration":0.0}
            },
            {
                "method": "off",
                "params": {},
                "control": {}
            }
        ]
    },
    {
        "type":"PWMLED",
        "usage":"Output",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_output.html#pwmled",
        "image": "device_LED.jpg",
        "params": {
            "pin": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "active_high": {
                "value": True,
                "type": "bool"
                },
            "initial_value": {
                "value": 0.0,
                "type": "float",
                "min": 0.0,
                "max": 1.0
                },
            "frequency": {
                "value": "100",
                "type": "int",
                "min": 0,
                "max": 1000
                },
        },
        "testMethods":[
            "on",
            "off",
            "pulse",
            "value",
            "off"
        ],
        "testStepDuration": 2,
        "actionTargets":[
            {
                "method": "on",
                "params": {},
                "control": {"duration":0.0}
            },
            {
                "method": "off",
                "params": {},
                "control": {}
            }
        ]
    },
    {
        "type":"RGBLED",
        "usage":"Output",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_output.html#rgbled",
        "image": "device_RGBLED.jpg",
        "params": {
            "red": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "green": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "blue": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "active_high": {
                "value": True,
                "type": "bool"
                },
            "initial_value": {
                "value": (0.0,0.0,0.0),
                "type": "tuple(float)"
                },
            "pwm": {
                "value": True,
                "type": "bool"
                }
        },
        "testMethods":[
            "on",
            {"color":(1,0,0)},
            {"color":(0,1,0)},
            {"color":(0,0,1)},
            "is_lit",
            "value"
        ],
        "testStepDuration": 1,
        "actionTargets":[
            {
                "method": "value",
                "params": {"value":(0.0,0.0,0.0)},
                "control": {"duration":0.0}
            },
            {
                "method": "off",
                "params": {},
                "control": {}
            }
        ]
    },
    {
        "type":"Buzzer",
        "usage":"Output",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_output.html#buzzer",
        "image": "device_Buzzer.jpg",
        "params": {
            "pin": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "active_high": {
                "value": True,
                "type": "bool"
                },
            "initial_value": {
                "value": False,
                "type": "boolOrNone"
                }
        },
        "testMethods":[
            "on",
            "value"
        ],
        "testDuration": 2,
        "actionTargets":[
            {
                "method": "on",
                "params": {},
                "control": {"duration":0.0}
            },
            {
                "method": "off",
                "params": {},
                "control": {}
            }
        ]
    },
    {
        "type":"TonalBuzzer",
        "usage":"Output",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_output.html#tonalbuzzer",
        "image": "device_TonalBuzzer.jpg",
        "params": {
            "pin": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "initial_value": {
                "value": None,
                "type": "floatOrNone",
                "min": -1.0,
                "max": 1.0
                },
            "mid_tone": {
                "value": 69,
                "type": "int",
                "min": 0,
                "max": 127
                },
            "octaves": {
                "value": 1,
                "type": "int",
                "min": 0,
                "max": 127
                }
        },
        "testMethods":[
            {"play":60},
            {"play":64},
            {"play":67},
            "value",
            "stop"
        ],
        "testStepDuration": 1,
        "actionTargets":[
            {
                "method": "play",
                "params": {"tone":69},
                "control": {"duration":0.0}
            },
            {
                "method": "stop",
                "params": {},
                "control": {}
            }
        ]
    },
    {
        "type":"Servo",
        "usage":"Output",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_output.html#servo",
        "image": "device_Servo.jpg",
        "params": {
            "pin": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "initial_value": {
                "value": 0.0,
                "type": "floatOrNone",
                "min": -1.0,
                "max": 1.0
                },
            "min_pulse_width": {
                "value": 0.001,
                "type": "float",
                "min": 0.0,
                "max": 10000.0
                },
            "max_pulse_width": {
                "value": 0.002,
                "type": "float",
                "min": 0.0,
                "max": 10000.0
                },
            "frame_width": {
                "value": 0.020,
                "type": "float",
                "min": 0.0,
                "max": 10000.0
                }
        },
        "testMethods":[
            "min",
            "max",
            "mid",
            "is_active",
            "value"
        ],
        "testStepDuration": 1,
        "actionTargets":[
            {
                "method": "value",
                "params": {"value":0.0},
                "control": {"duration":0.0, "steps":1}
            },
        ]
    },
    {
        "type":"AngularServo",
        "usage":"Output",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_output.html#angularservo",
        "image": "device_Servo.jpg",
        "params": {
            "pin": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "initial_angle": {
                "value": 0.0,
                "type": "float",
                "min": -90.0,
                "max": 90.0
                },
            "min_angle": {
                "value": -90.0,
                "type": "float",
                "min": -360.0,
                "max": 360.0
                },
            "max_angle": {
                "value": 90.0,
                "type": "float",
                "min": -360.0,
                "max": 360.0
                },
            "min_pulse_width": {
                "value": 0.001,
                "type": "float",
                "min": 0.0,
                "max": 10000.0
                },
            "max_pulse_width": {
                "value": 0.002,
                "type": "float",
                "min": 0.0,
                "max": 10000.0
                },
            "frame_width": {
                "value": 0.020,
                "type": "float",
                "min": 0.0,
                "max": 10000.0
                }
        },
        "testMethods":[
            "min",
            "max",
            "mid",
            "is_active",
            "angle",
            "value"
        ],
        "testStepDuration": 1,
        "actionTargets":[
            {
                "method": "angle",
                "params": {"angle":0.0},
                "control": {"duration":0.0, "steps":1}
            },
        ]
    },
    {
        "type":"Motor",
        "usage":"Output",
        "docUrl": "https://gpiozero.readthedocs.io/en/stable/api_output.html#motor",
        "image": "device_Motor.jpg",
        "params": {
            "forward": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "backward": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "enable": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "pwm": {
                "value": True,
                "type": "bool"
                }
        },
        "testMethods":[
            {"forward":1},
            {"backward":1},
            "stop"
        ],
        "testStepDuration": 3,
        "actionTargets":[
            {
                "method": "forward",
                "params": {"speed":1.0},
                "control": {"duration":0.0, "steps":1}
            },
            {
                "method": "backward",
                "params": {"speed":1.0},
                "control": {"duration":0.0, "steps":1}
            },
            {
                "method": "stop",
                "params": {},
                "control": {}
            }
        ]
    },
    {
        "type":"StepperMotor",
        "usage":"Output",
        "docUrl": "https://github.com/signag/raspi-cam-srv/blob/main/docs/gpioDevices/StepperMotor.md",
        "image": "device_StepperMotor.jpg",
        "params": {
            "in1": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "in2": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "in3": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "in4": {
                "value": "",
                "type": "int",
                "min": 0,
                "max": 27,
                "isPin": True
                },
            "speed": {
                "value": 1.0,
                "type": "float",
                "min": 0.0,
                "max": 1.0,
                },
            "stride_angle": {
                "value": 5.625,
                "type": "float",
                "min": 0.0,
                "max": 360.0,
                },
            "gear_reduction": {
                "value": 64,
                "type": "int",
                "min": 1,
                "max": 1000.0,
                }
        },
        "testMethods":[
            {"rotate_right":90},
            {"rotate_left":90}
        ],
        "testStepDuration": 1,
        "actionTargets":[
            {
                "method": "step_forward",
                "params": {"steps":1},
                "control": {}
            },
            {
                "method": "step_backward",
                "params": {"speed":1},
                "control": {}
            },
            {
                "method": "rotate_right",
                "params": {"angle":1.0},
                "control": {}
            },
            {
                "method": "rotate_left",
                "params": {"angle":1.0},
                "control": {}
            }
        ]
    }    
]