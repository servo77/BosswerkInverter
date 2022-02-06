import socket
import struct
import libscrc
import json
import sys
import os
import configparser
from binascii import *

os.chdir(os.path.dirname(sys.argv[0]))

# Read config
configParser = configparser.RawConfigParser()
configFilePath = r'./config.cfg'
configParser.read(configFilePath)

logger_ip = configParser.get('BosswerkInverter', 'logger_ip')
logger_port = int(configParser.get('BosswerkInverter', 'logger_port'))
# format like 40xxxxxxxx
logger_sn = int(configParser.get('BosswerkInverter', 'logger_sn'))
# 1 - parse message to json, 0 - output power / temp only
output_to_json = int(configParser.get('BosswerkInverter', 'output_to_json'))
# output additional message details
msg_details_output = int(configParser.get(
    'BosswerkInverter', 'msg_details_output'))

# Read register map
jsonmap = './DYRealTime.json'
with open(jsonmap) as txtfile:
    parameters = json.loads(txtfile.read())

# Initialize variables
if output_to_json:
    output = '{'  # initialize json output
else:
    output = ''  # initialize for vzlogger
    voltagedc1 = 0
    voltagedc2 = 0

# register start (other possible values 0x00/0x27 0x3b/0x36 0x96/0x2d)
reg_ini = int('0x56', 16)
reg_len = int('0x20', 16)  # register length


def dataextract(data):
    length, controlcode, serialin, serialout, logger_sn = struct.unpack_from(
        '<xHHBBI', data, offset=0)
    # like b'020000000000000000000000000000010300000027d005'
    datafield = data[11:11+length]
    businesskey, msg_reg_ini, msg_reg_len, crc = struct.unpack(
        '>HHHH', datafield[-8:])  # 010300000027d005
    if msg_details_output:
        print("Received new message. Length: %s" % length)
        print("controlcode: 0x%X" % controlcode)
        print("serialin: %s serialout: %s" % (serialin, serialout))
        print("logger_sn: %s" % logger_sn)
        print("businessfield: 0x%X reg_ini: %s reg_len: %s crc: 0x%X" %
              (businesskey, msg_reg_ini, msg_reg_len, crc))
    return datafield, length


def messagebuild(reg_ini, reg_len):
    msgStart = b'\xA5'  # start
    length = b'\x17\x00'  # datalength
    controlcode = b'\x10\x45'  # controlCode
    message_sn = b'\x00\x00'  # serial
    logger_sn_reverse = struct.pack('<I', int(logger_sn))
    # com.igen.localmode.dy.instruction.send.SendDataField
    datafield = unhexlify('020000000000000000000000000000')

    businessfield = b'\x01\x03' + \
        reg_ini.to_bytes(2, byteorder='big') + \
        reg_len.to_bytes(2, byteorder='big')  # sin CRC16MODBUS
    crc = libscrc.modbus(businessfield).to_bytes(
        2, byteorder='little')  # CRC16modbus

    frame_bytes = length + controlcode + message_sn + \
        logger_sn_reverse + datafield + businessfield + crc

    checksum = 0
    for i in range(0, len(frame_bytes), 1):
        checksum += frame_bytes[i] & 255
    checksum = (checksum & 255).to_bytes(1, byteorder='big')
    msgEnd = b'\x15'
    return msgStart + frame_bytes + checksum + msgEnd


try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)  # to fail sooner than 15 sec period of vzlogger exec
except OSError as msg:
    s = None
    print('could not open socket')
    print(msg)
    sys.exit(1)
try:
    s.connect((logger_ip, logger_port))
except OSError as msg:
    s.close()
    print('could not connect to host: %s, port: %s' % (logger_ip, logger_port))
    print(msg)
    sys.exit(1)

sdata = messagebuild(reg_ini, reg_len)
with s:
    s.sendall(sdata)
    data = s.recv(1024)
    if not data:
        print('could not receive data')
        sys.exit(1)

if msg_details_output:
    print('->Data sent: %s' % hexlify(sdata))

if msg_details_output:
    print('<-Data recieved: %s' % hexlify(data))

rdata = dataextract(data)

offset = 17  # ignore timestamp etc.

while offset < rdata[1]:

    hexpos = '0x%0*X' % (4, reg_ini + (offset - 17) // 2)

    for parameter in parameters:
        for item in parameter["items"]:
            title = item["titleEN"]
            ratio = item["ratio"]
            unit = item["unit"]
            for register in item["registers"]:
                if register == hexpos:
                    match item['interactionType']:
                        case 1:
                            match item['parserRule']:
                                case 1 | 2 | 3 | 4: result = round(struct.unpack_from('>H', rdata[0], offset=offset)[0] * ratio, 2)
                                case 5:  # leave as is
                                    result = str(rdata[0][offset:offset+2])
                        case 2:
                            for optionRange in item['optionRanges']:
                                if optionRange['key'] == struct.unpack_from('>H', rdata[0], offset=offset)[0]:
                                    try:
                                        result = optionRange['valueEN']
                                    except KeyError:
                                        result = optionRange['value']
                    match output_to_json:
                        case 1:
                            output = output+"\"" + title + \
                                "(" + unit + ")" + \
                                "\":" + str(result)+","
                        case 0:
                            match hexpos:  # prepare output for vzlogger
                                case '0x0056':
                                    output += 'powerac ' + \
                                        str(result) + '\n'
                                case '0x005A':
                                    if result != 0:
                                        output += 'temp ' + \
                                            str(result/10-10) + '\n'
                                case '0x006D':
                                    voltagedc1 = result
                                case '0x006E':
                                    output += 'powerdc1 ' + \
                                        str(round(voltagedc1*result, 2)) + '\n'
                                case '0x006F':
                                    voltagedc2 = result
                                case '0x0070':
                                    output += 'powerdc2 ' + \
                                        str(round(voltagedc2*result, 2)) + '\n'

                    if msg_details_output:
                        print(hexpos + "-" + title + ":" + str(result) + unit)
    offset += 2  # read every second byte
if output_to_json:
    output = output[:-1]+"}"

print(output)
