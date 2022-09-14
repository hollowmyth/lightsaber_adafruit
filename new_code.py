"""LASER SWORD (pew pew) example for Adafruit Hallowing & NeoPixel strip"""
# pylint: disable=bare-except

import time
import math
import gc
from digitalio import DigitalInOut, Direction, Pull
import digitalio
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
import json
import random


# CUSTOMIZE YOUR COLOR HERE:
# (red, green, blue) -- each 0 (off) to 255 (brightest)
# COLOR = (100, 0, 255)  # purple
# COLOR = (0, 100, 255) #cyan
# COLOR = (255, 0, 0) #red
# COLOR = (205, 205, 205) #white
#COLOR = (60, 240, 0) #green
COLOR = (0, 0, 230) #blue

# CUSTOMIZE SENSITIVITY HERE: smaller numbers = more sensitive to motion
HIT_THRESHOLD = 30 # 250
SWING_THRESHOLD = 3

NUM_PIXELS = 132
# NUM_PIXELS = 85
NEOPIXEL_PIN = board.D5
POWER_PIN = board.D10
SWITCH_PIN = board.D9

enable = DigitalInOut(POWER_PIN)
enable.direction = Direction.OUTPUT
enable.value =False

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.D4)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")
#with open("/sd/test.txt", "w") as f:
#    f.write("Hello world!\r\n")
#with open("/sd/test.txt", "r") as f:
#    print("Read line from file:")
#
#    print(f.readline())

red_led = DigitalInOut(board.D11)
red_led.direction = Direction.OUTPUT
green_led = DigitalInOut(board.D12)
green_led.direction = Direction.OUTPUT
blue_led = DigitalInOut(board.D13)
blue_led.direction = Direction.OUTPUT

audio = audioio.AudioOut(board.A0)     # Speaker
mixer = audiomixer.Mixer(voice_count=3, sample_rate=22050, channel_count=1,bits_per_sample=16, samples_signed=True)
audio.play(mixer)
mode = 0                               # Initial mode = OFF

strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False)
strip.fill(0)                          # NeoPixels off ASAP on startup
strip.show()

pin = DigitalInOut(SWITCH_PIN)
pin.direction = Direction.INPUT
pin.pull = Pull.UP
switch = Debouncer(pin)

time.sleep(0.1)

# Set up accelerometer on I2C bus, 4G range:
i2c = busio.I2C(board.SCL, board.SDA)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c)
accel.range = adafruit_lis3dh.RANGE_4_G

# "Idle" color is 1/4 brightness, "swinging" color is full brightness...
COLOR_IDLE = (int(COLOR[0] / 1), int(COLOR[1] / 1), int(COLOR[2] / 1))
COLOR_SWING = COLOR
COLOR_HIT = (255, 255, 255)  # "hit" color is white

S = open('/sd/Settings.json')
settings = json.load(S)
currPreset = settings['currPreset']
#currVolume = settings.currVolume
#Volume = settings.Volume[c]
customBladeColor = settings['customBladeColor']
S.close

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
swinghNums = Presets['presets'][currPreset]['swinghSounds']



def next_preset():
    currPreset += 1
    if currPreset > totalPresets - 1:
        currPreset = 0
    settings['currPreset'] = currPreset
    f = open('/sd/Settings.json')
    json.dump(settings, f)
    f.close
    update_preset()

def prev_preset():
    currPreset -= 1
    if currPreset < 0:
        currPreset = totalPresets - 1
    settings['currPreset'] = currPreset
    f = open('/sd/Settings.json')
    json.dump(settings, f)
    f.close
    update_preset()


def update_preset():
    presetName = Presets['presets'][currPreset]['name']
    COLOR = Presets['presets'][currPreset]['bladeColor']
    humNums  = Presets['presets'][currPreset]['hum']
    fontNums = Presets['presets'][currPreset]['font']
    outNums = Presets['presets'][currPreset]['outSounds']
    inNums = Presets['presets'][currPreset]['inSounds']
    blstNums = Presets['presets'][currPreset]['blstSounds']
    clshNums = Presets['presets'][currPreset]['clshSounds']
    swinghNums = Presets['presets'][currPreset]['swinghSounds']


def choose_random(num):
    random_num = random.randint(1,num)
    if random_num < 10:
        random_num = ("0" + str(random_num))
    random_num = str(random_num)
    return(random_num)


def build_name(name, soundNums):
    fileName = name + '/' + name + str(choose_random(soundNums)) + '.wav'
    return(fileName)


def play_wav(name, channel, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    @param name: partial file name str, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    @param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    print("playing", name)
    mixer.voice[0].stop()
    try:
        built_name = build_name(name, num)
        wave_file = open('/sd/' + presetName+'/' + built_name, 'rb')
        wave = audiocore.WaveFile(wave_file)
        #audio.play(mixer)
        mixer.voice[0].level = .4
        mixer.voice[0].play(wave,loop=loop)
        #audio.play(wave, loop=loop)
    except:
        return

def power_on(duration):
    """
    Animate NeoPixels with accompanying sound effect for power on / off.
    @param sound:    sound name (similar format to play_wav() above)
    @param duration: estimated duration of sound, in seconds (>0.0)
    @param reverse:  if True, do power-off effect (reverses animation)
    """
    prev = 0
    gc.collect()                   # Tidy up RAM now so animation's smoother
    start_time = time.monotonic()  # Save audio start time
    #if sound == "off" or sound == "on":
    #   play_wav(sound)
    #else:
    #wave_file = open('/sd/' + '/' + sound + '.wav', 'rb')
        #wave_file = open('/sd/Cal_Kestis_Pro/' + sound + '.wav', 'rb')
    #wave = audiocore.WaveFile(wave_file)
    #audio.play(wave, loop=False)
    outName = build_name("out", outNums)
    humName = build_name("hum", humNums)
    play_wav(outName, 1)
    play_wav(humName, 0, loop=True)
    
    print('powering up')
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
    print('power up finished')
    while mixer.voice[1].playing:                         # Wait until audio done
        pass
    swinghName = build_name("swingh", swinghNums)
    play_wav(swinghName, 1, loop=True)
    mixer.voice[1].level = 0

def power_off(duration):
    prev = NUM_PIXELS
    gc.collect()                   # Tidy up RAM now so animation's smoother
    start_time = time.monotonic()  # Save audio start time
    inName = build_name("in", inNums)
    play_wav(inName, 1)

    while True:
        elapsed = time.monotonic() - start_time  # Time spent playing sound
        if elapsed > duration:                   # Past sound duration?
            break                                # Stop animating
        fraction = elapsed / duration           # Animation time, 0.0 to 1.0
        fraction = 1.0 - fraction
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
    while mixer.voice[1].playing:                         # Wait until audio done
        pass
    print('stopping all voices.')
    mixer.voice[0].stop()
    mixer.voice[1].stop()
    mixer.voice[2].stop()

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

# Main program loop, repeats indefinitely
'''
while True:

    red_led.value = True

    if not switch.value:                    # button pressed?
        if mode == 0:                       # If currently off...
            enable.value = True
            #power('on', 1.7, False)         # Power up!
            power('maul_out01_B', 1.7, False)
            #power('cal_out01_B', 1.7, False)
            play_wav('idle', loop=True)     # Play background hum sound
            #idle_file = open('/sd/Darth_Maul/maul_hum01_A.wav', 'rb')
            #wave2 = audiocore.WaveFile(idle_file)
            #audio.play(wave2, loop=True)
            mode = 1                        # ON (idle) mode now
        else:                               # else is currently on...
            #power('off', 1.15, True)        # Power down
            power('maul_in01_B', 1.15, True)
            #power('cal_in01_B', 1.15, True)
            mode = 0                        # OFF mode now
            enable.value = False
        while not switch.value:             # Wait for button release
            time.sleep(0.2)                 # to avoid repeated triggering

    elif mode >= 1:                         # If not OFF mode...
        x, y, z = accel.acceleration # Read accelerometer
        accel_total = x * x + z * z
        # (Y axis isn't needed for this, assuming Hallowing is mounted
        # sideways to stick.  Also, square root isn't needed, since we're
        # just comparing thresholds...use squared values instead, save math.)
        if accel_total > HIT_THRESHOLD:   # Large acceleration = HIT
            TRIGGER_TIME = time.monotonic() # Save initial time of hit
            play_wav('hit')                 # Start playing 'hit' sound
            COLOR_ACTIVE = COLOR_HIT        # Set color to fade from
            mode = 3                        # HIT mode
        elif mode == 1 and accel_total > SWING_THRESHOLD: # Mild = SWING
            TRIGGER_TIME = time.monotonic() # Save initial time of swing
            play_wav('swing')               # Start playing 'swing' sound
            COLOR_ACTIVE = COLOR_SWING      # Set color to fade from
            mode = 2                        # SWING mode
        elif mode > 1:                      # If in SWING or HIT mode...
            if audio.playing:               # And sound currently playing...
                blend = time.monotonic() - TRIGGER_TIME # Time since triggered
                if mode == 2:               # If SWING,
                    blend = abs(0.5 - blend) * 2.0 # ramp up, down
                strip.fill(mix(COLOR_ACTIVE, COLOR_IDLE, blend))
                strip.show()
            else:                           # No sound now, but still MODE > 1
                play_wav('idle', loop=True) # Resume background hum
                strip.fill(COLOR_IDLE)      # Set to idle color
                strip.show()
                mode = 1                    # IDLE mode now


# psuedo code to real code
'''
pressed = False
saberOn = False
timePressed = 0
while True:


    while not saberOn:
        red_led.value = True
        switch.update()
        if switch.fell:
            timer = time.monotonic()
            pressed = True
            print('pressed')
        if switch.rose:
            timePressed = time.monotonic() - timer
            pressed = False
            print('rose' + str(timePressed))
        if pressed == False and timePressed > 500 and timePressed < 2000:
            timePressed = 0
            next_preset()
            fontName = build_name("font", fontNums)
            play_wav(fontName, 0)
        elif pressed == False and timePressed > 2000:
            timePressed = 0
            prev_preset()
            fontName = build_name("font", fontNums)
            play_wav(fontName, 0)
        elif pressed == False and timePressed < 500 and timePressed > 0:
            timePressed = 0
            saberOn = True
            power_on(1.7)
    i = 0
    boxFilter = [0, 0, 0]

    while saberOn:
        red_led.value = True
        switch.update()
        if switch.fell:
            timer = time.monotonic()
            pressed = True
            print('pressed')
        if switch.rose:
            timePressed = time.monotonic() - timer
            pressed = False
            print('rose' + str(timePressed))
        if pressed == False and timePressed > 1000:
            timePressed = 0
            saberOn = False
            power_off(1.15)
        elif pressed == False and timePressed < 1000:
            # Blaster sounds
            # Blaster effect on blade
            a = 1

        x, y, z = accel.acceleration # Read accelerometer
        accel_total = math.fabs(x) + math.fabs(y) + math.fabs(z) - 9.81
        boxFilter[i] = accel_total
        i += 1
        if (i >= len(boxFilter)):
            i = 0
        accel_total = (boxFilter[0] + boxFilter[1] + boxFilter[2]) / 3
        if accel_total > (HIT_THRESHOLD - SWING_THRESHOLD):
            print('Hit')
        #    play_wav('hit')
        #    COLOR_ACTIVE = COLOR_HIT
        if accel_total > HIT_THRESHOLD:
            accel_total = HIT_THRESHOLD
        elif accel_total < SWING_THRESHOLD:
            accel_total = 0
        volLevel = accel_total / HIT_THRESHOLD
        #print(volLevel)
        mixer.voice[1].level = volLevel