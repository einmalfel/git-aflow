import subprocess
import logging


def launch_and_get_stdout(command_and_args):
    try:
        result = subprocess.check_output(command_and_args).decode()[:-1]
    except FileNotFoundError:
        logging.critical('command ' + command_and_args[0] + ' not found!')
        raise
    logging.debug('calling ' + ' '.join(command_and_args)
                  + '. Result:\n' + result)
    return result


def launch_and_get_exit_code(command_and_args):
    try:
        subprocess.check_call(command_and_args, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as error:
        result = error.returncode
    except FileNotFoundError:
        logging.critical('command ' + command_and_args[0] + ' not found!')
        raise
    else:
        result = 0
    logging.debug('calling ' + ' '.join(command_and_args)
                  + '. Result: ' + str(result))
    return result
