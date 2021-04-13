#!/usr/bin/python

# This code is an json-to-json adapter used in cim-prometheus-pipelines as an adapter 
# to change between prometheus format to the json-ld format
#
# Author: José Luis Mendoza Sánchez,
# Departamento de Ingeniería Telemática de la Universidad Politécnica de Madrid (DIT-UPM)

import json
import sys
import argparse
import logging
import os
import datetime


# Folder where to log
FOLDER = '/var/log/jsonFormatter/'

def main(log=False, debug=False):
    '''Main function. 
    It has 2 arguments which are flags for logging and debugging.
    '''
    if log:
        # Create folder where to log if previously not created. Requires Python 3.5 or greater
        os.makedirs(FOLDER, exist_ok=True)

        # Time of "now" in format YYYY-MM-DD_HH:MM:SS.FFF, being F the milliseconds
        currentDT=datetime.datetime.now()
        nowString = currentDT.strftime("%Y-%m-%d_%H-%M-%S.%f")[:-3]

        # Create logfile name with time string
        logfileName = FOLDER + nowString + '.log'

        # Create logger and adjust parameters
        logger = logging.getLogger('jsonFormatter_' + nowString)
        file_handler = logging.FileHandler(logfileName)
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # Set level depending on debug argument
        if debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    # This is the way to log in this program. When logging.DEBUG, it will only be actually written in file/console if debug argument was True
    if log: 
        logger.log(logging.DEBUG, "Program begins")

    # Read the file that came from Nifi
    # json2Format = json.load(sys.stdin)
    JSON_CONST = '{"status":"success","data":{"resultType":"vector","result":[{"metric":{"__name__":"node_boot_time_seconds","instance":"node-exporter:9100","job":"node"},"value":[1618227408.904,"1616074849"]}]}}'
    json2Format = json.loads(JSON_CONST)
    if log:
        logger.log(logging.INFO, "Read json: " + json.dumps(json2Format))
    






if __name__ == "__main__":
    prog = sys.argv[0]

    # Make all required
    parser = argparse.ArgumentParser(prog=prog, description="Json-to-json adapter used in cim-prometheus-pipelines")
    parser.add_argument('-d','--debug',dest='debug',action='store_true',help="Show debugging information when true")
    parser.add_argument('-l','--log',dest='log',action='store_true',help="Log information in '/var/log/jsonFormatter/'")
    arguments = parser.parse_args()

    # Extract arguments
    debug = arguments.debug
    log = arguments.log
    
    main(log=log, debug=debug)
