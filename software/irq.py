import sys, os
import time

import pigpio
from sensor import *


# 注册Pin21上升沿为重启程序
# def restart_program():
#     """Restarts the current program.
#     Note: this function does not return. Any cleanup action (like
#     saving data) must be done before calling this function."""
#     python = sys.executable
#     os.execl(python, python, *sys.argv)


def irq_callback(gpio, level, tick):
    sensor_deinit()
    time.sleep(1)
    restart_program()


irq_pin = 21
pi = pigpio.pi()
cb1 = pi.callback(irq_pin, pigpio.RISING_EDGE, irq_callback)
