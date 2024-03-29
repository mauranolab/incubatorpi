#!/usr/bin/python3

import RPi.GPIO as IO
import time
import smtplib
from datetime import datetime
import signal
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
import configparser
import socket


###Utility functions
#Lookup table for the pin number used by incubators numbered 1 through 4
incubatorToPinMapping = {1: 12, 2: 11, 3: 10, 4: 8}

#Takes an incubator and returns the status code
def getIncubatorStatus(i):
    if i not in incubatorToPinMapping:
        raise ValueError("Invalid incubator number " + str(i))
    
    if not incubatorsactive[i-1]: #convert from 1 to 0 index
        #Suppresses alarm state
        return 2
    else:
    #IO.input(pin) measures current status of the pin
    #in this case, it returns either 0 or 1
        return IO.input(incubatorToPinMapping[i])


#Sets a given LED (color) to state (0/1)
def set_led_state(color,state):
    IO.setmode(IO.BOARD)
    IO.setup(40,IO.OUT)
    IO.setup(38,IO.OUT)
    if color == 'green':
        pin = 38
    elif color == 'red':
        pin = 40
    IO.output(pin,state)


#https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


#Will pass on any exceptions for send failure
def send_email(user, recipient, subject, body):
    global smtpserver
    
    FROM = user
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body
    
    # Prepare actual message
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
#    print(message)
#    print("trying to send email")
    server = smtplib.SMTP(smtpserver)
    #server.ehlo()
    server.sendmail(FROM, TO, message)
    server.quit()
#    print('successfully sent the mail')
    
    #Add in a delay to act as crude rate limiting
    time.sleep(20)


#%% in message will be replaced by incubator number
def broadcast_message(logger, to_emails, alarmname, incubatornames, status, incubatornum, message):
    global startupdate
    global senderemail
    
    if incubatornum is not None and incubatornames is not None:
        message = message.replace('%%', str(incubatornum) + ' (' + incubatornames[incubatornum-1] + ')')
    body = alarmname + ' - ' + message + '\n\n'
    if incubatornames is not None and status is not None:
        body += 'Current status: \n'
        for i in range(len(status)):
            body += incubatornames[i] + ': ' + ['ALARM', 'OK', 'UNMONITORED'][status[i]] + "\n"
        body += '\n'
    body += 'Hostname: ' + socket.gethostname() + ' (' + get_ip() + ')' + '\n'
    body += 'Current time: ' + str(datetime.now()) + '\n'
    runtime = datetime.now() - startupdate
    body += 'Running since: ' + str(startupdate) + ' (%d days, %d hours and %d minutes)\n' % (runtime.days, runtime.seconds/3600, (runtime.seconds/60)-60*int(runtime.seconds/3600))
    
    logger(message)
    
    keeptrying = True
    while keeptrying:
        try:
            #TODO Wrong severity level
            logger("Sending email to " + ",".join(to_emails))
            send_email(senderemail, to_emails, alarmname + ' - ' + message, body)
            keeptrying = False
        except Exception:
            msg = "Failed to send email to " + ",".join(to_emails)
            logger(msg)
            #tried logger.exception(msg) but get "AttributeError: 'function' object has no attribute 'exception'"
            if len(to_emails) > 1:
                #Try again out of paranoia after blindly truncating the first recipient from to_emails; send_email doesn't seem to check for a valid address beyond a@b.com, but just in case...
                body = "WARNING: failed to include " + to_emails[-1] + "as recipient; removed and tried again"
                to_emails = to_emails[:-1]
                #Give it some time in case there is a network issue
                time.sleep(30)
            else:
                #Nothing left to try
                keeptrying = False


###Main code begins here
###Initialize parameters not in the config file
basedir='/home/pi/Alarm/' #So we can find config file and log dirs
senderemail='VALIDEMAIL@nyulangone.org'
smtpserver="smtp.nyumc.org"
repeatinterval=30 #Frequency of reminder emails of ongoing alarm conditions (approximately in minutes)

#Initialize default values in case we have an error parsing config file later on
alarmname = 'Unknown'
to_emails = ['maurano@nyu.edu']
incubatornames = ['Incubator 1', 'Incubator 2', 'Incubator 3', 'Incubator 4']
incubatorsactive = [True, True, True, True]

###Initialize global variables
startupdate = datetime.now()
weeklytest = False #Whether we are in the weekly heartbeat announcement
alarm = False #Whether we are in an alarm state
curAlarmRepeat = 0 #The number of main loop iterations since we last sent a reminder of an ongoing alarm condition
status = [1, 1, 1, 1] # State vector of the incubators this cycle; initialize to all clear
priorstatus = status # State vector of the incubators last cycle

###Configure logging
logger = logging.getLogger("IncubatorAlarmLog")
logger.setLevel(logging.DEBUG)

handler1 = TimedRotatingFileHandler(basedir + 'Log/incubatoralarm.log', when="D", interval=30, backupCount=1000)
handler1.setLevel(logging.INFO)
logger.addHandler(handler1)

handler2 = logging.StreamHandler()
logger.addHandler(handler2)

#alarmname will be updated after reading config file
handler1.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s ' + alarmname + ' %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
handler2.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s ' + alarmname + ' %(message)s', datefmt='%Y-%m-%d %H:%M:%s'))

logger.info("Beginning startup")

#Set up handler to log a shutdown notice
def sigterm_handler(_signo, _stack_frame):
    #logger is a global variable
    logger.critical("Alarm monitor shutting down!")
    # Raises SystemExit(0):
    sys.exit(0)

signal.signal(signal.SIGTERM, sigterm_handler)


###initialize configuration
logger.info("Reading configuration from alarm_config.ini")
#alarm_config.ini must be present in same directory:
#[DEFAULT]
#alarmname=MyAlarmName
#emails=test@nyu.edu,test2@nyu.edu
#incubatornames=Incubator 1,Incubator 2,Incubator 3,Incubator 4
#incubatorsactive=1,1,1,1

####Now that we have the configuration loaded add the logfile handler
try:
    config = configparser.ConfigParser()
    config.read(basedir + 'alarm_config.ini')
    
    alarmname = config.get('DEFAULT', 'alarmname')
    #First update logging formatters to include alarmname pulled from config file
    handler1.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s ' + alarmname + ' %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    handler2.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s ' + alarmname + ' %(message)s', datefmt='%Y-%m-%d %H:%M:%s'))
    
    to_emails = config.get('DEFAULT', 'emails').split(',')
    incubatornames = config.get('DEFAULT', 'incubatornames').split(',')
    incubatorsactive = [ int(i)==1 for i in config.get('DEFAULT', 'incubatorsactive').split(',') ] #Parse and convert to logical
    logger.info("alarmname=" + alarmname)
    logger.info("to_emails=" + ",".join(to_emails))
    logger.info("incubatornames=" + ",".join(incubatornames))
    logger.info("incubatorsactive=" + str(incubatorsactive))
except Exception:
    msg = "Failed to read configuration, using hardcoded defaults"
    logger.exception(msg)
    #NB email may fail if run by cron since network may not be fully up yet, so give it a bit of time
    time.sleep(60)
    broadcast_message(logger.critical, to_emails, alarmname, None, None, None, msg)


###Setting up input pins to detect incubator alarm.
IO.setmode(IO.BOARD)
#DOWN = low voltage, Incubator Alarm Contacts 2-com, 3-N.O.
IO.setup(incubatorToPinMapping[1], IO.IN, pull_up_down=IO.PUD_DOWN)
IO.setup(incubatorToPinMapping[2], IO.IN, pull_up_down=IO.PUD_DOWN)
IO.setup(incubatorToPinMapping[3], IO.IN, pull_up_down=IO.PUD_DOWN)
IO.setup(incubatorToPinMapping[4], IO.IN, pull_up_down=IO.PUD_DOWN)


#NB network may not be fully up yet, so give it a bit of time
time.sleep(60)
logger.info('Connected to network as ' + socket.gethostname() + ' (' + get_ip() + ')')

logger.critical('Finished startup')


###Main loop
while True:
    try:
        #Print out status vector every cycle
        logger.debug("Incubator status: " + str(status))
        
        ###Check current status
        #In the all good state, status = [1, 1, 1, 1]
        priorstatus = status
        status = [ getIncubatorStatus(curIncubatorIndex) for curIncubatorIndex in range(1, 4+1) ]
        
        #Unmonitored incubators are guaranteed to return 2 by getIncubatorStatus(), so we don't need to handle them explicitly below
        if 0 not in status:
            #All clear
            indicator = 'green'
            if alarm == True:
                #We have just gone from 1+ incubator being in alarm state to all clear
                broadcast_message(logger.critical, to_emails, alarmname, incubatornames, status, None, 'All incubators have recovered')
                alarm = False #updating previous alarm state to clear
                curAlarmRepeat = 0
        else:
            logger.debug("Incubator status: " + str(status))
            
            #1+ incubator is in alarm state
            #Both red and green LEDs will be off while we evaluate
            curAlarmRepeat += 1
            for curIncubatorIndex in range(len(status)):
                curIncubatorNum = curIncubatorIndex+1
                if status[curIncubatorIndex] != priorstatus[curIncubatorIndex]:
                    if status[curIncubatorIndex] == 0: # This incubator just failed
                        logger.warning('Potential alarm detected in incubator ' + str(curIncubatorNum))
                        
                        time.sleep(15)
                        status[curIncubatorIndex] = getIncubatorStatus(curIncubatorNum)
                        logger.debug("Incubator status after check: " + str(status))
                        
                        #it seems the state goes to 2 for a brief period (not sure if it's time or read cycles) after a test unplugging the cable
                        if status[curIncubatorIndex] == 1:
                            #This alarm went away after a short wait, suggesting it was just a transient. Log the event but clear the alarm state.
                            logger.warning('Transient alarm detected in incubator ' + str(curIncubatorNum) + '; alarm signal no longer present.')
                        else:
                            #Still going, raise the alarm
                            broadcast_message(logger.critical, to_emails, alarmname, incubatornames, status, curIncubatorNum, 'New alarm detected in incubator #%%')
                            indicator = 'red'
                            alarm = True #Only set the alarm state once we are sure at least one incubator has a clear alarm
                    elif status[curIncubatorIndex] == 1: # This incubator just recovered (another incubator must still be failed)
                        broadcast_message(logger.critical, to_emails, alarmname, incubatornames, status, curIncubatorNum, 'Incubator #%% has recovered')
                else:
                    #Nothing has changed, we are still in an alarm state
                    if curAlarmRepeat >= repeatinterval:
                        broadcast_message(logger.critical, to_emails, alarmname, incubatornames, status, None, 'Ongoing alarm condition')
                        curAlarmRepeat = 0
        
        
        ###Check whether we should send a heartbeat message
        my_dt_ob = datetime.now()
        
        #Send the heartbeat message on Fridays at 10:00am
        if my_dt_ob.weekday() == 4 and my_dt_ob.hour == 10 and weeklytest == False:
            broadcast_message(logger.info, to_emails, alarmname, incubatornames, status, None, 'Weekly heartbeat - still running')
            logger.info('Connected to network as ' + socket.gethostname() + ' (' + get_ip() + ')')
            weeklytest = True
        elif my_dt_ob.hour == 11:
            weeklytest = False
        
        
        if my_dt_ob.second < 5 and my_dt_ob.minute == 0:
            logger.debug('Hourly heartbeat - still running')
        
        
        ###Finally sleep  to throttle the main control loop
        for i in range(0, 2):
            time.sleep(3)
            set_led_state(indicator,1)
            time.sleep(3)
            set_led_state(indicator,0)
    except Exception:
        logger.exception("Fatal error in main loop")


logger.critical("Loop ended -- this shouldn't happen")
