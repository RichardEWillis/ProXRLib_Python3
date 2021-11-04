#!/usr/bin/python3
## ********************************************************************
## proxr_lib.py
## A Python3 I/O Library for the ProXR Relay Serial Command Protocol
##
## Version:       1.0
## Last Modified: Nov 2021 (REW)
##
## Requirements:
## [1] PySerial Library (Python3) 
##     https://pyserial.readthedocs.io/en/latest/pyserial.html
##
## ********************************************************************

import serial
from enum import Enum

# decodes Comms-Test return value
class STATUS(Enum):
    RUN    = 85     # normal mode
    CONFIG = 86     # config set on bank/board
    LOCKDN = 87     # board in lockdown mode

# Command Return Code
class CMDSTATE(Enum):
    FAIL = -1       # Cmd Nack : Failed
    OK   =  0       # Cmd ACK  : Success
    RCLR =  1       # [Relay] Clear/Open
    RSET =  2       # [Relay] Set/Closed

class ProXRLib(object):

    # Timeout: affects blocking vs non-blocking
    #           0 := non-blocking
    #           n := block read for n seconds (floating pt. OK)
    #        None := wait forever on a read
    def __init__(self, timeout=0, useHWRTS=False, useHWDSR=False, useXONXOFF=False):
        self.tmout = timeout
        self.use_HW_RTSCTS = useHWRTS
        self.use_HW_DSRDTR = useHWDSR
        self.use_SW_XON_XOFF = useXONXOFF
        self.ser = None
        pass
    
    # Parity Types: 'N'one, 'E'ven, 'O'dd, 'M'ark, 'S'pace
    def open(self, devname, baud=115200, bits=8, stops=1, parity='N'):
        # san-checks
        e_bitsz  = serial.EIGHTBITS
        e_parity = serial.PARITY_NONE
        e_stops  = serial.STOPBITS_ONE
        
        # match-case is only available in Python ver3.10 and later
        # match bits:
            # case 5:
                # e_bitsz = serial.FIVEBITS
            # case 6:
                # e_bitsz = serial.SIXBITS
            # case 7:
                # e_bitsz = serial.SEVENBITS
            # case 8:
                # e_bitsz = serial.EIGHTBITS
            # case _:
                # raise Exception('Invalid bits, must be one of: {5,6,7,8}')

        if bits == 5:
            e_bitsz = serial.FIVEBITS
        elif bits == 6:
            e_bitsz = serial.SIXBITS
        elif bits == 7:
            e_bitsz = serial.SEVENBITS
        elif bits == 8:
            e_bitsz = serial.EIGHTBITS
        else:
            raise Exception('Invalid bits, must be one of: {5,6,7,8}')

        # match stops:
            # case 1:
                # e_stops  = serial.STOPBITS_ONE
            # case 2:
                # e_stops  = serial.STOPBITS_TWO
            # case _:
                # raise Exception('Invalid stops, must be one of: {1,2}')
        
        if stops == 1:
            e_stops  = serial.STOPBITS_ONE
        elif stops == 2:
            e_stops  = serial.STOPBITS_TWO
        else:
            raise Exception('Invalid stops, must be one of: {1,2}')
            
        # match parity:
            # case 'E':
                # e_parity = serial.PARITY_EVEN
            # case 'O':
                # e_parity = serial.PARITY_ODD
            # case 'N':
                # e_parity = serial.PARITY_NONE
            # case 'M':
                # e_parity = serial.PARITY_MARK
            # case 'S':
                # e_parity = serial.PARITY_SPACE
            # case _:
                # raise Exception('Invalid parity, must be one of: {E,O,N,M,S}')

        if parity == 'E':
            e_parity = serial.PARITY_EVEN
        elif parity == 'O':
            e_parity = serial.PARITY_ODD
        elif parity == 'N':
            e_parity = serial.PARITY_NONE
        elif parity == 'M':
            e_parity = serial.PARITY_MARK
        elif parity == 'S':
            e_parity = serial.PARITY_SPACE
        else:
            raise Exception('Invalid parity, must be one of: {E,O,N,M,S}')
            
        self.ser = serial.Serial(port=devname, baudrate=baud, bytesize=e_bitsz, 
            parity=e_parity, stopbits=e_stops, timeout=self.timeout, 
            xonxoff=self.use_SW_XON_XOFF, rtscts=self.use_HW_RTSCTS,
            dsrdtr=self.use_HW_DSRDTR, write_timeout=self.timeout,
            exclusive=True)
            
    def close(self):
        self.ser.close()
        self.ser = None

    def isOpen(self):
        return (self.ser != None)

    def _reader(self, count):
        if self.ser:
            return self.ser.read(count)
        return None
    
    def _readAck(self):
        inb = self._reader(1)
        return (inb.hex() == '55')
        
    # 'bout' must be of type 'bytearray'
    def _writer(self, bout):
        if self.ser:
            bout = bytearray(b'\xfe') + bout # add the preamble
            ret = self.ser.write(bout)
            return  ret - 1 # return no. 'bout' bytes sent, cmd preamble is not counted.
        return 0
    
    # Send a Comms Test.
    # Returns: one of {STATUS.RUN, STATUS.CONFIG, STATUS.LOCKDN} or None if closed.
    def Cmd_CommsTest(self):
        if self.ser:
            if self._writer(bytearray(b'\x21')) == 1:
                ack = self._reader(1)
                # match ack:
                    # case STATUS.RUN.value:
                        # return STATUS.RUN
                    # case STATUS.CONFIG.value:
                        # return STATUS.CONFIG
                    # case STATUS.LOCKDN.value:
                        # return STATUS.LOCKDN
                    # case _:
                        # raise Exception('Unexpected return value from CommsTest')
                
                if ack == STATUS.RUN.value:
                    return STATUS.RUN
                elif ack == STATUS.CONFIG.value:
                    return STATUS.CONFIG
                elif ack == STATUS.LOCKDN.value:
                    return STATUS.LOCKDN
                else:
                    raise Exception('Unexpected return value from CommsTest')
                    
        return None

    # Set/Clear a Relay
    # Bank: 1 .. 255 (Default = 1) (NOTE: Currently only Bank:1 is available)
    # Relay {0..7}. 0 := first relay in bank of 8
    # setOn {True, False} True := will close the relay contact (RSET).
    # Returns: (Enum)CMDSTATE: {OK,FAIL}
    def Cmd_Relay(self, relay=0, bank=1, setOn=False):
        if self.ser:
            if (relay > 7) or (relay < 0):
                raise Exception('Invalid Relay, range{0..7}')
            if bank != 1:
                raise Exception('Invalid Bank, At present, only 1 is supported')
            ba = bytearray()
            if setOn:
                ba.append(0x6c + relay)
            else:
                ba.append(0x64 + relay)
            ba.append(bank)
            if self._writer(ba) == 2 and self._readAck() == True:
                return CMDSTATE.OK
        return CMDSTATE.FAIL
        
    # Read a relay
    # Bank: 1 .. 255 (Default = 1) (NOTE: Currently only Bank:1 is available)
    # Relay {0..7}. 0 := first relay in bank of 8
    # Returns: (Enum)CMDSTATE: {FAIL,RCLR,RSET}
    def Cmd_RelayState(self, relay=0, bank=1):
        if self.ser:
            if (relay > 7) or (relay < 0):
                raise Exception('Invalid Relay, range{0..7}')
            if bank != 1:
                raise Exception('Invalid Bank, At present, only 1 is supported')
            ba = bytearray()
            ba.append(0x74 + relay)
            ba.append(bank)
            if self._writer(ba) == 2:
                res = self._reader(1)
                if res.hex() == '01':
                    return CMDSTATE.RSET
                else:
                    return CMDSTATE.RCLR
        return CMDSTATE.FAIL



class Loopback(ProXRLib):
    
    def __init__(self, timeout=0, useHWRTS=False, useHWDSR=False, useXONXOFF=False):
        self.loop = None
        self.relays = [0,0,0,0,0,0,0,0]
        super().__init__(timeout, useHWRTS, useHWDSR, useXONXOFF)

    def open(self, devname, baud=115200, bits=8, stops=1, parity='N'):
        self.ser = 1
        
    def close(self):
        self.ser = None
        
    def _reader(self, count):
        print('[Loopback._reader] : %s' % self.loop.hex())
        return self.loop
        
    def _writer(self, bout):
        print('[Loopback._writer] : %s' % bout.hex())
        self.loop = bytearray()
        assert(len(bout) >= 1), '[Loopback._writer] Error, command length too short'
        if (bout[0] >= 0x64) and (bout[0] <= 0x6b):
            ri = bout[0] - 0x64
            self.relays[ri] = 0
            self.loop.append(0x55)
        elif (bout[0] >= 0x6c) and (bout[0] <= 0x73):
            ri = bout[0] - 0x6c
            self.relays[ri] = 1
            self.loop.append(0x55)
        elif (bout[0] >= 0x74) and (bout[0] <= 0x7b):
            ri = bout[0] - 0x74
            self.loop.append( self.relays[ri] )
        else:
            assert(0), '[Loopback._writer] Error, unhandled relay command: %s' % hex(bout[1])
        return len(bout)
        
        
if __name__ == '__main__':
    
    print('[proxr_lib] run self-tests in loopback mode...')        

    pxr = Loopback()
    assert (pxr.relays == [0,0,0,0,0,0,0,0]), '[proxr_lib] Error, loopback relays in unexpected state'
    assert (pxr.isOpen() == False), '[proxr_lib] Error, endpoint should be closed.'
    pxr.open('/foo/bar')
    assert (pxr.isOpen() == True), '[proxr_lib] Error, endpoint should be open.'
    assert (pxr.Cmd_RelayState(relay=0) == CMDSTATE.RCLR), '[proxr_lib] Error, Relay[0] not open.'
    assert (pxr.Cmd_Relay(relay=0, setOn=True) == CMDSTATE.OK), '[proxr_lib] Error, failed to SET Relay[0].'
    assert (pxr.Cmd_RelayState(relay=0) == CMDSTATE.RSET), '[proxr_lib] Error, Relay[0] not closed.'
    assert (pxr.relays == [1,0,0,0,0,0,0,0]), '[proxr_lib] Error, loopback relays in unexpected state'
    pxr.close()
    assert (pxr.isOpen() == False), '[proxr_lib] Error, endpoint should be closed.'
    
    
