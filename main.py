import board
import digitalio
import busio
import terminalio
# import storage
import circuitpython_csv as csv
import adafruit_bme680
import adafruit_vl53l0x #ToF sensor
import time
from time import sleep
#display libs
import displayio 
from adafruit_display_text import label
from adafruit_st7789 import ST7789 #display
from adafruit_bitmap_font import bitmap_font

# define constants
temperature_offset = -3
local_Sea_level_press= 1024.25
cali=0 #ToF case offset
acc=33 #ToF acc'y
msmnt_int=55#measurement interval in secs
dough_offset=.8
max_range=400 #if range mm>this is overrange
ToF_samples=6 #No. of samples to be averaged in 1 reading
max_no_msmnts=1000
yscale=280
yfactor=0.75
xscale=6
xfactor=0.75
delay=56

#Initialiseinterfaces
def inithw():# I2C setup
    global vl53,bme680sensor,display,led,local_Sea_level_press
    i2c = busio.I2C(board.GP1, board.GP0, frequency=400000)
    i2c.unlock()
    while not i2c.try_lock():
        pass
        busio.i2c.scan()
        [hex(x) for x in i2c.scan()]  
    print( 
          "I2C addresses found:", [hex(device_address) for device_address in i2c.scan()]
         )
    i2c.unlock()
    vl53 = adafruit_vl53l0x.VL53L0X(i2c, address=0x29)
    bme680sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x77)#bme680 Sensor at 0x77
    bme680sensor.sea_level_pressure = local_Sea_level_press# set location's pressure (hPa) at sea level
    #display setup
    displayio.release_displays()
    spi = busio.SPI(board.GP18, board.GP19)
    tft_cs = board.GP17
    tft_dc = board.GP16
    display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs)
    display = ST7789(display_bus, width=340, height=240, rowstart=5, rotation=90)
# set up pico led ctl
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
# set up file write pin
    write_pin = digitalio.DigitalInOut(board.GP10)
    write_pin.direction = digitalio.Direction.INPUT
    write_pin.pull = digitalio.Pull.UP
    if not write_pin.value:
        text=("file_write_enabled")
        print(text)
    elif write_pin.value:
        text=("not_enabled_to_write")
        print(text) 
    
#initialise consts
def readconsts():    # open file for reading
    global temperature_offset,local_Sea_level_press,cali,acc,msmnt_int,dough_offset,max_range,ToF_samples,max_no_msmnts,delay
    global yscale,yfactor,xscale,xfactor
    with open('consts.txt') as csvDataFile:
        csvReader = csv.reader(csvDataFile)
        for const in csvReader:
            if -10<=int(const[0])<=10:
                temperature_offset=int(const[0])
            if 800<=float(const[1])<=1200:
                local_Sea_level_press=float(const[1])
            if 0<=int(const[2])<=150:
                cali=int(const[2])
            if 1<=int(const[3])<=50:
                acc=int(const[3])
            if 5<=int(const[4])<=300:
                msmnt_int=int(const[4])
            if 0<=float(const[5])<=1.25:
                dough_offset=float(const[5])
            if 200<=int(const[6])<=500:
                max_range=int(const[6])
            if 2<=int(const[7])<=10:
                ToF_samples=int(const[7])
            if 10<=int(const[8])<=1000:
                max_no_msmnts=int(const[8])
            if 1<=float(const[9])<=350:
                yscale=float(const[9])
            if 0.1<=float(const[10])<=.9:
                yfactor=float(const[10])
            if 1<=float(const[11])<=30:
                xscale=float(const[11])
            if 0.1<=float(const[12])<=.9:
                xfactor=float(const[12])
            if 0<=int(const[13])<=200:
                delay=int(const[13])
    return()

def lower():
    lower_bitmap = displayio.Bitmap(270, 50, 1)
    lower_palette = displayio.Palette(1)
    lower_palette[0] = 0x000FFF # no colour
    lower_window = displayio.TileGrid(lower_bitmap,
     pixel_shader=lower_palette,
     x=21, y=185)
    font = bitmap_font.load_font("/SerifPro-Bold-20.bdf")
    text_group = displayio.Group(scale=1, x=5, y=5)
    text = "             "
    global text_area1, text_area2
    text_area1 = label.Label(font, text=text, color=0xFFFF00, x=30, y=180)
    text_group.append(text_area1)
    text_area2 = label.Label(font, text=text, color=0xFFFF00, x=30, y=210)
    text_group.append(text_area2)
    display.show(text_group)
    
#led blink
def blink(speed,flash): #speed is delay in secs
    flash*=2
    while(flash>0):
        led.value = not led.value
        time.sleep(speed/2)
        flash-=1

#Read env seMax_no_msmntsnsor    
def bme680read():
    t = round(bme680sensor.temperature + temperature_offset,1)
    g = bme680sensor.gas
    h = round(bme680sensor.relative_humidity,1)
    p = round(bme680sensor.pressure,1)
    a = round(bme680sensor.altitude,1)
    return t, g, h, p, a  

#ToF Read, returns distance
def readvl53(acc, cali):   
    if acc > 0:
        vl53.measurement_timing_budget = acc*1000
    else:
        vl53.measurement_timing_budget = 33*1000 #default
    if type(cali) == int:
        average=0    
        i=ToF_samples
        while(i>0):
            blink(0.5,1)
            if((vl53.range-cali)<max_range):
                average+= (vl53.range-cali)
                text=("Mean_rdg_count= "+str(i))
#                print(text)
                text_area2.text=text
                i-=1
            else:
                text="OOR_repeating_meas'nt"
                print(text)
                text_area2.text=text

        average/=(ToF_samples)
        text=("mean_d= "+str(average))
        print(text)
        text_area2.text=text
        return average

def log(i,elapsed_time,t,h,g,r,a):  
    try:
        with open("/log.txt", "a") as datalog:
            if True:
                datalog.write("{},{},{},{},{},{}\n".format(elapsed_time,t,h,g,r,a))
                datalog.flush() 
            else:
                while(i<1):
                    text=("Not_able_to_log")
                    print(text)
                    datalog.close()                 
                    return()

    except OSError as e:  # Typically when the filesystem isn't writeable...
        while(i<1):
            delay = 0.5  # ...blink the LED every half second.
            text=("can't_write_log")
            print(text)
            text=("continuing_without")
            print(text)
            if e.args[0] == 28:  # If the filesystem is full...
                delay = 0.25  # ...blink the LED faster!
                text=("memory_full")
                print(text)               
            while True:        
                return()

# display group settup
def dispitd(elapsed_time,t,h,g,r,a):
    lower_bitmap = displayio.Bitmap(270, 50, 1)
    lower_palette = displayio.Palette(1)
    lower_palette[0] = 0x000000 # no colour
    lower_window = displayio.TileGrid(lower_bitmap,
     pixel_shader=lower_palette,
     x=21, y=185)
    font = bitmap_font.load_font("/SerifPro-Bold-20.bdf")
    global text_group
    text_group = displayio.Group(scale=1, x=5, y=5)
    text = "et= " + str(elapsed_time)
    index = label.Label(font, text=text, color=0xFFFF00, x=30, y=180)
    text_group.append(index)
    text = " t= "+ str(t)
    temp = label.Label(font, text=text, color=0xFFFF00, x=125, y=180)
    text_group.append(temp)
    text = " h= "+ str(h)
    dist = label.Label(font, text=text, color=0xFFFF00, x=205, y=180)
    text_group.append(dist)
    text = "g= "+ str(g)
    delta = label.Label(font, text=text, color=0xFFFF00, x=30, y=210)
    text_group.append(delta)
    text = " r= "+ str(r)
    rate = label.Label(font, text=text, color=0xFFFF00, x=110, y=210)
    text_group.append(rate)
    text = " a= "+ str(a)
    accl = label.Label(font, text=text, color=0xFFFF00, x=195, y=210)
    text_group.append(accl)
    display.show(text_group)

def grph(i):
    upper_bitmap = displayio.Bitmap(270,165, 1)
    upper_palette = displayio.Palette(1)
    upper_palette[0] = 0x000000 # no colour
    upper_window = displayio.TileGrid(upper_bitmap,
     pixel_shader=upper_palette,
     x=21, y=10)
    bitmap = displayio.Bitmap(2,2,3)
    palette = displayio.Palette(1)
    palette[0] = 0xFFF000 # green
#autoscale
    
    global yscale,yfactor,xscale,xfactor
    while(160-((g[i]-dough_offset)*yscale)<0):
        yscale*=yfactor
    while((30+i*xscale)>260):
        xscale*=xfactor

#plot
    j=0
    lastx=0
    while(j<=i):
        x=int((30+j*xscale))
        y=int(160-((g[j]-dough_offset)*yscale))
        if(x!=lastx):
            point = displayio.TileGrid(
                bitmap,pixel_shader=palette,x=x, y=y
                )
            text_group.append(point)
        lastx=x
        j+=1
    display.show(text_group)

def wait(text,delay):
    text=text
    print(text)
#    text_area1.text=text
    k=int(delay)
    while(k>0):
        text=("waiting__"+str(k))
        sleep(1)
        text_area2.text=text
        k-=1
    
def main():   
#initialise consts
    global temperature_offset,local_Sea_level_press,cali,acc,msmnt_int,dough_offset,max_range,ToF_samples,max_no_msmnts,yscale,yfactor,xscale,xfactor,delay
    readconsts()
#initialise devices
    inithw()
    global text_area1,text_area2,d,g
    lower()#set up text areas
    dbann=0
    d=[];#thickness of dough
#This section waits for in range reading
    wait("Waiting",delay)
    blink(.25,2)# 2 blinks indicates waiting for in range rdg
    readvl53(acc,cali)#waiting for in range rdg 
    blink(.25,3)# 3 blinks indicates start of measuring banneton
    # wait for 3 readings to be within range and within 5mm
    text=("measure_banneton_base")
    print(text)
    text_area1.text=text
    rdg=[0,0,0,0];
    i=0
    average=float(0)
    while(i<=2):
        rdg[i]=readvl53(acc,cali)
        average+=rdg[i]
        sleep(5)
        if(i>0):
            delta=(rdg[i]-rdg[i-1])
            if((delta**2)>25):
                i=-1# start over
                average=0
        i+=1
    dbann=round(average/3,3)# calc average depth to bottom of banneton
    text=("dbann= "+str(dbann))
    text_area2.text=text
    sleep(5)
#wait for dough to be introduced
    blink(0.25,3)
    text=("Introduce_dough")
    print(text)
    text_area1.text=text
    wait("waiting",delay)
# check 3 readings within 5mm  and in range, measure thickness of dough, store in d[]
    i=0
    average=0
    while(i<=2):
        rdg[i]=readvl53(acc,cali)
        average+=rdg[i]
        sleep(5)
        if(i>0):
            delta=(rdg[i]-rdg[i-1])
            if((delta**2)>25):
                print("rdg[i]= "+str(rdg[i]),"delta= "+str(delta))
                i=-1
        i+=1
    d.append(round((dbann-(average/3)),3))# calc average height of dough
# Rising Phase
    blink(0.5,6)#6 blinks means start of rise phase
    text=("Rising_Phase_starting")
    print(text)
    text_area1.text=text
    start=time.monotonic()#get start time
    text=("start= "+str(start))
    print(text)
    text_area2.text=text
    #initialise data array
    elapsed_time=[];#elapsed rising time
    t=[];#temperature
    h=[];#humidity
    deltad=[];#last change in height
    g=[];#growth ratio
    r=[];#rate of growth
    a=[];#acceleration of growth
    i=0
    while (i<max_no_msmnts):#allows for 500 measurements
        elapsed_time.append(round((time.monotonic()-start)/60,2))
        rdgs=bme680read()
        t.append(rdgs[0])#temp
        h.append(rdgs[2])#humidity
        d.append(round(dbann-readvl53(acc, cali),3))#dough thickness
        if(i==0):
            deltad.append(0)
            g.append(1)
            r.append(0)
            a.append(0)
        else:
            g.append(round((d[i]/d[0]),3))
#            g.append(round(2-10/((i+1)),3))
#            g.append(round((2-i/1000),3))
            deltad.append(round((d[i]-d[i-1]),3))#change in height
            r.append(round(100*(deltad[i]/msmnt_int),3))# rate of growth
            if(i==1):
                a.append(0)
            else:
                a.append(round(100*((r[i]-r[i-1])/(msmnt_int*60)),3))#acceleration in growth         
        print(elapsed_time[i],t[i],h[i],g[i],r[i],a[i])
        dispitd(elapsed_time[i],t[i],h[i],g[i],r[i],a[i])
        log(i,elapsed_time[i],t[i],h[i],g[i],r[i],a[i])
        if(i>0):
            grph(i)
        sleep(msmnt_int)
        print("i= "+str(i))
        i+=1
    text="Max_cycles_reached"
    print(text)
    text_area1.text=text
if __name__ == "__main__":
    main()







