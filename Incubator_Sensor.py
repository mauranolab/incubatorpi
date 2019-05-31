#!/usr/bin/python

import RPi.GPIO as IO
import time
import smtplib
from datetime import datetime
import signal
import sys
import logging
from logging.handlers import TimedRotatingFileHandler


###Global parameters to be configured per alarm
alarmname = 'Maurano_SB848'
to_emails = ['maurano@nyu.edu', 'ranbroshran@gmail.com', 'martij44@nyu.edu']
incubatornames = ['Incubator #1', 'Incubator #2', 'Incubator #3', 'Incubator #4']

###Utility functions
def led_blink(color,state):
    IO.setmode(IO.BOARD)
    IO.setup(40,IO.OUT)
    IO.setup(38,IO.OUT)
    if color == 'green':
        pin = 38
    elif color == 'red':
        pin = 40
    IO.output(pin,state)


#Will pass on any exceptions for send failure
def send_email(user, pwd, recipient, subject, body):
    FROM = user
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body
    
    # Prepare actual message
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
#    print(message)
#    print("trying to send email")
    server = smtplib.SMTP("smtp.nyumc.org")
    #server.ehlo()
    server.sendmail(FROM, TO, message)
    server.quit()
#    print('successfully sent the mail')


#%% in message will be replaced by incubator number
def broadcast_message(logger, to_emails, alarmname, incubatornames, incubatornum, message):
    message = message.replace('%%', str(incubatornum) + ' (' + incubatornames[incubatornum-1] + ')')
    body = alarmname + ' - ' + message + '\n\n' + str(datetime.now())
    
    logger(message)
    
    double_check = True
    for email in to_emails:
        try:
            #TODO Wrong severity level
            logger("Sending email to " + email)
            send_email('andrew.martin@nyumc.org ', '', email, alarmname + ' - ' + message, body)
        except Exception:
            #TODO Wrong severity level
            logger("ERROR failed to send email to " + email)
            double_check = False
    return double_check


###Main code begins here
#Setting up input pins to detect incubator alarm.
IO.setmode(IO.BOARD)
IO.setup(12, IO.IN, pull_up_down=IO.PUD_DOWN) #DOWN = low voltage, Incubator Alarm Contacts 2-com, 3-N.O.
IO.setup(11, IO.IN, pull_up_down=IO.PUD_DOWN)
IO.setup(10, IO.IN, pull_up_down=IO.PUD_DOWN)
IO.setup(8, IO.IN, pull_up_down=IO.PUD_DOWN)


#Configure logging
logger = logging.getLogger("IncubatorAlarmLog")
logger.setLevel(logging.DEBUG)

handler1 = TimedRotatingFileHandler('/home/pi/Alarm/Log/' + alarmname + ".txt", when="D", interval=30, backupCount=1000)
handler1.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s ' + alarmname + ' %(message)s', datefmt='%Y-%m-%d %H:%M'))
handler1.setLevel(logging.INFO)
logger.addHandler(handler1)

handler2 = logging.StreamHandler()
handler2.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s ' + alarmname + ' %(message)s', datefmt='%Y-%m-%d %H:%M'))
logger.addHandler(handler2)


#Set up handler to log a shutdown notice
def sigterm_handler(_signo, _stack_frame):
    #logger is a global variable
    logger.critical("Alarm monitor shutting down!")
    # Raises SystemExit(0):
    sys.exit(0)

signal.signal(signal.SIGTERM, sigterm_handler)


alarm = False
alarm_check = True
weeklytest = True


logger.critical('Started up successfully')


while True:
    try:
        ###Check whether we should send a heartbeat message
        my_dt_ob = datetime.now()
        
        if (my_dt_ob.day)%7 == 1 and my_dt_ob.hour == 10 and weeklytest == False:
            #if my_dt_ob.hour == 10 and weeklytest == False
            broadcast_message(logger.info, to_emails, alarmname, None, None, 'Weekly heartbeat - still running')
            weeklytest = True
        elif my_dt_ob.hour == 11:
            weeklytest = False
        
        
        if my_dt_ob.second < 5 and my_dt_ob.minute == 0:
            logger.debug('Hourly heartbeat - still running')
        
        
        ###Check current status
        #IO.input(pin) measures current status of the pin
        #in this case, it returns either 0 or 1
        #In the all good state, status = [1, 1, 1, 1]
        status = [IO.input(12), IO.input(11), IO.input(10), IO.input(8)]
        logger.debug("Incubator status: " + str(status))
        
        if 0 not in status:
            indicator = 'green'
            if alarm == True and alarm_check == True:
                broadcast_message(logger.critical, to_emails, alarmname, incubatornames, alarm_number, 'Incubator #%% has recovered')
                alarm = False #updating previous alarm state to clear
        else:
            indicator = 'red'
            for i in range(4):
                if status[i] == 0: #checking for current alarm state
                    if alarm == False: #check for previous alarm state
                        alarm_number = i+1
                        alarm_check = broadcast_message(logger.critical, to_emails, alarmname, incubatornames, alarm_number, 'Alarm detected in incubator #%%')
                        alarm = True #updating previous alarm state to alarmed
                    
        led_blink(indicator,1)
        time.sleep(2)
        led_blink(indicator,0)
        time.sleep(2)
    except Exception:
        logger.exception("Fatal error in main loop")


logger.critical("Loop ended -- this shouldn't happen")
