#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

######################################################### Importieren der Module
import os
import json
import glob
import time
import Adafruit_DHT
import time
import RPi.GPIO as gpio
import rrdtool
import math
import gettext
from sht_sensor import Sht

######################################################### Definieren von Funktionen
#---------------------------------------------------------------------------------- Function goodbye
def goodbye():
    cleanup()
    logstring = _('goodbye') + '!'
    write_verbose(logstring, False, False)

#---------------------------------------------------------------------------------- Function cleanup
def cleanup():
    logstring = _('running cleanup script') + '...'
    write_verbose(logstring, False, False)
    gpio.cleanup() # GPIO zurücksetzen
    logstring = _('cleanup complete') + '.'
    write_verbose(logstring, True, False)

#---------------------------------------------------------------------------------- Function Setup GPIO
def setupGPIO():
    global board_mode
    global gpio_heater
    global gpio_cooling_compressor
    global gpio_circulating_air
    global gpio_humidifier
    global gpio_exhausting_air
    logstring = _('setting up GPIO') + '...'
    write_verbose(logstring, False, False)
    gpio.setwarnings(False)
#---------------------------------------------------------------------------------------------------------------- Board mode wird gesetzt
    gpio.setmode(board_mode)
#---------------------------------------------------------------------------------------------------------------- Einstellen der GPIO PINS
    gpio.setup(gpio_heater, gpio.OUT)
    gpio.setup(gpio_cooling_compressor, gpio.OUT)
    gpio.setup(gpio_circulating_air, gpio.OUT)
    gpio.setup(gpio_humidifier, gpio.OUT)
    gpio.setup(gpio_exhausting_air, gpio.OUT)
    gpio.output(gpio_heater, relay_off)
    gpio.output(gpio_cooling_compressor, relay_off)
    gpio.output(gpio_circulating_air, relay_off)
    gpio.output(gpio_humidifier, relay_off)
    gpio.output(gpio_exhausting_air, relay_off)
    logstring = _('GPIO setup complete') + '.'
    write_verbose(logstring, True, False)
#---------------------------------------------------------------------------------- Function write verbose
def write_verbose(logstring, newLine=False, print_in_logfile=False):
    global verbose
    
    if(verbose):
        print(logstring)
        if(newLine is True):
            print('')
    if (print_in_logfile is True):
        logfile_txt = open(logfile_txt_file, 'a')           # Variable target = logfile.txt öffnen
        logfile_txt.write(logstring)
        logfile_txt.close
#---------------------------------------------------------------------------------- Function Schreiben der current.json
def write_current_json(sensor_temperature, sensor_humidity):
    global current_json_file

    current_data = json.dumps({"sensor_temperature":sensor_temperature, "status_heater":gpio.input(gpio_heater), "status_exhaust_air":gpio.input(gpio_exhausting_air), "status_cooling_compressor":gpio.input(gpio_cooling_compressor), "status_circulating_air":gpio.input(gpio_circulating_air),"sensor_humidity":sensor_humidity, 'last_change':int(time.time())})
    with open(current_json_file, 'w') as currentjsonfile:
        currentjsonfile.write(current_data)
#---------------------------------------------------------------------------------- Function Lesen der settings.json
def read_settings_json():
    global settings_json_file
    settings_data = None
    with open(settings_json_file, 'r') as settingsjsonfile:
        settings_data = settingsjsonfile.read()
    data_settingsjsonfile = json.loads(settings_data)
    return data_settingsjsonfile
#---------------------------------------------------------------------------------- Function Lesen der config.json
def read_config_json():
    global config_json_file
    config_data = None
    with open(config_json_file, 'r') as configjsonfile:
        config_data = configjsonfile.read()
    data_configjsonfile = json.loads(config_data)
    return data_configjsonfile
#---------------------------------------------------------------------------------- Function zum Plotten der Grafiken
def ploting(plotting_value):
#---------------------------------------------------------------------------------------------------------------- Beschriftung für die Grafiken festlegen
    global rrd_dbname
    # print "DEBUG: in plotingfunction"
    if plotting_value == 'sensor_temperature':
        title = _('temperature')
        label = 'in C'
    elif plotting_value == 'sensor_humidity':
        title = _('humidity')
        label = 'in %'
    elif plotting_value == "stat_exhaust_air":
        title = _('exhaust air')
        label = 'ein oder aus'
    elif plotting_value == "stat_circulate_air":
        title = _('circulatioon air')
        label = 'ein oder aus'
    elif plotting_value == "stat_heater":
        title = _('heater')
        label = 'ein oder aus'
    elif plotting_value == "stat_coolcompressor":
        title = _('cooling compressor')
        label = 'ein oder aus'
    elif plotting_value == "status_humidifier":
        title = _('humidifier')
        label = 'ein oder aus'
#---------------------------------------------------------------------------------------------------------------- Aufteilung in drei Plots
    for plot in ['daily' , 'weekly', 'monthly', 'hourly']:
        # print "DEBUG: in for schleife"
        if plot == 'weekly':
            period = 'w'
        elif plot == 'daily':
            period = 'd'
        elif plot == 'monthly':
            period = 'm'
        elif plot == 'hourly':
            period = 'h'
#---------------------------------------------------------------------------------------------------------------- Grafiken erzeugen
        ret = rrdtool.graph("%s%s_%s-%s.png" %(picture_website_path,rrd_dbname,plotting_value,plot),
            "--start",
            "-1%s" % (period),
            "--title=%s (%s)" % (title, plot),
            "--vertical-label=%s" % (label),
            '--watermark=Grillsportverein',
            "-w 400",
            "--alt-autoscale",
            "--slope-mode",
            "DEF:%s=%s:%s:AVERAGE" % (plotting_value, rrd_filename, plotting_value),
            "DEF:%s=%s:sensor_temperature:AVERAGE" % (_('durch'), rrd_filename),
            "DEF:%s=%s:sensor_humidity:AVERAGE" % (_('durchhum'), rrd_filename),
            "GPRINT:%s:AVERAGE:%s\: %%3.2lf C" % (_('durch'), _('Temperatur')),
            "GPRINT:%s:AVERAGE:%s\: %%3.2lf" % (_('durchhum'), _('Luftfeuchtigkeit')), 
            "LINE1:%s#0000FF:%s_%s" % (plotting_value, rrd_dbname, plotting_value))

#---------------------------------------------------------------------------------- Function zum Setzen des Sensors
def set_sensortype():
    global sensor
    global sensorname
    global sensorvalue
    data_configjsonfile = read_config_json()
    sensortype = data_configjsonfile ['sensortype']
    if sensortype == 1: #DHT
        sensor = Adafruit_DHT.DHT11
        sensorname = 'DHT11'
        sensorvalue = 1
    elif sensortype == 2: #SHT
        sensor = Adafruit_DHT.AM2302
        sensorname = 'DHT22'
        sensorvalue = 2
    elif sensortype == 3: #SHT
        sensor = Adafruit_DHT.AM2302
        sensorname = 'SHT'
        sensorvalue = 3
#---------------------------------------------------------------------------------- Function Mainloop
def doMainLoop():
    #global value
    global circulation_air_duration       #  Umluftdauer
    global circulation_air_period         #  Umluftperiode
    global circulation_air_start          #  Unix-Zeitstempel für den Zählstart des Timers Umluft
    global exhaust_air_duration           #  (Abluft-)luftaustauschdauer
    global exhaust_air_period             #  (Abluft-)luftaustauschperiode
    global exhaust_air_start              #  Unix-Zeitstempel für den Zählstart des Timers (Abluft-)Luftaustausch
    global sensor_temperature             #  Gemessene Temperatur am Sensor
    global sensor_humidity                #  Gemessene Feuchtigkeit am Sensor
    global switch_on_cooling_compressor   #  Einschalttemperatur
    global switch_off_cooling_compressor  #  Ausschalttemperatur
    global switch_on_humidifier           #  Einschaltfeuchte
    global switch_off_humidifier          #  Ausschaltfeuchte
    #global temperature
    global settings
    global status_circulating_air         #  Umluft
    global status_exhaust_air             #  (Abluft-)Luftaustausch
    global status_heater                  #  Heizung
    global status_cooling_compressor      #  Kühlung
    global loopcounter                    #  Zählt die Durchläufe des Mainloops
    global status_humidifier              #  Luftbefeuchtung
    global counter_humidify               #  Zähler Verzögerung der Luftbefeuchtung
    global delay_humidify                 #  Luftbefeuchtungsverzögerung
    global status_exhaust_fan             #  Variable für die "Evakuierung" zur Feuchtereduzierung durch (Abluft-)Luftaustausch
#---------------------------------------------------------------------------------------------------------------- Prüfen Sensor, dann Settings einlesen
    while True:
        # print "DEBUG: in While True"
        # print 'DEBUG: ' + str(sensorname)
        if sensorname == 'DHT11': #DHT11
            # print 'DEBUG Sesnorname:' + sensorname
            #sensor_humidity_big, sensor_temperature_big = Adafruit_DHT.read_retry(sensor, gpio_sensor_data)
            sensor_humidity_big = 50
            sensor_temperature_big = 20
            # print "DEBUG: " + str(sensor_temperature_big)
            # print "DEBUG: " + str(sensor_humidity_big)
            atp = 17.271 # ermittelt aus dem Datenblatt DHT11 und DHT22
            btp = 237.7  # ermittelt aus dem Datenblatt DHT11 und DHT22
        elif sensorname == 'DHT22': #DHT22
            # print 'DEBUG Sesnorname:' + sensorname
            sensor_humidity_big, sensor_temperature_big = Adafruit_DHT.read_retry(sensor, gpio_sensor_data)
            atp = 17.271 # ermittelt aus dem Datenblatt DHT11 und DHT22
            btp = 237.7  # ermittelt aus dem Datenblatt DHT11 und DHT22
        elif sensorname == 'SHT': #SHT
            # print 'DEBUG Sesnorname:' + sensorname
            sensor_temperature_big = gpio_sensor_sht.read_t()
            sensor_humidity_big = gpio_sensor_sht.read_rh()
        if sensor_humidity_big is not None and sensor_temperature_big is not None:
            # print "DEBUG: in if"
            sensor_temperature = round (sensor_temperature_big,2)
            sensor_humidity = round (sensor_humidity_big,2)
        else:
            # print "DEBUG: in else"
            logstring = _('Failed to get reading. Try again!')
            write_verbose (logstring, False, False)
        try:
            # print "DEBUG: in try"
            data_settingsjsonfile = read_settings_json()
            data_configjsonfile = read_config_json()
        except:
            logstring = _('unable to read settings file, checking if in the blind.')
            write_verbose(logstring, False, False)
            continue
        modus = data_settingsjsonfile['modus']
        setpoint_temperature = data_settingsjsonfile['setpoint_temperature']
        setpoint_humidity = data_settingsjsonfile['setpoint_humidity']
        circulation_air_period = data_settingsjsonfile['circulation_air_period']
        circulation_air_duration = data_settingsjsonfile['circulation_air_duration']
        exhaust_air_period = data_settingsjsonfile['exhaust_air_period']
        exhaust_air_duration = data_settingsjsonfile['exhaust_air_duration']
        switch_on_cooling_compressor = data_configjsonfile['switch_on_cooling_compressor']
        switch_off_cooling_compressor = data_configjsonfile['switch_off_cooling_compressor']
        switch_on_humidifier = data_configjsonfile['switch_on_humidifier']
        switch_off_humidifier = data_configjsonfile['switch_off_humidifier']
        delay_humidify = data_configjsonfile ['delay_humidify']
        delay_humidify = delay_humidify * 10
        sensortype = data_configjsonfile ['sensortype']
        # An dieser Stelle sind alle settings eingelesen, Ausgabe auf Konsole
        # lastSettingsUpdate = settings['last_change']
        # lastConfigUpdate = config['last_change']
        os.system('clear') # Clears the terminal
        current_time = int(time.time())
        logstring = ' '
        write_verbose(logstring, False, False)
        write_verbose(logspacer, False, False)
        write_verbose(logstring, False, False)
        logstring = _('Main loop/Unix-Timestamp: (') + str(current_time)+ ')'
        write_verbose(logstring, False, False)
        write_verbose(logspacer2, False, False)
        logstring = _('target temperature') + ': ' + str(setpoint_temperature) + '°C'
        write_verbose(logstring, False, False)
        logstring = _('actual temperature') + ': ' + str(sensor_temperature) + '°C'
        write_verbose(logstring, False, False)
        write_verbose(logspacer2, False, False)
        logstring = _('target humidity') + ': ' + str(setpoint_humidity) + '%'
        write_verbose(logstring, False, False)
        logstring = _('actual humidity') + ': ' + str(sensor_humidity) + '%'
        write_verbose(logstring, False, False)
        write_verbose(logspacer2, False, False)
        logstring = _('selected sensor') + ': ' + str(sensorname)
        write_verbose(logstring, False, False)
        logstring = _('value in config.json') + ': ' + str(sensortype)
        write_verbose(logstring, False, False)
        write_verbose(logspacer2, False, False)
        
        write_current_json(sensor_temperature, sensor_humidity)
        # Durch den folgenden Timer läuft der Ventilator in den vorgegebenen Intervallen zusätzlich zur generellen Umluft bei aktivem Heizen, Kühlen oder Befeuchten
#---------------------------------------------------------------------------------------------------------------- Timer für Luftumwälzung-Ventilator
        if circulation_air_period == 0:                          # gleich 0 ist an,  Dauer-Timer
            status_circulation_air = False
        if circulation_air_duration == 0:                        # gleich 0 ist aus, kein Timer
            status_circulation_air = True
        if circulation_air_duration > 0:
            if current_time < circulation_air_start + circulation_air_period:
                status_circulation_air = True                       # Umluft - Ventilator aus
                logstring = _('circulation air timer on (deactive)')
                write_verbose(logstring, False, False)
            if current_time >= circulation_air_start + circulation_air_period:
                status_circulation_air = False                      # Umluft - Ventilator an
                logstring = _('circulation air timer on (active)')
                write_verbose(logstring, False, False)
            if current_time >= circulation_air_start + circulation_air_period + circulation_air_duration:
                circulation_air_start = int(time.time())    # Timer-Timestamp aktualisiert
#---------------------------------------------------------------------------------------------------------------- Timer für (Abluft-)Luftaustausch-Ventilator
        if exhaust_air_period == 0:                      # gleich 0 ist an,  Dauer-Timer
            status_exhaust_air = False
        if exhaust_air_duration == 0:                        # gleich 0 ist aus, kein Timer
            status_exhaust_air = True
        if exhaust_air_duration > 0:                        # gleich 0 ist aus, kein Timer
            if current_time < exhaust_air_start + exhaust_air_period:
                status_exhaust_air = True                      # (Abluft-)Luftaustausch-Ventilator aus
                logstring = _('exhaust air timer on (deactive)')
                write_verbose(logstring, False, False)
            if current_time >= exhaust_air_start + exhaust_air_period:
                status_exhaust_air = False                     # (Abluft-)Luftaustausch-Ventilator an
                logstring = _('exhaust air timer on (active)')
                write_verbose(logstring, False, False)
            if current_time >= exhaust_air_start + exhaust_air_period + exhaust_air_duration:
                exhaust_air_start = int(time.time())   # Timer-Timestamp aktualisiert
#---------------------------------------------------------------------------------------------------------------- Kühlen
        if modus == 0:
            status_exhaust_fan = False                              # Feuchtereduzierung Abluft aus
            gpio.output(gpio_heater, relay_off)                     # Heizung aus
            gpio.output(gpio_humidifier, relay_off)                 # Befeuchtung aus
            if sensor_temperature >= setpoint_temperature + switch_on_cooling_compressor:
                gpio.output(gpio_cooling_compressor, relay_on)      # Kühlung ein
            if sensor_temperature <= setpoint_temperature + switch_off_cooling_compressor :
                gpio.output(gpio_cooling_compressor, relay_off)     # Kühlung aus
#---------------------------------------------------------------------------------------------------------------- Kühlen mit Befeuchtung
        if modus == 1:
            status_exhaust_fan = False                     # Feuchtereduzierung Abluft aus
            gpio.output(gpio_heater, relay_off)      # Heizung aus
            if sensor_temperature >= setpoint_temperature + switch_on_cooling_compressor:
                gpio.output(gpio_cooling_compressor, relay_on)     # Kühlung ein
            if sensor_temperature <= setpoint_temperature + switch_off_cooling_compressor :
                gpio.output(gpio_cooling_compressor, relay_off)    # Kühlung aus
            if sensor_humidity <= setpoint_humidity - switch_on_humidifier:
                gpio.output(gpio_humidifier, relay_on)      # Befeuchtung ein
            if sensor_humidity >= setpoint_humidity - switch_off_humidifier:
                gpio.output(gpio_humidifier, relay_off)     # Befeuchtung aus
#---------------------------------------------------------------------------------------------------------------- Heizen mit Befeuchtung
        if modus == 2:
            status_exhaust_fan = False                     # Feuchtereduzierung Abluft aus
            gpio.output(gpio_cooling_compressor, relay_off)        # Kühlung aus
            if sensor_temperature <= setpoint_temperature - switch_on_cooling_compressor:
                gpio.output(gpio_heater, relay_on)   # Heizung ein
            if sensor_temperature >= setpoint_temperature - switch_off_cooling_compressor:
                gpio.output(gpio_heater, relay_off)  # Heizung aus
            if sensor_humidity <= setpoint_humidity - switch_on_humidifier:
                gpio.output(gpio_humidifier, relay_on)      # Befeuchtung ein
            if sensor_humidity >= setpoint_humidity - switch_off_humidifier:
                gpio.output(gpio_humidifier, relay_off)     # Befeuchtung aus
#---------------------------------------------------------------------------------------------------------------- Automatiktemperatur mit Befeuchtung
        if modus == 3:
            status_exhaust_fan = False                     # Feuchtereduzierung Abluft aus
            if sensor_temperature >= setpoint_temperature + switch_on_cooling_compressor:
                gpio.output(gpio_cooling_compressor, relay_on)     # Kühlung ein
            if sensor_temperature <= setpoint_temperature + switch_off_cooling_compressor:
                gpio.output(gpio_cooling_compressor, relay_off)    # Kühlung aus
            if sensor_temperature <= setpoint_temperature - switch_on_cooling_compressor:
                gpio.output(gpio_heater, relay_on)   # Heizung ein
            if sensor_temperature >= setpoint_temperature - switch_off_cooling_compressor:
                gpio.output(gpio_heater, relay_off)  # Heizung aus
            if sensor_humidity <= setpoint_humidity - switch_on_humidifier:
                gpio.output(gpio_humidifier, relay_on)      # Befeuchtung ein
            if sensor_humidity >= setpoint_humidity - switch_off_humidifier:
                gpio.output(gpio_humidifier, relay_off)     # Befeuchtung aus
#---------------------------------------------------------------------------------------------------------------- Automatik mit Befeuchtung und Entfeuchtung durch (Abluft-)Luftaustausch
        if modus == 4:
            if sensor_temperature >= setpoint_temperature + switch_on_cooling_compressor:
                gpio.output(gpio_cooling_compressor, relay_on)     # Kühlung ein
            if sensor_temperature <= setpoint_temperature + switch_off_cooling_compressor:
                gpio.output(gpio_cooling_compressor, relay_off)    # Kühlung aus
            if sensor_temperature <= setpoint_temperature - switch_on_cooling_compressor:
                gpio.output(gpio_heater, relay_on)   # Heizung ein
            if sensor_temperature >= setpoint_temperature - switch_off_cooling_compressor:
                gpio.output(gpio_heater, relay_off)  # Heizung aus
            if sensor_humidity <= setpoint_humidity - switch_on_humidifier:
                counter_humidify = counter_humidify + 1
                if counter_humidify >= delay_humidify:               # Verzögerung der Luftbefeuchtung
                    gpio.output(gpio_humidifier, relay_on)  # Luftbefeuchter ein
            if sensor_humidity >= setpoint_humidity - switch_off_humidifier:
                gpio.output(gpio_humidifier, relay_off)     # Luftbefeuchter aus
                counter_humidify = 0
            if sensor_humidity >= setpoint_humidity + switch_on_humidifier:
                status_exhaust_fan = True                        # Feuchtereduzierung Abluft-Ventilator ein
            if sensor_humidity <= setpoint_humidity + switch_off_humidifier:
                status_exhaust_fan = False                         # Feuchtereduzierung Abluft-Ventilator aus
#---------------------------------------------------------------------------------------------------------------- Schalten des Umluft - Ventilators
        if gpio.input(gpio_heater) or gpio.input(gpio_cooling_compressor) or gpio.input(gpio_humidifier) or status_circulation_air == False:
            gpio.output(gpio_circulating_air, relay_on)               # Umluft - Ventilator an
        if gpio.input(gpio_heater) and gpio.input(gpio_cooling_compressor) and gpio.input(gpio_humidifier) and status_circulation_air == True:
            gpio.output(gpio_circulating_air, relay_off)             # Umluft - Ventilator aus
#---------------------------------------------------------------------------------------------------------------- Schalten des (Abluft-)Luftaustausch-Ventilator
        if status_exhaust_air == False or status_exhaust_fan == True:
            gpio.output(gpio_exhausting_air, relay_on)
        if status_exhaust_fan == False and status_exhaust_air == True:
            gpio.output(gpio_exhausting_air, relay_off)
#---------------------------------------------------------------------------------------------------------------- Ausgabe der Werte auf der Konsole
        write_verbose(logspacer2, False, False)
        if gpio.input(gpio_heater) == False:
            logstring = _('heater on')
            write_verbose(logstring, False, False)
            status_heater = 10
        else:
            logstring = _('heater off')
            write_verbose(logstring, False, False)
            status_heater = 0
        if gpio.input(gpio_cooling_compressor) == False:
            logstring = _('cooling compressor on')
            write_verbose(logstring, False, False)
            status_cooling_compressor = 10
        else:
            logstring = _('cooling compressor off')
            write_verbose(logstring, False, False)
            status_cooling_compressor = 0
        if gpio.input(gpio_humidifier) == False:
            logstring = _('humidifier on')
            write_verbose(logstring, False, False)
            status_humidifier = 10
        else:
            logstring = _('humidifier off')
            write_verbose(logstring, False, False)
            status_humidifier = 0
        if gpio.input(gpio_circulating_air) == False:
            logstring = _('circulation air on')
            write_verbose(logstring, False, False)
            status_circulating_air = 10
        else:
            logstring = _('circulation air off')
            write_verbose(logstring, False, False)
            status_circulating_air = 0
        if gpio.input(gpio_exhausting_air) == False:
            logstring = _('exhaust air on')
            write_verbose(logstring, False, False)
            status_exhaust_air = 10
        else:
            logstring = _('exhaust air off')
            write_verbose(logstring, False, False)
            status_exhaust_air = 0
        write_verbose(logspacer2, False, False)
#---------------------------------------------------------------------------------------------------------------- Messwerte in die RRD-Datei schreiben
        from rrdtool import update as rrd_update
        ret = rrd_update('%s' %(rrd_filename), 'N:%s:%s:%s:%s:%s:%s:%s' %(sensor_temperature, sensor_humidity, status_exhaust_air, status_circulating_air, status_heater, status_cooling_compressor, status_humidifier))
        #array für graph     
        # Grafiken erzeugen
        if loopcounter % 3 == 0:
            logstring = _("creating graphs")
            write_verbose(logstring, False, False)
            # print "DEBUG: ploting sensor_temperature"
            ploting('sensor_temperature')#', 'status_heater', 'status_cooling_compressor', 'status_circulating_air')
            # print "DEBUG: ploting sensor_humidity"
            ploting('sensor_humidity')#, 'status_humidifier', 'status_circulating_air', 'status_exhaust_air')
            # print "DEBUG: ploting status_circulating_air"
            ploting('stat_circulate_air')#, 'status_exhaust_air')
            # print "DEBUG: ploting status_exhaust_air"
            ploting('stat_exhaust_air')
            # print "DEBUG: ploting status_heater"
            ploting('stat_heater')
            # print "DEBUG: ploting status_cooling_compressor"
            ploting('stat_coolcompressor')
            # print "DEBUG: ploting status_humidifier"
            ploting('status_humidifier')
            # print 'DEBUG Loopnumber: ' + loopcounter

        time.sleep(1)  
        # Mainloop fertig
        logstring = _('loop complete.')
        write_verbose(logstring, False, False)
        time.sleep(3)
        loopcounter += 1
    
######################################################### Definition von Variablen
#---------------------------------------------------------------------------------- Pfade zu den Dateien
website_path = '/var/www/'
settings_json_file = website_path + 'settings.json'
current_json_file = website_path + 'current.json'
picture_website_path = website_path + 'pic/'
config_json_file = website_path + '/config.json'
logfile_txt_file = website_path + '/logfile.txt'
#---------------------------------------------------------------------------------- allgemeine Variablen
# sensor = Adafruit_DHT.AM2302
logspacer = "\n" + "***********************************************"
logspacer2 = "\n" + '-------------------------------------------------------'
delay = 4                      # Wartezeit in der Schleife
counter_humidify = 0           # Zähler für die Verzögerung der Befeuchtung
status_exhaust_fan = False     # Variable für die "Evakuierung" zur Feuchtereduzierung durch (Abluft-)Luftaustausch
verbose = True                # Dokumentiert interne Vorgänge wortreich
#---------------------------------------------------------------------------------- Allgemeingültige Werte aus config.json
data_configjsonfile = read_config_json()
sensortype = data_configjsonfile ['sensortype']                                        # Sensortyp
language = data_configjsonfile ['language']                                            # Sprache der Textausgabe
switch_on_cooling_compressor = data_configjsonfile ['switch_on_cooling_compressor']    # Einschalttemperatur
switch_off_cooling_compressor = data_configjsonfile ['switch_off_cooling_compressor']  # Ausschalttemperatur
switch_on_humidifier = data_configjsonfile ['switch_on_humidifier']                    # Einschaltfeuchte
switch_off_humidifier = data_configjsonfile ['switch_off_humidifier']                  # Ausschaltfeuchte
delay_humidify = data_configjsonfile ['delay_humidify']                                # Luftbefeuchtungsverzögerung
#---------------------------------------------------------------------------------- Sainsmart Relais Vereinfachung 0 aktiv
relay_on = False               # negative Logik!!! des Relay's, Schaltet bei 0 | GPIO.LOW  | False  ein
relay_off = (not relay_on)     # negative Logik!!! des Relay's, Schaltet bei 1 | GPIO.High | True aus
#---------------------------------------------------------------------------------- RRD-Tool
rrd_dbname = 'pi-ager'                   # Name fuer Grafiken etc
rrd_filename = rrd_dbname + '.rrd'   # Dateinamen mit Endung
measurement_time_interval = 10       # Zeitintervall fuer die Messung in Sekunden
# i = 0
loopcounter = 0                      #  Zählt die Durchläufe des Mainloops
#-----------------------------------------------------------------------------------------Pinbelegung
board_mode = gpio.BCM         # GPIO board mode (BCM = Broadcom SOC channel number - numbers after GPIO [GPIO.BOARD = Pin by number])
data_configjsonfile = read_config_json()
gpio_cooling_compressor = data_configjsonfile ['gpio_cooling_compressor']    # GPIO für Kühlschrankkompressor
gpio_heater = data_configjsonfile ['gpio_heater']                            # GPIO für Heizkabel
gpio_humidifier = data_configjsonfile ['gpio_humidifier']                    # GPIO für Luftbefeuchter
gpio_circulating_air = data_configjsonfile ['gpio_circulating_air']          # GPIO für Umluftventilator
gpio_exhausting_air = data_configjsonfile ['gpio_exhausting_air']            # GPIO für Austauschlüfter
gpio_uv_light = data_configjsonfile ['gpio_uv_light']                        # GPIO für UV Licht
gpio_light = data_configjsonfile ['gpio_light']                              # GPIO für Licht
gpio_reserved1 = data_configjsonfile ['gpio_reserved1']                      # 
gpio_sensor_data = data_configjsonfile ['gpio_sensor_data']                  # GPIO für Data Temperatur/Humidity Sensor
gpio_sensor_sync = data_configjsonfile ['gpio_sensor_sync']                  # GPIO für Sync Temperatur/Humidity Sensor
gpio_sensor_sht = Sht(gpio_sensor_sync, gpio_sensor_data)       # GPIO's für Temperatur/Humidity Sensor SHT Sht(Synchronisierung, DATA)
gpio_scale1_wire1 = data_configjsonfile ['gpio_scale1_wire1']                # GPIO für Waage1 Ader 1
gpio_scale1_wire2 = data_configjsonfile ['gpio_scale1_wire2']                # GPIO für Waage1 Ader 2
gpio_scale2_wire1 = data_configjsonfile ['gpio_scale2_wire1']                # GPIO für Waage2 Ader 1
gpio_scale2_wire2 = data_configjsonfile ['gpio_scale2_wire2']                # GPIO für Waage2 Ader 2

#---------------------------------------------------------------------------------------------------------------- Sprache
####   Set up message catalog access
# translation = gettext.translation('pi_ager', '/var/www/locale', fallback=True)
# _ = translation.ugettext
if language == 'de':
    translation = gettext.translation('pi_ager', '/var/www/locale', languages=['en'], fallback=True)
elif language == 'en':
    translation = gettext.translation('pi_ager', '/var/www/locale', languages=['de'], fallback=True)
# else:
    
translation.install()

######################################################### Hauptprogramm
########################################################################################################################

os.system('clear') # Bildschirm löschen
write_verbose(logspacer, False, False)
setupGPIO() # GPIO initialisieren

#---------------------------------------------------------------------------------- RRD-Datenbank anlegen, wenn nicht vorhanden
try:
    with open(rrd_filename): pass
    logstring = _("database file found") + ": " + rrd_filename
    write_verbose(logstring, False, False)
#    i = 1
except IOError:
    logstring = _("creating a new database") + ": " + rrd_filename
    write_verbose(logstring, False, False)
    ret = rrdtool.create("%s" %(rrd_filename),
        "--step","%s" %(measurement_time_interval),
        "--start",'0',
        "DS:sensor_temperature:GAUGE:2000:U:U",
        "DS:sensor_humidity:GAUGE:2000:U:U",
        "DS:stat_exhaust_air:GAUGE:2000:U:U",
        "DS:stat_circulate_air:GAUGE:2000:U:U",
        "DS:stat_heater:GAUGE:2000:U:U",
        "DS:stat_coolcompressor:GAUGE:2000:U:U",
        "DS:status_humidifier:GAUGE:2000:U:U",
        "RRA:AVERAGE:0.5:1:2160",
        "RRA:AVERAGE:0.5:5:2016",
        "RRA:AVERAGE:0.5:15:2880",
        "RRA:AVERAGE:0.5:60:8760",)

#    i = 1
write_verbose(logspacer, False, False)
settings = read_settings_json()
config = read_config_json()
set_sensortype()
circulation_air_start = int(time.time())
exhaust_air_start = circulation_air_start
try:
    doMainLoop()
except KeyboardInterrupt:
    pass

except Exception, e:
    logstring = _('exception occurred') + '!!!'
    write_verbose(logstring, True, False)
    write_verbose(str(e), True, False)
    pass

goodbye()