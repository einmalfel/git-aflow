import logging
from os import linesep
import subprocess


class GitUnexpectedError(Exception):
    """Git subprocess returns unexpected error"""


def get_output_01(command_and_args):
    """Returns command output if it runs successfully, None if it returns 1"""
    try:
        result = subprocess.check_output(command_and_args,
                                         stderr=subprocess.STDOUT).decode()[:-1]
    except subprocess.CalledProcessError as error:
        if error.returncode == 1:
            result = None
        else:
            raise GitUnexpectedError(' '.join(error.cmd) + ' returns ' +
                                     str(error.returncode) + '. Output: ' +
                                     error.output) from error
    except FileNotFoundError:
        logging.critical('Command ' + command_and_args[0] + ' not found!')
        raise
    logging.debug('Calling ' + ' '.join(command_and_args)
                  + '. Result: ' + str(result[1]) + linesep + 'Output:' +
                  linesep + result[0])
    return result


def check_01(command_and_args):
    try:
        subprocess.check_call(command_and_args, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as error:
        if error.returncode == 1:
            return False
        else:
            raise GitUnexpectedError(' '.join(error.cmd) + ' returns ' +
                                     str(error.returncode)) from error
    except FileNotFoundError:
        logging.critical('Command ' + command_and_args[0] + ' not found!')
        raise
    return True


def call(command_and_args):
    try:
        subprocess.check_call(command_and_args, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as error:
        raise GitUnexpectedError(' '.join(error.cmd) + ' returns ' +
                                 str(error.returncode)) from error
    except FileNotFoundError:
        logging.critical('Command ' + command_and_args[0] + ' not found!')
        raise


def get_output(command_and_args):
    try:
        result = subprocess.check_output(command_and_args,
                                         stderr=subprocess.STDOUT).decode()[:-1]
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


def get_output_and_exit_code(command_and_args):
    try:
        result = subprocess.check_output(
            command_and_args, stderr=subprocess.STDOUT).decode()[:-1], 0
    except subprocess.CalledProcessError as error:
        result = (error.output.decode()[:-1], error.returncode)
    except FileNotFoundError:
        logging.critical('Command ' + command_and_args[0] + ' not found!')
        raise
    logging.debug('Calling ' + ' '.join(command_and_args)
                  + '. Result: ' + str(result[1]) + linesep + 'Output:' +
                  linesep + result[0])
    return result
