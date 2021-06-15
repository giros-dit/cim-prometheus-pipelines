#!/usr/bin/python

# This code is an json-to-json format processor used in cim-prometheus-pipelines as an adapter
# to change between prometheus format to the NGSI-LD format that a CIM context broker like Scorpio requires:
#
# From one that looks like this:
#
# {
#   "status" : "success",
#   "data" : {
#     "resultType" : "vector",
#     "result" : [ {
#       "metric" : {
#         "__name__" : "node_cpu_seconds_total",
#         "instance" : "node-exporter:9100",
#         "job" : "node"
#       },
#       "value" : [ 1.618227408904E9, "1616074849" ]
#     } ]
#   }
# }
#
# To another that looks like this:
#
# {
#     "id": "urn:ngsi-ld:Metric:hash_function(result[0].metric)",
#     "type": "Metric",
#     "name": {
#         "type": "Property",
#         "value": "node_cpu_seconds_total"
#     },
#     "timestamp": {
#         "type": "Property",
#         "value": "1618227409"
#     },
#     "value": {
#         "type": "Property",
#         "value": "1616074849"
#     },
#     "labels": {
#         "type": "Property",
#         "value": {
#             "exporter" : "node_exporter",
#             "job" : "node-exporter:9100"
#         }
#     }
# }
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
FOLDER = '/var/log/jsonFormatter/'

def prometheus2NGSI_LDFormat(dict2Format):
    '''Parsing function.
    This function takes a dict which is supposed to be previously checked by checkPrometheusFormat function and parses it to NGSI-LD format.
    Returns the dictionary directly as a json string.
    '''
    formattedJson = dict()

    # Prometheus internally uses a 64-bit FNV-1 hash of the result.metric labels to identify a metric with a certain timestamp.
    # We are going to reuse this concept, but instead of using a FNV-1 hash, we are just going to do the MD5 hash of this dictionary.
    stringifiedLabels = json.dumps(dict2Format['metric'], sort_keys=True, indent=2) # sort_keys so that order does not affect
    hashedLabels = hashlib.md5(stringifiedLabels.encode("utf-8")).hexdigest()

    # Extract '__name__' from result.metric labels
    metricName = str(dict2Format['metric'].pop('__name__'))

    # Now we create the dictionary key by key
    # Some part of this code could have been simplified with a for loop, but we consider this would decrease readability
    formattedJson['id']                 = 'urn:ngsi-ld:Metric:' + hashedLabels
    formattedJson['type']               = 'Metric'
    formattedJson['name']               = dict()
    formattedJson['name']['type']       = 'Property'
    formattedJson['name']['value']      = metricName
    formattedJson['timestamp']          = dict()
    formattedJson['timestamp']['type']  = 'Property'
    formattedJson['timestamp']['value'] = str(int(dict2Format['value'][0]))
    formattedJson['value']              = dict()
    formattedJson['value']['type']      = 'Property'
    formattedJson['value']['value']     = dict2Format['value'][1]
    formattedJson['labels']             = dict()
    formattedJson['labels']['type']     = 'Property'
    formattedJson['labels']['value']    = dict2Format['metric'].copy()

    return json.dumps(formattedJson)


def checkPrometheusFormat(dict2Check):
    ''' Checking function.
    This function checks if a given json has the expected Prometheus format.
    Otherwise, it raises an AssertionError with a descriptive message.
    '''
    # TODO: if ampliation is needed, consider using dict2Check.keys() method. We did not use it because there was very little advantage.
    if 'status' not in dict2Check:
        raise AssertionError("'status' key not found inside given json")
    if 'data' not in dict2Check:
        raise AssertionError("'data' key not found inside given json")
    if 'resultType' not in dict2Check['data']:
        raise AssertionError("'data.resultType' key not found inside given json")
    if str(dict2Check['data']['resultType']) != 'vector':
        raise AssertionError("'data.resultType' takes value: " + str(dict2Check['data']['resultType']) + ". Expected: 'vector'")
    if 'result' not in dict2Check['data']:
        raise AssertionError("'data.result' key not found inside given json")
    if len(dict2Check['data']['result']) != 1:
        # TODO: in the future, this could be supported
        raise AssertionError("'data.result' vector length is: " + str(len(dict2Check['data']['result'])) +
            '. Expected: 1 (More than one metric are being queried. This processor does not support that)')
    if 'metric' not in dict2Check['data']['result'][0]:
        raise AssertionError("'data.result[0].metric' key not found inside given json")
    if '__name__' not in dict2Check['data']['result'][0]['metric']:
        raise AssertionError("'data.result[0].metric.__name__' key not found inside given json")
    if 'value' not in dict2Check['data']['result'][0]:
        raise AssertionError("'data.result[0].value' key not found inside given json")
    if len(dict2Check['data']['result'][0]['value']) != 2:
        raise AssertionError("'data.result[0].value' length is: " + str(len(dict2Check['data']['result'][0]['value'])) +
            '. Expected: 2 (the timestamp and the actual value of the metric)')
    if not isinstance(dict2Check['data']['result'][0]['value'][0], float):
        raise AssertionError("'data.result[0].value[0]' is an instance of: " + str(dict2Check['data']['result'][0]['value'][0]) +
            '. Expected instance: float (metric timestamp)')
    if not isinstance(dict2Check['data']['result'][0]['value'][1], str):
        raise AssertionError("'data.result[0].value[1]' is an instance of: " + str(dict2Check['data']['result'][0]['value'][1]) +
            '. Expected instance: str (metric value)')

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
    # JSON_CONST = '{"status":"success","data":{"resultType":"vector","result":[{"metric":{"__name__":"node_boot_time_seconds","instance":"node-exporter:9100","job":"node"},"value":[1618227408.904,"1616074849"]}]}}'
    # dict2Format = json.loads(JSON_CONST)

    # Log read json
    if log:
        logger.log(logging.INFO, 'Read json: ' + json.dumps(dict2Format))

    # Check the given format or raise exception instead
    try:
        # checkPrometheusFormat(dict2Format)
        pass
    except Exception as e:
        if log:
            logger.log(logging.ERROR, 'Incoming JSON does not have expected format.')
            logger.log(logging.ERROR, '    Exception msg : ' +              str(e)               ) # Requires python 3.0 or greater
        raise e

    # Transform the format
    try:
        newJson = prometheus2NGSI_LDFormat(dict2Format)
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
    parser.add_argument('-l','--log',dest='log',action='store_true',help="Log information in '/var/log/jsonFormatter/'")
    arguments = parser.parse_args()

    # Extract arguments
    debug = arguments.debug
    log = arguments.log

    main(log=log, debug=debug)
