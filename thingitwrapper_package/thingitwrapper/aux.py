import logging
import os
import subprocess


try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'w')


debug_mode = os.environ.get('GIT_WRAPPER_DEBUG') == '1'


class GitUnexpectedError(Exception):
    """Git subprocess returns unexpected error"""


def get_output_01(command_and_args):
    """Returns command output if it runs successfully, None if it returns 1"""
    if debug_mode:
        output, exit_code = get_output_and_exit_code(command_and_args)
        if exit_code == 0:
            return output
        elif exit_code == 1:
            return None
        else:
            raise GitUnexpectedError(' '.join(command_and_args) + ' returns ' +
                                     str(exit_code) +
                                     '. 0 or 1 expected. Output: ' + output)
    else:
        try:
            return subprocess.check_output(
                command_and_args, stderr=subprocess.STDOUT).decode()[:-1]
        except subprocess.CalledProcessError as error:
            if error.returncode == 1:
                return None
            else:
                raise


def check_01(command_and_args):
    if debug_mode:
        output, exit_code = get_output_and_exit_code(command_and_args)
        if exit_code == 0:
            return True
        elif exit_code == 1:
            return False
        else:
            raise GitUnexpectedError(' '.join(command_and_args) + ' returns ' +
                                     str(exit_code) +
                                     '. 0 or 1 expected. Output: ' + output)
    else:
        exit_code = subprocess.call(command_and_args,
                                    stderr=DEVNULL,
                                    stdout=DEVNULL)
        if exit_code == 0:
            return True
        elif exit_code == 1:
            return False
        else:
            raise GitUnexpectedError(' '.join(command_and_args) + ' returns ' +
                                     str(exit_code) + '. 0 or 1 expected.')


def call(command_and_args):
    if debug_mode:
        output, exit_code = get_output_and_exit_code(command_and_args)
        if exit_code != 0:
            raise GitUnexpectedError(' '.join(command_and_args) + ' returns ' +
                                     str(exit_code) + '. Zero expected. ' +
                                     'Output: ' + output)
    else:
        subprocess.check_call(command_and_args,
                              stderr=DEVNULL,
                              stdout=DEVNULL)


def get_output(command_and_args):
    if debug_mode:
        output, exit_code = get_output_and_exit_code(command_and_args)
        if exit_code != 0:
            raise GitUnexpectedError(' '.join(command_and_args) + ' returns ' +
                                     str(exit_code) + '. Zero expected. ' +
                                     'Output: ' + output)
        else:
            return output
    else:
        return subprocess.check_output(
            command_and_args, stderr=subprocess.STDOUT).decode()[:-1]


def get_exit_code(command_and_args):
    if debug_mode:
        return get_output_and_exit_code(command_and_args)[1]
    else:
        return subprocess.call(command_and_args,
                               stderr=DEVNULL,
                               stdout=DEVNULL)


def get_output_and_exit_code(command_and_args):
    if debug_mode:
        logging.debug('Calling ' + ' '.join(command_and_args))
    try:
        result = subprocess.check_output(
            command_and_args, stderr=subprocess.STDOUT).decode()[:-1], 0
    except subprocess.CalledProcessError as error:
        result = (error.output.decode()[:-1], error.returncode)
    except FileNotFoundError:
        logging.critical('Command ' + command_and_args[0] + ' not found!')
        raise
    if debug_mode:
        logging.debug('Result: ' + str(result[1]) + ' Output:' + result[0])
    return result
