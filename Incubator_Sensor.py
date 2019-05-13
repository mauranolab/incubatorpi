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
    gmail_user = user
    gmail_pwd = pwd
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
        server = smtplib.SMTP("smtp.nyumc.org", 25, timeout = 30)
        server.ehlo()
        server.sendmail(FROM, TO, message)
        server.close()
        print('successfully sent the mail')
    except:
        report = False
        print("failed to send mail")
    return report


def send(incubator, message_num):
    
    to_emails = ['henri.berger@nyumc.org','hbhberger@gmail.com','amartin4191@gmail.com','andrew.martin@nyumc.org']
    
    messages = ['Incubator #' +str(incubator)+' has entered Alarm State\n(Final Test - Do not panic)\n',
                'Incubator #' +str(incubator)+' has recovered from Alarm State\n(Final Test - Do not panic)\n',
                'Incubator #' +str(incubator)+' Alarm System Weekly Update\n(Final Test - Do not panic)\n']
    
    body = messages[message_num] + str(datetime.now())
    double_check = True

    for email in to_emails:
        check = send_email1('andrew.martin@nyumc.org', '', email, 'Incubator Alarm', body)
        if check == False:
            double_check = False
    return double_check


def write_log(filename, message):
    log_file = open('/home/pi/Alarm/Log/'+filename, 'a+')
    log_file.write(str(datetime.now()) + ' : ' + message + '\n')
    log_file.close()


def main():
    IO.setmode(IO.BOARD)
    IO.setup(12, IO.IN, pull_up_down=IO.PUD_DOWN)
    IO.setup(11, IO.IN, pull_up_down=IO.PUD_DOWN)
    IO.setup(10, IO.IN, pull_up_down=IO.PUD_DOWN)
    IO.setup(8, IO.IN, pull_up_down=IO.PUD_DOWN)
    
    alarm = False
    alarm_check = True
    weeklytest = True

    while True:
        my_dt_ob = datetime.now()
        log_name = 'Log_' +str(my_dt_ob.year) +'-'+str(my_dt_ob.month) +'-'+str(my_dt_ob.day)+ ':'+str(my_dt_ob.day+7) +'.txt'
        date_list = [my_dt_ob.year, my_dt_ob.month, my_dt_ob.day, my_dt_ob.hour, my_dt_ob.minute, my_dt_ob.second]

        if (my_dt_ob.day)%7 == 1 and my_dt_ob.hour == 10 and weeklytest == False:
            #if my_dt_ob.hour == 10 and weeklytest == False
            log_name = 'Log_' +str(my_dt_ob.year) +'-'+str(my_dt_ob.month) +'-'+str(my_dt_ob.day)+ ':'+str(my_dt_ob.day+7) +'.txt'
            write_log(log_name, 'Weekly Log - Running')
            send(1,3)
            weeklytest == True        

        elif my_dt_ob.hour == 11:
            weeklytest == False
        elif my_dt_ob.second < 5 and my_dt_ob.minute == 0:
            write_log(log_name, 'Daily Log - Running')
        
        status = [IO.input(12),IO.input(11),IO.input(10),IO.input(8)]
        print(status)
        print(str(datetime.now()))
        print()
        
        if False not in status:
            indicator = 'green'
            if alarm == True and alarm_check == True:
                write_log(log_name, 'Alarm Recovered!')
                send(alarm_number,1)
                alarm = False
                
        else:
            indicator = 'red'
            for i in range(4):
                if status[i] == False:
                    if alarm == False:
                      	alarm_number = i+1
			write_log(log_name, 'Alarm Detected!')
                        alarm_check = send(alarm_number,0)
                        alarm = True
                        
        led_blink(indicator,1)
        time.sleep(2)
        led_blink(indicator,0)
        time.sleep(2)


main()





