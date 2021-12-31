import cv2 as cv
import numpy as np
import time
import serial
import sys, os
import pigpio
import RPi.GPIO as GPIO
from sensor import *
from UART import *
from reset import *

sensor_init()
UART_Init()

led_pin = 20
irq_pin = 21
pi = pigpio.pi()
pi.set_mode(led_pin, pigpio.OUTPUT)
pi.write(led_pin, 1)
empty_dict = {
    0: 0,
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0,
    7: 0,
    8: 0
}


# 注册Pin21上升沿为重启程序


def irq_callback(gpio, level, tick):
    sensor_deinit()
    restart_program()


cb1 = pi.callback(irq_pin, pigpio.RISING_EDGE, irq_callback)

# 第一阶段，识别需要去的病房号
res = []
get_goal = False
while (not res) or (not get_goal):
    res = discern()
    try:
        goal = res[0][0][0]
        get_goal = True
    except:
        pass
print(goal)
pi.write(led_pin, 0)

# 目标病房 1为前左 2为前右
# 发送至下位机 2为左转 1为右转 3为直行通过
if goal == 1:
    SendFlags(2)
    # waiting for reset
    while True:
        pass
elif goal == 2:
    SendFlags(1)
    # waiting for reset
    while True:
        pass
else:
    SendFlags(3)
    time.sleep(2)
    # 第二阶段，第一次识别路上病房号的位置
    num_dict = empty_dict.copy()
    while True:
        # start = time.time()
        res = discern()
        try:
            if (res != None):  # and (res[0][0][0] != res[1][0][0]):
                # for each_res in res:
                #     num_dict[each_res[0][0]] += 1
                #     if each_res[0][1]:
                #         left_num = each_res[0][0]
                #     else:
                #         right_num = each_res[0][0]
                if (res[0][0] == None) and (res[1][0] != None):
                    if res[1][0][0] == goal:  # 所需为res1
                        if res[0][1] < res[1][1]:  # 所需在右边
                            SendFlags(0, 1)
                        else:  # 所需在左边
                            SendFlags(0, 2)
                    else:  # 所需为res0
                        if res[0][1] < res[1][1]:  # 所需在左边
                            SendFlags(0, 2)
                        else:  # 所需在右边
                            SendFlags(0, 1)
                elif (res[0][0] != None) and (res[1][0] == None):
                    if res[0][0][0] == goal:  # 所需为res0
                        if res[0][1] < res[1][1]:  # 所需在左边
                            SendFlags(0, 2)
                        else:
                            SendFlags(0, 1)  # 所需在右边
                    else:  # 所需为res1
                        if res[0][1] < res[1][1]:  # 所需在右边
                            SendFlags(0, 1)
                        else:  # 所需在左边
                            SendFlags(0, 2)
                if res[0][1] < res[1][1]:
                    left_num = res[0][0][0]
                    right_num = res[1][0][0]
                else:
                    left_num = res[1][0][0]
                    right_num = res[0][0][0]
                if goal == left_num:
                    SendFlags(0, 2)
                elif goal == right_num:
                    SendFlags(0, 1)
                else:
                    SendFlags(0, 3)
                print(res, left_num)
        except:
            if res != []:
                print(res)

        if cv.waitKey(1) & 0xFF == ord('q'):
            break

        # end = time.time()
        # fps = 1 / (end - start)
        # print(f"fps:{fps}")
