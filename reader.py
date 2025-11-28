from smartcard.System import readers
from smartcard.Exceptions import *
from smartcard.scard import (
    SCARD_SHARE_SHARED,
    SCARD_PROTOCOL_T0,
    SCARD_LEAVE_CARD,
    SCARD_RESET_CARD
)
import ndef
import time
import pyautogui as kbd
from usb.core import find as finddev


def extract_ndef(raw_bytes):
    i = 0
    while i < len(raw_bytes) and raw_bytes[i] == 0x00:
        i += 1
    if raw_bytes[i] != 0x03:
        raise ValueError(f"Expected NDEF TLV type 0x03, found {raw_bytes[i]:02X}")
    i += 1

    length = raw_bytes[i]
    i += 1

    ndef_bytes = raw_bytes[i:i+length]
    return ndef_bytes

r = readers()
print("Available readers:", r)
r = readers()[0].createConnection()

all_data = b''
gottag = False
firsttime = True
while True:
        try:
            time.sleep(0.1)
            r.connect()
            if (gottag == False):
                if (firsttime == True):
                    # here we turn the buzzer off. Usualy it buzzes when it detects a tag.
                    # A lot of people pull their tag away before the reader has a chance to actualy read it.
                    # So instead we buzz when we actualy have read the data.
                    turnOffBuzz = [0xFF, 0x00, 0x52, 0x00, 0x00]
                    resp, sw1, sw2 = r.transmit(turnOffBuzz)
                    firsttime = False
                all_data = b''

                key = [0xFF]*6  # default Key A
                load_key_apdu = [0xFF, 0x82, 0x00, 0x00, 0x06] + key
                resp, sw1, sw2 = r.transmit(load_key_apdu)
                load_key_apdu = [0xFF, 0x82, 0x00, 0x01, 0x06] + key
                resp, sw1, sw2 = r.transmit(load_key_apdu)
                if (sw1, sw2) != (0x90, 0x00):
                    raise Exception("Load key failed")
                try:
                    for page in range(1, 2):
                        absoluteBankNumber = 3 + (page*4)
                        auth_apdu = [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, absoluteBankNumber , 0x61, 0x00]
                        resp, sw1, sw2 = r.transmit(auth_apdu)
                        for block in range(4):
                            cmd = [0xFF, 0xB0, 0x00, int(absoluteBankNumber-3 + block), 0x10]
                            resp, sw1, sw2 = r.transmit(cmd)
                            all_data += bytes(resp)
                except Exception as e:
                    print("Error reading tag:", e)

                #once in a blue moon when a tag is removed before it can fully be read it fails here.
                # understandable really, the unfortunate thing is that the reader still thinks it has a tag. Very anoying.
                for record in ndef.message_decoder(extract_ndef(bytes(all_data))):
                    text = getattr(record, 'text', None)
                    turnOnBuzz = [0XFF,0x00,0X40,0X50,0X04,0X00,0x01,0x02,0x02]
                    resp, sw1, sw2 = r.transmit(turnOnBuzz)
                    print(text)
                    kbd.write(text, 0.1) # 0.1 second typewrite effect
                    gottag = True
        except NoCardException as e:
            gottag = False
        except Exception as e:
            r.disconnect()
            try:
                #reset the reader, it's stuck in limbo'
                dev = finddev(idVendor=0x072f, idProduct=0x2200)
                dev.reset()
            except:
                pass
            gottag = False
            firsttime = True
            time.sleep(2)



