import datetime


def generate_name(name):
    """
    This function generates an unique name by adding a timestamp at the end of the provided name
    """

    new_name = str(name) + '_{:%Y_%m_%d_%H_%M_%S}'.format(datetime.datetime.now())
    return new_name
