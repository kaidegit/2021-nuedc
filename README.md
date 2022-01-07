# 2021-nuedc
 2021年电赛F题智能送药小车图像部分

## 前言

* 众所周知，电赛时间还是很赶的，所以代码质量可能没能很好的保证，有些乱
* 本代码用的是模板匹配，因为当时对图像以及神经网络不熟，同时选用的树莓派4b没有CUDA，运行YOLO应该会算力不足，帧数太低（测试YOLOX，别人给的模型，R5-3500U运行0.7s/帧）。

## 硬件

* 树莓派4b配CSI摄像头
* 外接USB转串口和单片机（STM32）通讯
* GPIO和单片机RESET连接

## 图像处理

首先，读取摄像头数据然后灰度腐蚀膨胀一梭子，处理完要显示的图像放个list里面方便显示。由于是8g的pi，不担心内存。

```python
    # 转换成灰度
    gray = cv.cvtColor(img.copy(), cv.COLOR_BGR2GRAY)
    # 平滑滤波
    blur = cv.blur(gray, (3, 3))
    # 二值化
    _, binary = cv.threshold(blur, 120, 255, cv.THRESH_BINARY)
    # 腐蚀膨胀
    kernel = cv.getStructuringElement(cv.MORPH_RECT, (9, 9))
    erode = cv.erode(binary, kernel)
    dilate = cv.dilate(erode, kernel)
```

之后就是找外轮廓，根据拟合出来的矩形进行拉伸变换。这里我没有对顶点进行排序，所以可能会产生两种图，似乎对顶点进行排序就可以避免这个问题。（未尝试）

首先当然是canny一下让外框明显。

```python
    canny = cv.Canny(dilate, 100, 100 * 3)
```

然后选出可能是要识别的图像部分。我这边是根据和外接矩形的面积（实际上在图像中是pixel数）比例，外接矩形的大小来共同筛选。在这段代码中同时也返回了合适的外接矩形的中心点坐标返回，用于判断左右（当时似乎没时间做4个图了，就直接对2个图进行了针对性的优化）

```python
	# 找轮廓
    contours, _ = cv.findContours(canny, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    rect_list = []
    # 对每个轮廓进行遍历判断
    for each_contour in contours:
        # 计算轮廓外接矩形面积
        rect = cv.minAreaRect(each_contour)
        width, height = rect[1]
        box_pixel = width * height
        # 计算找出来的轮廓包起来的面积
        pic_pixel = cv.contourArea(each_contour)
        found_list = []
        # 根据外接矩形大小和轮廓与外接矩形面积比来筛选
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
                mid_x /= 4
                mid_y /= 4
                # print(f"middle:{mid_x},{mid_y}")
                found_list.append((mid_x, mid_y))
                img_approx = cv.polylines(img_approx, [approx], True, (0, 0, 255), 2)
                rect_list.append((approx, mid_x))
                # print(f"b:{box_pixel},p:{pic_pixel}")
            else:
                # print(f"b:{box_pixel},p:{pic_pixel}")
                pass
        else:
            # print(f"b:{box_pixel},p:{pic_pixel}")
            pass
```

然后对找出来的合适的图进行透视变换。由于本身是矩形，外接矩形也差不多能抠的准，所以可以直接进行透视变换。然而透视变换会在某些不合适的情况下报错，具体报错emmm不是很想查，毕竟一次识别不出来重新识别即可，帧率也不是很低，而且也没有识别时间的限制。

```python
    # 透视变换
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

            res = match(perspective)
            res_list.append((res, each_rect[1]))
        except:
            pass
```

这之后的图个人看着已经很不错了。

![processed_pic](software/template/1-shu.jpg)

接着是根据图像做匹配，这边用的是模板匹配。

```python
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
```

## 硬件相关

 树莓派毕竟是Linux，底层不会去用类似于CubeMX这种直接配置，而是使用各种接口

### UART

我们使用外置的USB2TTL（CP2102）来和单片机通讯。个人不推荐使用树莓派板载串口，毕竟关了调试串口万一开不开了不好搞。程序主要使用pyserial库

```python
import serial

global ser

def UART_Init():
    global ser
    try:
        port = "/dev/ttyUSB0"
        rate = 115200
        time_out = 5
        ser = serial.Serial(port, rate, timeout=time_out)
    #    ser.write("HelloWorld")
        return True
    except:
        print("UART ERROR")
        return False

```

左和右一个中文一个拼音，更方便迷糊时候分辨（bushi

```python
def SendFlags(flag0=0, flag1=0, flag2=0, flag3=0):
    if (flag0 == 2):
        print("左")
    elif (flag0 == 1):
        print("you")
    else:
        if (flag1 == 2):
            print("左")
        elif (flag1 == 1):
            print("you")
    print(f"({flag0},{flag1},{flag2},{flag3},{flag0 + flag1 + flag2 + flag3})")
    ser.write(f"({flag0}{flag1}{flag2}{flag3}{flag0 + flag1 + flag2 + flag3})".encode())
```

### 摄像头

摄像头我们使用的CSI的摄像头，能降低一点CPU的压力。开启方法具体可自行百度。

### RESET实现

题目中要求仅按一次RESET按键来重新开始运行，所以RESET也要同时重置树莓派。重启树莓派那快1分钟肯定不现实，所以我们飞了跟RESET到GPIO，开中断来重启python程序。

需要注意的是，关闭python前需要关闭摄像头，否则概率性导致重启后摄像头打开失败。

```python
import pigpio

def irq_callback(gpio, level, tick):
    sensor_deinit()
    restart_program()

pi = pigpio.pi()
# 注册中断，上升沿触发
irq_pin = 21
cb1 = pi.callback(irq_pin, pigpio.RISING_EDGE, irq_callback)
```

关闭摄像头函数：

```python
def sensor_deinit():
    global cap
    cap.release()
```

重启函数：

```python
import os,sys

def restart_program():
    """Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function."""
    python = sys.executable
    os.execl(python, python, *sys.argv)
```

### 开机自启的实现

似乎有人说把屏幕和键盘一起封进去就可以不用做这块了，但我还是建议做一下。

简单一点，我推荐一两句的shell就直接放rc.local中就行。不过需要注意的是有些系统默认不开启rc.local的开机执行，需要补全rc-local.service并启用。

rc.local最后添加shell：

```shell
/usr/bin/python3 <your-python-file> &
```

最后一个&表示后台执行python程序，这很重要，不加可能会导致树莓派开机卡死在你的python程序，如果你的程序中有死循环的话。（所以有个可以读写树莓派sd卡的Linux主机/虚拟机很有必要，笑）

记得给rc.local加执行权限（默认似乎是有的）。

直接用`systemctl enable rc-local`开启`rc-local`服务自启会报一些错，类似于下面这样（由于RPi没带回家，暂时拿OPi演示）：

```shell
root@orangepione:~# systemctl enable rc-local
The unit files have no installation config (WantedBy=, RequiredBy=, Also=,
Alias= settings in the [Install] section, and DefaultInstance= for template
units). This means they are not meant to be enabled using systemctl.

Possible reasons for having this kind of units are:
• A unit may be statically enabled by being symlinked from another unit's
  .wants/ or .requires/ directory.
• A unit's purpose may be to act as a helper for some other unit which has
  a requirement dependency on it.
• A unit may be started when needed via activation (socket, path, timer,
  D-Bus, udev, scripted systemctl call, ...).
• In case of template units, the unit is meant to be enabled with some
  instance name specified.
```

service文件一般放在`/usr/lib/systemd/system/`下，打开rc-local.service会发现缺一部分东西（我们随便开一个ssh.service对比下）:

```shell
rc-local.service:

[Unit]
Description=/etc/rc.local Compatibility
Documentation=man:systemd-rc-local-generator(8)
ConditionFileIsExecutable=/etc/rc.local
After=network.target

[Service]
Type=forking
ExecStart=/etc/rc.local start
TimeoutSec=0
RemainAfterExit=yes
GuessMainPID=no


ssh.service:

[Unit]
Description=OpenBSD Secure Shell server
Documentation=man:sshd(8) man:sshd_config(5)
After=network.target auditd.service
ConditionPathExists=!/etc/ssh/sshd_not_to_be_run

[Service]
EnvironmentFile=-/etc/default/ssh
ExecStartPre=/usr/sbin/sshd -t
ExecStart=/usr/sbin/sshd -D $SSHD_OPTS
ExecReload=/usr/sbin/sshd -t
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
Restart=on-failure
RestartPreventExitStatus=255
Type=notify
RuntimeDirectory=sshd
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
Alias=sshd.service
```

缺`[Install]`就把这部分补上即可，直接把ssh服务的这个部分复制过去，Alias别名就别复制了。然后就能`systemctl enable rc-local`了。



## 几个使用树莓派做竞赛的小建议

### 远程开发

个人推荐PyCharm专业版，添加远程解释器。PyCharm的索引计算是在本机，只在前期编制索引时比较吃远程机性能，后面都是靠本机。

VSCode的Remote-SSH，所有东西都靠安装在远程机上的VSCode后端来计算，包括智能感知什么的。由于RPi性能本身不咋的，再加上网络延时，体验不会很好。

VNC。。。。

### 远程调试

这边（图像方向）暂时只讨论看图像显示的结果。

我这边使用了X11-Forwaring来进行图像的回传。由于是无压缩数据，对网络要求似乎有点高，推荐5GWiFi或是千兆有线。我当时使用2.4GWiFi进行调试，因为离路由器距离较远怕干扰什么的，就挺拉跨。

Jupyter似乎有一套自己的图像回传方法，经过压缩的。不过我本次并未使用Jupyter进行开发，暂未研究。





