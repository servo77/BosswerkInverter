# BosswerkInverter
Inspired by https://github.com/volkszaehler and cloned from https://github.com/jlopez77/DeyeInverter

Small utility for requesting Bosswerk Inverter MI 600 for AC and DC power ouput of two panels and sending data to vzlogger using ModBus protocol of Solarman Datalogger. Works with logger S/N 40* and Bosswerk Inverter S/N 21*. Temperature values are experimental, help is appreciated.

# Configuration

Edit the config.cfg and enter the following data:
```
[BosswerkInverter]
logger_ip=192.168.X.XXX
logger_port=8899
logger_sn=40XXXXXXXX
output_to_json=0 # ouput in json or vzlogger format
msg_details_output=0 # ouput message parsing details
```

# Steps

1. Install latest python3 (tested on 3.10). For Raspberry Pi you may have to compile it from sources. Refer to https://raspberrytips.com/install-latest-python-raspberry-pi/
```
cd && wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz
tar -zxvf Python-3.10.0.tgz
cd Python-3.10.0
./configure --enable-optimizations
sudo make altinstall
cd /usr/local/bin && sudo ln -s /usr/local/bin/python3.10 python3
```
2. Install libscrc module
```
sudo -H pip3 install libscrc
```
3. Clone repo to /home/pi/BosswerkInverter
```
cd && git clone https://github.com/servo77/BosswerkInverter.git
```
4. Adjust config.cfg to match your S/N and IP.
```
nano /home/pi/BosswerkInverter/config.cfg
```
5. Verify, vzlogger can execute script
```
sudo -u vzlogger python3 /home/pi/BosswerkInverter/InverterData.py
```
Returning something like:
```
powerac 300.0
temp 10.0
powerdc1 150.00
powerdc2 150.00
```
6. Create 4 new channels in volkszaehler, recording uuids per https://wiki.volkszaehler.org/software/middleware/einrichtung:
   * AC power (Typ: powersensor)
   * DC1 power (Typ: powersensor)
   * DC2 power (Typ: powersensor)
   * Temperature (Typ: temperature)
  
7. Modify **/etc/vzlogger.conf**, pasting uuids from above into right placeholders. Refer to provided example https://github.com/servo77/BosswerkInverter/blob/main/vzlogger_conf_example.jsonc

8. Restart vzlogger:
```
sudo systemctl restart vzlogger
```
   
9.  If everything was fine, you'll get results in less then a minute

<img src=https://github.com/servo77/BosswerkInverter/blob/main/volkszaehler_example.png>


# Run

```
$ python3 InverterData.py

powerac 300.0
temp 10.0
powerdc1 150.00
powerdc2 150.00
```
Running with output_to_json=1

```
{
    "Total Load Consumption(KWH)": 300.0,
    "DC Temperature(º)": 200.0,
    "AC Temperature(º)": 0.0,
    "Total Production(KWH)": 0.0,
    "Total Production(KWH)": 0.0,
    "Alert()": 0.0,
    "Alert()": 0.0,
    "Alert()": 0.0,
    "Alert()": 0.0,
    "Alert()": 0.0,
    "Alert()": 0.0,
    "Daily Production(KWH)": 0.0,
    "PV1 Voltage(V)": 30.0,
    "PV1 Current(A)": 5.0,
    "PV2 Voltage(V)": 30.0,
    "PV2 Current(A)": 5.0
}
```

# Troubleshooting
* **No data in volkszaheler**
  1. Verify you subscribed to channels and channels have correct uuids in **vzlogger.conf**
  2. Increase loglevel in **vzlogger.conf**
```
 "verbosity": 15
 ```
  3. look for MeterExec messages via
```
tail -f /var/log/vzlogger.log
```
* **Bosswerk logger times out**

Be patient, after some time it replies with data

# Known Issues

The inverter is not fast enough to answer, you can get timeouts if you query it too often.
Formula for temperature is experimental and may be ignored for now.

# Contrib

Welcome to submit messages from other Bosswerk inverters to see other values (tested on MI 600 version) 
