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


# def UART_Send(str):
#     ser.write(str)
#

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
    #pass
    print(f"({flag0},{flag1},{flag2},{flag3},{flag0 + flag1 + flag2 + flag3})")
    ser.write(f"({flag0}{flag1}{flag2}{flag3}{flag0 + flag1 + flag2 + flag3})".encode())
    # UART_Send(f"({flag0},{flag1},{flag2},{flag3})")
