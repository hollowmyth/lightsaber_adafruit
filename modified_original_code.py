"""LASER SWORD (pew pew) example for Adafruit Hallowing & NeoPixel strip"""
# pylint: disable=bare-except

import time
import math
import gc
from digitalio import DigitalInOut, Direction, Pull
import adafruit_sdcard
import storage
import audioio
import audiocore
import audiomixer
import busio
import board
import neopixel
import adafruit_lis3dh
from adafruit_debouncer import Debouncer
import random
import json

# CUSTOMIZE YOUR COLOR HERE:
# (red, green, blue) -- each 0 (off) to 255 (brightest)
# COLOR = (100, 0, 255)  # purple
# COLOR = (0, 100, 255) #cyan
COLOR = (255, 0, 0) #red
# COLOR = (205, 205, 205) #white
#COLOR = (60, 240, 0) #green
#COLOR = (0, 0, 230) #blue

# CUSTOMIZE SENSITIVITY HERE: smaller numbers = more sensitive to motion
HIT_THRESHOLD = 30 # 250
SWING_THRESHOLD = 10

NUM_PIXELS = 132
# NUM_PIXELS = 85
NEOPIXEL_PIN = board.D5
POWER_PIN = board.D10
SWITCH_PIN = board.D9

enable = DigitalInOut(POWER_PIN)
enable.direction = Direction.OUTPUT
enable.value =False

red_led = DigitalInOut(board.D11)
red_led.direction = Direction.OUTPUT
green_led = DigitalInOut(board.D12)
green_led.direction = Direction.OUTPUT
blue_led = DigitalInOut(board.D13)
blue_led.direction = Direction.OUTPUT

audio = audioio.AudioOut(board.A0)     # Speaker
mixer = audiomixer.Mixer(voice_count=3, sample_rate=44100, buffer_size=2048, channel_count=1,bits_per_sample=16, samples_signed=True)
audio.play(mixer)
mode = 0                               # Initial mode = OFF

strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False)
strip.fill(0)                          # NeoPixels off ASAP on startup
strip.show()

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = DigitalInOut(board.D4)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

pin = DigitalInOut(SWITCH_PIN)
pin.direction = Direction.INPUT
pin.pull = Pull.UP
switch = Debouncer(pin, interval=0.05)

time.sleep(0.1)

# Set up accelerometer on I2C bus, 4G range:
i2c = busio.I2C(board.SCL, board.SDA)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c)
accel.range = adafruit_lis3dh.RANGE_4_G



S = open('/sd/Settings.json')
settings = json.load(S)
currPreset = settings['currPreset']
#currVolume = settings.currVolume
#Volume = settings.Volume[c]
#customBladeColor = settings['customBladeColor']
S.close
print(settings)
currPreset = 1
print(currPreset)
print(type(currPreset))
P = open('/sd/Presets.json')
Presets = json.load(P)
P.close
totalPresets = len(Presets['presets'])
presetName = Presets['presets'][currPreset]['name']
COLOR = Presets['presets'][currPreset]['bladeColor']
humNums  = Presets['presets'][currPreset]['hum']
fontNums = Presets['presets'][currPreset]['font']
outNums = Presets['presets'][currPreset]['outSounds']
inNums = Presets['presets'][currPreset]['inSounds']
blstNums = Presets['presets'][currPreset]['blstSounds']
clshNums = Presets['presets'][currPreset]['clshSounds']
swngNums = Presets['presets'][currPreset]['swngSounds']

# "Idle" color is 1/4 brightness, "swinging" color is full brightness...
COLOR_IDLE = (int(COLOR[0] / 1), int(COLOR[1] / 1), int(COLOR[2] / 1))
COLOR_SWING = COLOR
COLOR_HIT = (255, 255, 255)  # "hit" color is white

def update_preset():
    currPreset = settings['currPreset']
    presetName = Presets['presets'][currPreset]['name']
    COLOR = Presets['presets'][currPreset]['bladeColor']
    humNums  = Presets['presets'][currPreset]['hum']
    fontNums = Presets['presets'][currPreset]['font']
    outNums = Presets['presets'][currPreset]['outSounds']
    inNums = Presets['presets'][currPreset]['inSounds']
    blstNums = Presets['presets'][currPreset]['blstSounds']
    clshNums = Presets['presets'][currPreset]['clshSounds']
    swinghNums = Presets['presets'][currPreset]['swngSounds']
    COLOR_IDLE = COLOR
    COLOR_SWING = COLOR

def next_preset(int1):
    int1 += 1
    if int1 > totalPresets - 1:
        int1 = 0
    settings['currPreset'] = int1

    with open("/sd/test.txt", "w") as f:
        #f.write("Hello world!\r\n")
        json.dump(settings, f)

    #f = open('/sd/Settings.json', 'w')
    #json.dump(settings, f)
    f.close
    update_preset()

def prev_preset(int1):
    int1 -= 1
    if int1 < 0:
        int1 = totalPresets
    settings['currPreset'] = int1

    with open("/sd/test.txt", "w") as f:
        #f.write("Hello world!\r\n")
        json.dump(settings, f)

    #f = open('/sd/Settings.json', 'w')
    #json.dump(settings, f)
    f.close
    update_preset()

def choose_random(num):
    random_num = random.randint(1,num)
    if random_num < 10:
        random_num = ('0'+str(random_num))
    else:
        random_num = (str(random_num))
    return(random_num)

def build_name(name, num):
    rand_num = choose_random(num)
    fileName = name + '/' + name + rand_num + '.wav'
    return(fileName)

def play_wav(name, voice, num, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    @param name: partial file name string, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    @param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    
    mixer.voice[voice].stop()
    try:
        built_name = build_name(name, num)
        print("1-building name")
        openFile = '/sd/' + presetName +'/' + built_name
        print("filename: " + openFile)
        wave_file = open(openFile, 'rb')
        print("2-open sd")
        wave = audiocore.WaveFile(wave_file)
        print("3-select file")
        #audio.play(mixer)
        mixer.voice[voice].level = .4
        mixer.voice[voice].play(wave,loop=loop)
        print("4-playing", openFile)
        #audio.play(wave, loop=loop)
    except:
        print('error in playing ' + built_name)
        return
        
def play_wav1(name, voice, num, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    @param name: partial file name string, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    @param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    
    mixer.voice[voice].stop()
    try:
        built_name = build_name(name, num)
        print("1-building name")
        openFile = '/sd/' + presetName +'/' + built_name
        print("filename: " + openFile)
        wave_file = open(openFile, 'rb')
        print("2-open sd")
        wave = audiocore.WaveFile(wave_file)
        print("3-select file")
        #audio.play(mixer)
        mixer.voice[voice].level = .4
        mixer.voice[voice].play(wave,loop=loop)
        print("4-playing", openFile)
        #audio.play(wave, loop=loop)
    except:
        print('error in playing ' + built_name)
        return
def play_wav2  (name, voice, num, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    @param name: partial file name string, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    @param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    
    mixer.voice[voice].stop()
    try:
        built_name = build_name(name, num)
        print("1-building name")
        openFile = '/sd/' + presetName +'/' + built_name
        print("filename: " + openFile)
        wave_file = open(openFile, 'rb')
        print("2-open sd")
        wave = audiocore.WaveFile(wave_file)
        print("3-select file")
        #audio.play(mixer)
        mixer.voice[voice].level = .4
        mixer.voice[voice].play(wave,loop=loop)
        print("4-playing", openFile)
        #audio.play(wave, loop=loop)
    except:
        print('error in playing ' + built_name)
        return

def powerOn(sound, voice, duration):
    """
    Animate NeoPixels with accompanying sound effect for power on / off.
    @param sound:    sound name (similar format to play_wav() above)
    @param duration: estimated duration of sound, in seconds (>0.0)
    @param reverse:  if True, do power-off effect (reverses animation)
    """
    prev = 0
    gc.collect()                   # Tidy up RAM now so animation's smoother
    start_time = time.monotonic()  # Save audio start time
    num = outNums
    play_wav(sound, voice, num)
    while True:

        elapsed = time.monotonic() - start_time  # Time spent playing sound
        if elapsed > duration:                   # Past sound duration?
            break                                # Stop animating
        fraction = elapsed / duration            # Animation time, 0.0 to 1.0
        fraction = math.pow(fraction, 0.5)       # Apply nonlinear curve
        threshold = int(NUM_PIXELS * fraction + 0.5)
        num = threshold - prev # Number of pixels to light on this pass
        if num != 0:
            strip[prev:threshold] = [COLOR_IDLE] * num
            strip.show()
            # NeoPixel writes throw off time.monotonic() ever so slightly
            # because interrupts are disabled during the transfer.
            # We can compensate somewhat by adjusting the start time
            # back by 30 microseconds per pixel.
            start_time -= NUM_PIXELS * 0.00003
            prev = threshold

    strip.fill(COLOR_IDLE)                   # or all pixels set on
    strip.show()
    while mixer.voice[voice].playing:                         # Wait until audio done
        pass

def powerOff(sound, voice, duration):
    prev = NUM_PIXELS
    gc.collect()                   # Tidy up RAM now so animation's smoother
    start_time = time.monotonic()  # Save audio start time
    num = inNums
    play_wav(sound, voice, num)
    while True:

        elapsed = time.monotonic() - start_time  # Time spent playing sound
        if elapsed > duration:                   # Past sound duration?
            break                                # Stop animating
        fraction = elapsed / duration            # Animation time, 0.0 to 1.0
        fraction = 1.0 - fraction            # 1.0 to 0.0 if reverse
        fraction = math.pow(fraction, 0.5)       # Apply nonlinear curve
        threshold = int(NUM_PIXELS * fraction + 0.5)
        num = threshold - prev # Number of pixels to light on this pass
        if num != 0:
            strip[threshold:prev] = [0] * -num
            strip.show()
            # NeoPixel writes throw off time.monotonic() ever so slightly
            # because interrupts are disabled during the transfer.
            # We can compensate somewhat by adjusting the start time
            # back by 30 microseconds per pixel.
            start_time -= NUM_PIXELS * 0.00003
            prev = threshold

    strip.fill(0)                            # At end, ensure strip is off
    strip.show()
    while mixer.voice[voice].playing:                         # Wait until audio done
        pass


def mix(color_1, color_2, weight_2):
    """
    Blend between two colors with a given ratio.
    @param color_1:  first color, as an (r,g,b) tuple
    @param color_2:  second color, as an (r,g,b) tuple
    @param weight_2: Blend weight (ratio) of second color, 0.0 to 1.0
    @return: (r,g,b) tuple, blended color
    """
    if weight_2 < 0.0:
        weight_2 = 0.0
    elif weight_2 > 1.0:
        weight_2 = 1.0
    weight_1 = 1.0 - weight_2
    return (int(color_1[0] * weight_1 + color_2[0] * weight_2),
            int(color_1[1] * weight_1 + color_2[1] * weight_2),
            int(color_1[2] * weight_1 + color_2[2] * weight_2))

# Main program loop, repeats indefinitely                  # IDLE mode now
pressed = False
saberOn = False
timePressed = 0
#play_wav('font', fontNums)

while True:
    red_led.value = True

    timePressed = 0
    while not saberOn:
        switch.update()
        if switch.fell:
            timer = time.monotonic()
            pressed = True
            print('pressed')

        if switch.rose:
            timePressed = time.monotonic() - timer
            pressed = False
            print('rose' + str(timePressed))

        if pressed == False and timePressed > .500 and timePressed < 2.000:
            timePressed = 0
            #next_preset(currPreset)
            print('next preset')
            currPreset += 1
            if currPreset >= totalPresets:
                currPreset = 0
            #settings['currPreset'] = currPreset
            #with open("/sd/test.txt", "w") as f:
            #f.write("Hello world!\r\n")
                #json.dump(settings, f)
            #f = open('/sd/Settings.json', 'w')
            #json.dump(settings, f)
            #f.close
            presetName = Presets['presets'][currPreset]['name']
            COLOR = Presets['presets'][currPreset]['bladeColor']
            humNums  = Presets['presets'][currPreset]['hum']
            fontNums = Presets['presets'][currPreset]['font']
            outNums = Presets['presets'][currPreset]['outSounds']
            inNums = Presets['presets'][currPreset]['inSounds']
            blstNums = Presets['presets'][currPreset]['blstSounds']
            clshNums = Presets['presets'][currPreset]['clshSounds']
            swinghNums = Presets['presets'][currPreset]['swngSounds']
            COLOR_IDLE = COLOR
            COLOR_SWING = COLOR
            print("preset: " + str(currPreset) + Presets['presets'][currPreset]['name'])
        elif pressed == False and timePressed > 2.000:
            timePressed = 0
            #next_preset(currPreset)
            print('prev preset')
            currPreset -= 1
            if currPreset < 0:
                currPreset = totalPresets - 1
            #settings['currPreset'] = currPreset
            #with open("/sd/test.txt", "w") as f:
            #f.write("Hello world!\r\n")
                #json.dump(settings, f)
            #f = open('/sd/Settings.json', 'w')
            #json.dump(settings, f)
            #f.close
            presetName = Presets['presets'][currPreset]['name']
            COLOR = Presets['presets'][currPreset]['bladeColor']
            humNums  = Presets['presets'][currPreset]['hum']
            fontNums = Presets['presets'][currPreset]['font']
            outNums = Presets['presets'][currPreset]['outSounds']
            inNums = Presets['presets'][currPreset]['inSounds']
            blstNums = Presets['presets'][currPreset]['blstSounds']
            clshNums = Presets['presets'][currPreset]['clshSounds']
            swinghNums = Presets['presets'][currPreset]['swngSounds']
            COLOR_IDLE = COLOR
            COLOR_SWING = COLOR
            print("preset: " + str(currPreset) + Presets['presets'][currPreset]['name'])
            play_wav('font', 0, fontNums)
        elif pressed == False and timePressed < .500 and timePressed > 0:
            timePressed = 0
            saberOn = True
            enable.value = True
            powerOn('out', 0, 1.7)         # Power up!
            play_wav('hum', 0, humNums, loop=True)     # Play background hum sound
            print('started hum.wav')      # ON (idle) mode now

 

    i = 0
    boxFilter = [0,0,0]
    pressed = False
    mode = 1
    while saberOn:
        switch.update()
        x, y, z = accel.acceleration # Read accelerometer
        accel_total = math.fabs(x) + math.fabs(y) + math.fabs(z) - 9.81
        if accel_total < HIT_THRESHOLD:
            boxFilter[i] = accel_total
            i += 1
            if (i >= len(boxFilter)):
                i = 0
            accel_total = (boxFilter[0] + boxFilter[1] + boxFilter[2]) / 3
        if switch.fell:
            timer = time.monotonic()
            pressed = True
            print('pressed')
        if switch.rose:
            timePressed = time.monotonic() - timer
            pressed = False
            print('rose' + str(timePressed))
        if pressed == False and timePressed > 1.000:
            timePressed = 0
            saberOn = False
            powerOff('in', 0, 1.15)        # Power down
            enable.value = False
        if accel_total > HIT_THRESHOLD:
            print('clashing')
            TRIGGER_TIME = time.monotonic()
            play_wav('clsh', 0, clshNums)                 # Start playing 'hit' sound
            COLOR_ACTIVE = COLOR_HIT
            mode = 3
        elif mode == 1 and accel_total > SWING_THRESHOLD:
            print('swinging')
            TRIGGER_TIME = time.monotonic()
            play_wav('swng', 0, swngNums)               # Start playing 'swing' sound
            COLOR_ACTIVE = COLOR
            mode = 2
        elif mode > 1:
            if mixer.voice[0].playing:
                strip.fill(COLOR_ACTIVE)
                strip.show()
            elif not mixer.voice[0].playing:
                play_wav('hum',0, humNums, loop=True) # Resume background hum
                print('resume hum')
                strip.fill(COLOR)      # Set to idle color
                strip.show()
                mode = 1
