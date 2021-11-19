#!/usr/bin/python3
## ********************************************************************
## proxr_cli.py
## A Python3 Command Line Interface for the ProXR Relay Serial 
## Command Protocol
##
## Version:       1.0
## Last Modified: Nov 2021 (REW)
##
## Requirements:
## [1] proxr_lib.py (Python3) Ver 1.0
##
## USAGE:
## [0] All Modes
##        [{-d | --device} <device>] [{-b | --baud} <baud>]
##      <device> "/dev/tty*", eg. "/dev/ttyUSB0"
##        if not specified, defaults to "/dev/ttyUSB0"
##      <baud>   {9600,38400,57600,115200, etc}
##          if not specified, defaults to 115200
##      note: other settings hard-coded to 8N1, no hw flowctl as 
##            USB-serial is not normally affected by flowcontrol.
##
## [1] one-shot command mode
##        Runs once, processing the arguments, then closes the serial 
##      conn. and exits.
##
##        {-c | --command} <noun> [<relay> [<val>]]
##
##        Command one action on a specified relay. The actions (nouns) are:
##        {'on'}  <relay>                Turn a relay ON
##        {'off'} <relay>                Turn a relay OFF
##        {'set'} <relay> <val>            Set a relay to ON or OFF, based on <val>
##          {'get'|'read'} <relay>        Read a relay's current state (ON|OFF)
##        'status'                      Obtain relay board status
##        <relay> := [int](1..8)
##        <val> := {'on|'ON'|'off'|'OFF'}
##        'get' prints the relay state into stdout, either 'ON' or 'OFF'
##
## [2] interactive mode
##        Runs in a loop until interrupted with CTRL-C and then exits.
##      Note: CTRL-C signal is internally trapped.
##
##        {-i | --interactive}
##
##        Use above argument to enable the interactive mode. At the 
##      command prompt '> ' enter a command using the same syntax as 
##      used in [1]. Example:
##
##            > get 1
##              OFF
##          > set 7 on
##            OK
##          > status
##          ...
##
## Command Help
##    help | ?                            display this help
##  quit | exit                            exit interactive mode
##  set <relay> <val>                    set a relay state, on or off
##  get <relay>                            get a relay's state
##  on <relay>                            turn a relay on
##  off <relay>                            turn a relay off
##  status                                get relay boards status (mode)
##        <relay> := {1 .. 8}                    valid range of relays
##        <val>   := {'on' | 'off'}            valid values
##
## ********************************************************************

import proxr_lib as pxlib
import argparse as agp

ap = agp.ArgumentParser(description='ProXR CLI')
ap.add_argument('-d', '--device', default='/dev/ttyUSB0')
ap.add_argument('-b', '--baud', type=int, default=115200)
ap.add_argument('-i', '--interactive', action='store_true')
ap.add_argument('-c', '--command', nargs='*')
args = vars( ap.parse_args() )

loop_running = False

def print_help():
    print(
    '''
    Command Help
      help | ?                       display this help
      quit | exit                    exit interactive mode
      set <relay> <val>              set a relay state, on or off
      get <relay>                    get a relay's state
      on <relay>                     turn a relay on
      off <relay>                    turn a relay off
      status                         get relay boards status (mode)
        <relay> := {1 .. 8}          valid range of relays
        <val>   := {'on' | 'off'}    valid values
    '''
    )
    
def run_once( ep, cmdlist ):
    # ep :: serial endpoint object (instance)
    # cmdlist:: [<cmd>, <relay> [, <val>] ]
    # cmd   := {'on' | 'off' | 'set' | 'get' | 'status'}
    # argss       2      2       3       2         1
    # relay := {1..8}
    # val   := ('set' only') {'on|'ON'|'off'|'OFF'}
    cmd = None
    relay = None
    val = None
    if len(cmdlist) == 1:
        cmd = cmdlist[0]
    elif len(cmdlist) == 2:
        (cmd, relay) = cmdlist
    elif len(cmdlist) == 3:
        (cmd, relay, val) = cmdlist
    else:
        print("Command: - Syntax Error (arg count)")
        return
    
    if relay != None:
        try:
            relay = int(relay)
        except ValueError:
            print("Command: - Syntax Error (relay range: not a number!)")
            return
        if relay < 1 or relay > 8:
            print("Command: - Syntax Error (relay range) :: %s" % relay)
            return
        # convert relay # to zeros-based, for the library uses {0..7}
        relay = relay - 1
    
    if val != None:
        val = val.lower()
        if val != 'on' and val != 'off':
            print("Command: - Syntax Error (value) :: %s" % val)
            return
    
    if cmd == 'on':
        if relay == None:
            print("Command:on - Syntax Error (missing arg: relay #)")
            return
        rc = ep.Cmd_Relay(relay=relay, setOn=True)
        if rc == pxlib.CMDSTATE.OK:
            print("OK")
        else:
            print("ERROR")
            
    elif cmd == 'off':
        if relay == None:
            print("Command:off - Syntax Error (missing arg: relay #)")
            return
        rc = ep.Cmd_Relay(relay=relay, setOn=False)
        if rc == pxlib.CMDSTATE.OK:
            print("OK")
        else:
            print("ERROR")

    elif cmd == 'set':
        if relay == None or val == None:
            print("Command:set - Syntax Error (missing arg)")
            return
        rc = ep.Cmd_Relay(relay=relay, setOn=(val == 'on'))
        if rc == pxlib.CMDSTATE.OK:
            print("OK")
        else:
            print("ERROR")

    elif cmd == 'get':
        if relay == None:
            print("Command:get - Syntax Error (missing arg: relay #)")
            return
        rc = ep.Cmd_RelayState(relay=relay)
        if rc == pxlib.CMDSTATE.RSET:
            print("ON")
        elif rc == pxlib.CMDSTATE.RCLR:
            print("OFF")
        else:
            print("ERROR")

    elif cmd == 'status':
        status = ep.Cmd_CommsTest()
        print("Status: %s" % ep.StatusDesc(status)) 

    else:
        print("Command: - Syntax Error (unknown command)")
        return
        
    
def run_loop():
    ep = pxlib.ProXRLib(timeout=1)
    ep.open(devname=args['device'], baud=args['baud'])
    loop_running = True
    while loop_running:
        try:
            cmdstrn = input('> ')
            cmdargs = cmdstrn.split()
        except KeyboardInterrupt:
            loop_running = False
            print("")
            break
        if len(cmdargs) > 0:
            if cmdargs[0] == 'quit' or cmdargs[0] == 'exit':
                loop_running = False
            elif cmdargs[0] == 'help' or cmdargs[0] == '?':
                print_help()
            else:
                run_once(ep, cmdargs)
    ep.close()
    print("exited.")

if args['command'] == None and args['interactive'] == False:
    print('Error, please specify either an interactive mode or a command.')
    exit (1)
    
if args['interactive']:
    run_loop()
else:
    ep = pxlib.ProXRLib(timeout=1)
    ep.open(devname=args['device'], baud=args['baud'])
    run_once(ep, args['command'])
    ep.close()
