import cv2 as cv
import numpy as np
import time
import serial

from reset import *

global cap


def sensor_init():
    global cap
    cap = cv.VideoCapture(0)


def sensor_deinit():
    global cap
    cap.release()


def match(pic):
    # 首先匹配正的
    res_list = []
    shape_list = []
    for i in range(1, 9):
        template_pic = cv.imread(f'/home/pi/2021-nuedc-python/letnet_cv/template/{i}-shu.jpg', cv.IMREAD_GRAYSCALE)
        res = cv.matchTemplate(pic, template_pic, cv.TM_SQDIFF)
        res_list.append(cv.minMaxLoc(res)[0])
        shape_list.append(template_pic.shape[:2])
    # 如果没找到匹配的，就匹配横的
    if min(res_list) < 10 * 1000 * 1000:
        index = res_list.index(min(res_list))
        # print(min(res_list))
        return index + 1, shape_list[index]
    else:
        res_list = []
        shape_list = []
        for i in range(1, 9):
            template_pic = cv.imread(f'/home/pi/2021-nuedc-python/letnet_cv/template/{i}-heng.jpg', cv.IMREAD_GRAYSCALE)
            res = cv.matchTemplate(pic, template_pic, cv.TM_SQDIFF)
            res_list.append(cv.minMaxLoc(res)[0])
            shape_list.append(template_pic.shape[:2])
        if min(res_list) < 10 * 1000 * 1000:
            index = res_list.index(min(res_list))
            return index + 1, shape_list[index]
        # else:
        #     res_list = []
        #     shape_list = []
        #     for i in range(1, 9):
        #         template_pic = cv.imread(f'template/{i}-jia.jpg', cv.IMREAD_GRAYSCALE)
        #         res = cv.matchTemplate(pic, template_pic, cv.TM_SQDIFF)
        #         res_list.append(cv.minMaxLoc(res)[0])
        #         shape_list.append(template_pic.shape[:2])
        #     if min(res_list) < 10 * 1000 * 1000:
        #         index = res_list.index(min(res_list))
        #         return index + 1, shape_list[index]


def display(img_list):
    # for i in range(len(img_list)):
    #     cv.imshow(f"{i}", img_list[i])
    pass


def discern():
    global cap
    img_list = []
    _, img = cap.read()
    img_list.append(img)
    # cv.imshow("frame", img)
    # 滤去红色
    # blue_c, green_c, red_c = cv.split(img)
    # lower = np.array([0, 0, 0])
    # upper = np.array([120, 255, 255])
    # red_thresh = cv.inRange(red_c, lower, upper)
    # result_img = cv.merge((blue_c, green_c, red_thresh))
    # lower = np.array([80, 80, 0])
    # upper = np.array([255, 255, 255])
    # red_thresh = cv.inRange(img, lower, upper)
    # cv.imshow("red_thresh", red_thresh)
    # blue_c, green_c, red_c = cv.split(img)
    # red_thresh = cv.merge((blue_c, green_c, green_c))
    # 转换成灰度
    # gray = red_thresh.copy()
    try:
        gray = cv.cvtColor(img.copy(), cv.COLOR_BGR2GRAY)
    except:
        time.sleep(1)
        restart_program()
    # cv.imshow('gray', gray)
    # 平滑滤波
    blur = cv.blur(gray, (3, 3))
    # cv.imshow('blur', blur)
    # 二值化
    _, binary = cv.threshold(blur, 120, 255, cv.THRESH_BINARY)
    # cv.imshow('3', binary)
    # 腐蚀膨胀
    kernel = cv.getStructuringElement(cv.MORPH_RECT, (9, 9))
    erode = cv.erode(binary, kernel)
    # cv.imshow('4', erode)
    dilate = cv.dilate(erode, kernel)
    # cv.imshow('dilate', dilate)
    img_list.append(dilate)
    # 找轮廓
    canny = cv.Canny(dilate, 100, 100 * 3)
    # cv.imshow('canny', canny)
    img_list.append(canny)
    # 找外轮廓 拟合直线
    contours, _ = cv.findContours(canny, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    img_approx = img.copy()
    rect_list = []
    for each_contour in contours:
        rect = cv.minAreaRect(each_contour)
        # box = cv.boxPoints(rect)
        # box = np.int0(box)
        width, height = rect[1]
        box_pixel = width * height
        pic_pixel = cv.contourArea(each_contour)
        found_list = []
        if (3000 < box_pixel < 100000) and (3000 < pic_pixel < 100000):
            if abs((box_pixel - pic_pixel) / box_pixel) < 0.5:
                approx = cv.approxPolyDP(each_contour, 5, True)
                # find out the position of these boxes
                mid_x, mid_y = 0, 0
                i = 0  # if the number of approx is not 4, it is not a rect
                for each_approx in approx:
                    # print(f"approx:{each_approx}")
                    mid_x += each_approx[0][0]
                    mid_y += each_approx[0][1]
                    i += 1
                # if i != 4:
                #     continue
                mid_x /= 4
                mid_y /= 4
                # print(f"middle:{mid_x},{mid_y}")
                found_list.append((mid_x, mid_y))
                # if mid_x < 360:
                #     isLeft = True
                #     # print("左边")
                # else:
                #     isLeft = False
                #     # print("右边")
                # print(" ")
                img_approx = cv.polylines(img_approx, [approx], True, (0, 0, 255), 2)
                rect_list.append((approx, mid_x))
                # print(f"b:{box_pixel},p:{pic_pixel}")
            else:
                # print(f"b:{box_pixel},p:{pic_pixel}")
                pass
        else:
            # print(f"b:{box_pixel},p:{pic_pixel}")
            pass
    img_list.append(img_approx)
    # cv.imshow('approx', img_approx)
    # 透视变幻
    res_list = []
    for each_rect in rect_list:
        try:
            target = np.array([[0., 0.],
                               [0., 120.0],
                               [90.0, 120.0],
                               [90.0, 0.]], dtype=np.float32)
            M = cv.getPerspectiveTransform(np.array(each_rect[0], dtype=np.float32), target)
            perspective = cv.warpPerspective(blur.copy(), M, (90, 120), cv.INTER_LINEAR,
                                             cv.BORDER_CONSTANT)
            img_list.append(perspective)
            # cv.imshow('7', perspective)

            res = match(perspective)
            res_list.append((res, each_rect[1]))
            # if res is not None:
            #     ser.write(res[0])

        # template = cv.imread('template/7-shu.jpg', cv.IMREAD_GRAYSCALE)
        # height, width = template.shape[:2]
        # res = cv.matchTemplate(perspective, template, cv.TM_SQDIFF)
        # min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)
        # print(min_val)
        # left_top = min_loc
        # right_bottom = (left_top[0] + width, left_top[1] + height)
        # cv.rectangle(img=perspective, pt1=left_top, pt2=right_bottom, color=(0, 0, 255), thickness=2)
        # cv.imshow('result', perspective)

        except:
            pass

    display(img_list)
    return res_list
    # ser.write(res[0])
    # if cv.waitKey(1) & 0xFF == ord('q'):
    #     break
