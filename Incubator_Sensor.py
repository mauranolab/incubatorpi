import RPi.GPIO as IO
import time
import smtplib
from datetime import datetime


def led_blink(color,state):
    IO.setmode(IO.BOARD)
    IO.setup(40,IO.OUT)
    IO.setup(38,IO.OUT)
    if color == 'green':
        pin = 38
    elif color == 'red':
        pin = 40
    IO.output(pin,state)

def send_email1(user, pwd, recipient, subject, body):
    report = True
    FROM = user
    TO = recipient if type(recipient) is list else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    print(message)
    try:
        print("trying to send email")
        server = smtplib.SMTP("smtp.nyumc.org")
        #server.ehlo()
        server.sendmail(FROM, TO, message)
        server.quit()
        print('successfully sent the mail')
    except:
        report = False
        print("failed to send mail")
    return report


def send(incubator, message_num):
    
    to_emails = ['maurano@nyu.edu','ranbroshran@gmail.com','martij44@nyu.edu']
    
    messages = ['Maurano848 Incubator #' +str(incubator)+' has entered Alarm State\n\n',
                'Maurano848 Incubator #' +str(incubator)+' has recovered from Alarm State\n\n',
                'Maurano848 Alarm System Weekly Update\n\n']
    
    body = messages[message_num] + str(datetime.now())
    double_check = True

    for email in to_emails:
        check = send_email1('andrew.martin@nyumc.org ', '', email, 'Maurano848 Incubator Alarm', body)
        if check == False:
            double_check = False
    return double_check


def write_log(filename, message):
    log_file = open('/home/pi/Alarm/Log/'+filename, 'a+')
    log_file.write(str(datetime.now()) + ' : ' + message + '\n')
    log_file.close()


def main():
    # Setting up input pins to detect incubator alarm.
    IO.setmode(IO.BOARD)
    IO.setup(12, IO.IN, pull_up_down=IO.PUD_DOWN) #DOWN = low voltage, Incubator Alarm Contacts 2-com, 3-N.O.
    IO.setup(11, IO.IN, pull_up_down=IO.PUD_DOWN)
    IO.setup(10, IO.IN, pull_up_down=IO.PUD_DOWN)
    IO.setup(8, IO.IN, pull_up_down=IO.PUD_DOWN)
    
    alarm = False
    alarm_check = True
    weeklytest = True
    week_counter = 0
    
    while True:
        my_dt_ob = datetime.now()
        log_name = 'Maurano848Log_' +str(my_dt_ob.year) +'-'+str(my_dt_ob.month) +'-'+str(my_dt_ob.day)+ ':'+str(my_dt_ob.day+7) +'.txt'
        date_list = [my_dt_ob.year, my_dt_ob.month, my_dt_ob.day, my_dt_ob.hour, my_dt_ob.minute, my_dt_ob.second]

        if (my_dt_ob.day)%7 == 1 and my_dt_ob.hour == 10 and weeklytest == False:
            #if my_dt_ob.hour == 10 and weeklytest == False
            weekly_log_name = 'Maurano848 Weekly_Log_' +str(my_dt_ob.year) +'-'+str(my_dt_ob.month) +'-'+str(my_dt_ob.day)+ ':'+str(my_dt_ob.day+7) +'.txt'
            write_log(weekly_log_name, 'Maurano848 Weekly Log - Running')
            send(1,2)
            weeklytest = True        

        elif my_dt_ob.hour == 11:
            weeklytest = False
            
        elif my_dt_ob.second < 5 and my_dt_ob.minute == 0:
            write_log(log_name, 'Maurano848 Daily Log - Running')
            week_counter += 1
            if week_counter > (24*7):
                send(1,2)
                week_counter = 0
        #IO.input(pin) measures current status of the pin
        #in this case, it returns either 0 or 1
        #In the all good state, status = [1, 1, 1, 1]
        status = [IO.input(12),IO.input(11),IO.input(10),IO.input(8)]
        print(status)
        print(str(datetime.now()))
        print()
        
        if 0  not in status:
            indicator = 'green'
            if alarm == True and alarm_check == True:
                log_message = 'Maurano848 Alarm Recovered for incubator number: ' + str(alarm_number)
                write_log(log_name, log_message)
                send(alarm_number,1)
                alarm = False #updating previous alarm state to clear
                
        else:
            indicator = 'red'
            for i in range(4):
                if status[i] == 0: #checking for current alarm state
                    if alarm == False: #check for previous alarm state
                        alarm_number = i+1
                        log_message = 'Maurano848 Alarm Detected in incubator number: ' + str(alarm_number)
                        write_log(log_name, log_message)
                        alarm_check = send(alarm_number,0)
                        alarm = True #updating previous alarm state to alarmed
                        
        led_blink(indicator,1)
        time.sleep(2)
        led_blink(indicator,0)
        time.sleep(2)


main()
