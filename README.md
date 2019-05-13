# incubatorpi
```
Raspberry pi code to monitor and alert based on RJ11 incubator alarm signals
Written by Henri Berger

The Incubator Alarms are Raspberry Pi Systems plugged into the various incubators which detect alarm states and send out alerts.
The raspberry pis are running the following headless version of raspbian:
2018-06-27-raspbian-stretch-lite.img
This distro can be found at the raspberry pi website:
https://www.raspberrypi.org/downloads/raspbian/
Once connected to the nyu network, the raspberry pis are auto assigned a local IP address that they will keep forever.
For example the prototype alarm is pi@10.148.19.148
The prototype uses default login
The systems have an "Alarm" folder in the home directory, which contains the python script that deos all the work.
 - home/pi/Alarm/2018-10-05_Incubator_Sensor.py
While running, this script monitors the incubators, generates logs and sends emails in the event of an alarm state.
The systems have an entry in their crontab so they they start the monitoring python script on every boot.
@reboot python3 /home/pi/Alarm/2018-10-05_Incubator_Sensor.py
This entry can be modified by the following command (After ssh-ing into the raspberry)
sudo crontab -e
and you should see this:
@reboot python3 /home/pi/Alarm/2018-10-05_Incubator_Sensor.py
```
