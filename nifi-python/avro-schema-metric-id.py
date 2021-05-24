#!/usr/bin/python

# This code is a json-to-json format processor used in cim-prometheus-pipelines as an adapter 
# to create the metric-id from the json translated with avro schema that comes from the Kafka path
#
# From one that looks like this:
# 
# {
#   "labels" : {
#     "instance" : "node-exporter:9100",
#     "job" : "node"
#   },
#   "name" : "node_boot_time_seconds",
#   "timestamp" : 1.621847621678E9,
#   "value" : "1620127346",
#   "captureTimestamp" : 1621847621696
# }
# 
# To another that looks like this:
# 
# {
#     "id": "urn:ngsi-ld:Metric:hash_function(labels_dictionary)",
#     "labels" : {
#       "instance" : "node-exporter:9100",
#       "job" : "node"
#     },
#     "name" : "node_boot_time_seconds",
#     "timestamp" : 1.621847621678E9,
#     "value" : "1620127346",
#     "captureTimestamp" : 1621847621696
# }
#
# being the labels_dictionary:
#
# labels_dictionary = {
#   "__name__" : "node_cpu_seconds_total",
#   "instance" : "node-exporter:9100",
#   "job" : "node"
# },
# 
# Author: José Luis Mendoza Sánchez,
# Departamento de Ingeniería Telemática de la Universidad Politécnica de Madrid (DIT-UPM)

import json
import sys
import argparse
import logging
import os
import datetime
import hashlib

# Folder where to log
FOLDER = '/var/log/avro-schema-metric-id/'

def avro2metric_id(dict2Format):
    '''Parsing function.
    This function takes a dict which is supposed to be previously checked by checkPrometheusFormat function and calculates the metric-id
    Returns the dictionary directly as a json string.
    '''
    formattedJson = dict2Format

    # Initialize labels_dictionary
    labels_dictionary = dict()
    labels_dictionary["__name__"] = dict2Format["name"]
    labels_dictionary["instance"] = dict2Format["labels"]["instance"]
    labels_dictionary["job"]      = dict2Format["labels"]["job"]

    # Prometheus internally uses a 64-bit FNV-1 hash of the result.metric labels to identify a metric with a certain timestamp.
    # We are going to reuse this concept, but instead of using a FNV-1 hash, we are just going to do the MD5 hash of this dictionary.
    stringifiedLabels = json.dumps(labels_dictionary, sort_keys=True, indent=2) # sort_keys so that order does not affect
    hashedLabels = hashlib.md5(stringifiedLabels.encode("utf-8")).hexdigest()
    
    # Now we add "id" to the dictionary
    formattedJson['id'] = 'urn:ngsi-ld:Metric:' + hashedLabels
    
    return json.dumps(formattedJson)


def checkAvroSchemaFormat(dict2Check):
    ''' Checking function.
    This function checks if a given json has the expected Avro-schema format. 
    Otherwise, it raises an AssertionError with a descriptive message.
    '''

    # TODO: if ampliation is needed, consider using dict2Check.keys() method. We did not use it because there was very little advantage.
    if 'labels' not in dict2Check:
        raise AssertionError("'labels' key not found inside given json")
    if 'instance' not in dict2Check['labels']:
        raise AssertionError("'labels.instance' key not found inside given json")
    if 'job' not in dict2Check['labels']:
        raise AssertionError("'labels.job' key not found inside given json")
    if 'name' not in dict2Check:
        raise AssertionError("'name' key not found inside given json")
    if 'timestamp' not in dict2Check:
        raise AssertionError("'timestamp' key not found inside given json")
    if 'value' not in dict2Check:
        raise AssertionError("'value' key not found inside given json")
    if 'captureTimestamp' not in dict2Check:
        raise AssertionError("'captureTimestamp' key not found inside given json")

def main(log=False, debug=False):
    '''Main function. 
    It has 2 arguments which are flags for logging and debugging.
    '''
    if log:
        # Create folder where to log if previously not created. Requires Python 3.5 or greater
        os.makedirs(FOLDER, exist_ok=True)

        # Time of "now" in format YYYY-MM-DD_HH:MM:SS.FFF, being F the milliseconds
        currentDT=datetime.datetime.now()
        nowString = currentDT.strftime('%Y-%m-%d_%H-%M-%S.%f')[:-3]

        # Create logfile name with time string
        logfileName = FOLDER + nowString + '.log'

        # Create logger and adjust parameters
        logger = logging.getLogger('jsonFormatter_' + nowString)
        file_handler = logging.FileHandler(logfileName)
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        logger.addHandler(file_handler)

        # Uncomment handler to log in console (be careful, in the ExecuteStreamCommand of nifi sys.stdout is the outcoming FlowFile)
        # console_handler = logging.StreamHandler(sys.stdout)
        # console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        # logger.addHandler(console_handler)


        # Set level depending on debug argument
        if debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    # This is the way to log in this program. When logging.DEBUG, it will only be actually written in file and console
    # (if console handler is uncommented) if debug argument was True
    if log: 
        logger.log(logging.DEBUG, 'Program begins')

    # Read the file that came from Nifi
    try:
        dict2Format = json.load(sys.stdin) # In the ExecuteStreamCommand processor of Nifi, sys.stdin is the incoming FlowFile
    except Exception as e:
      if log:
          logger.log(logging.ERROR, 'Exception while parsing incoming FlowFile to JSON format.')
          logger.log(logging.ERROR, '    Exception name: ' +       e.__class__.__name__        )
          logger.log(logging.ERROR, '    Exception msg : ' +              str(e)               ) # Requires python 3.0 or greater
      raise e

    # Uncomment this section to substitute Nifi incoming FlowFile parsing by a mocked one
    # JSON_CONST = '[{"labels":{"instance":"node-exporter:9100","job":"node"},"name":"node_boot_time_seconds","timestamp":1621847621.678,"value":"1620127346","captureTimestamp":{"type":"Property","value":1621847621696}}]'
    # dict2Format = json.loads(JSON_CONST)

    # Log read json
    if log:
        logger.log(logging.INFO, 'Read json: ' + json.dumps(dict2Format))
    
    # Check the given format or raise exception instead
    try:
        checkAvroSchemaFormat(dict2Format)
    except Exception as e:
        if log:
            logger.log(logging.ERROR, 'Incoming JSON does not have expected format.')
            logger.log(logging.ERROR, '    Exception msg : ' +              str(e)               ) # Requires python 3.0 or greater
        raise e
    
    # Transform the format
    try:
        newJson = avro2metric_id(dict2Format)
    except Exception as e:
        if log:
            logger.log(logging.ERROR, 'Exception while parsing incoming JSON to NGSI-LD format.')
            logger.log(logging.ERROR, '    Exception name: ' +       e.__class__.__name__        )
            logger.log(logging.ERROR, '    Exception msg : ' +              str(e)               ) # Requires python 3.0 or greater
        raise e

    # Log formatted json
    if log:
        logger.log(logging.INFO, 'Formatted json: ' + newJson)

    # In the ExecuteStreamCommand processor of Nifi, sys.stdout is the outcoming FlowFile
    sys.stdout.write(newJson)

if __name__ == "__main__":
    prog = sys.argv[0]

    # Make all required
    parser = argparse.ArgumentParser(prog=prog, description="Json-to-json adapter used in cim-prometheus-pipelines")
    parser.add_argument('-d','--debug',dest='debug',action='store_true',help="Show debugging information when true")
    parser.add_argument('-l','--log',dest='log',action='store_true',help="Log information in '/var/log/avro-schema-metric-id/'")
    arguments = parser.parse_args()

    # Extract arguments
    debug = arguments.debug
    log = arguments.log
    
    main(log=log, debug=debug)
