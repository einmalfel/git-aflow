import logging
from os import linesep
import subprocess


def get_stdout(command_and_args):
    try:
        result = subprocess.check_output(command_and_args).decode()[:-1]
    except subprocess.CalledProcessError as error:
        logging.critical('Command ' + ' '.join(command_and_args) +
                         ' failed. Exit code: ' + str(error.returncode) +
                         '. Output: ' + error.output.decode()[:-1])
        raise
    except FileNotFoundError:
        logging.critical('Command ' + command_and_args[0] + ' not found!')
        raise
    logging.debug('Calling ' + ' '.join(command_and_args)
                  + '. Result:' + linesep + result)
    return result


def get_exit_code(command_and_args):
    try:
        subprocess.check_call(command_and_args, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as error:
        result = error.returncode
    except FileNotFoundError:
        logging.critical('Command ' + command_and_args[0] + ' not found!')
        raise
    else:
        result = 0
    logging.debug('Calling ' + ' '.join(command_and_args)
                  + '. Result: ' + str(result))
    return result


def get_stdout_and_exit_code(command_and_args):
    try:
        result = subprocess.check_output(command_and_args).decode()[:-1], 0
    except subprocess.CalledProcessError as error:
        result = (error.output.decode()[:-1], error.returncode)
    except FileNotFoundError:
        logging.critical('Command ' + command_and_args[0] + ' not found!')
        raise
    logging.debug('Calling ' + ' '.join(command_and_args)
                  + '. Result: ' + str(result[1]) + linesep + 'Output:' +
                  linesep + result[0])
    return result