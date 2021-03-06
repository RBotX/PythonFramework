__author__ = 'Evan Racah'


import time
import dill
import pickle
import numpy as np
import os
import shutil
import getpass
import socket

#TODO: Way to do this without needing to login?
def send_email(address='agress@ucdavis.edu', subject=''):
    import smtplib
    from email.mime.text import MIMEText
    import email
    msg = MIMEText('')
    msg['Subject'] = subject
    msg['From'] = address
    msg['To'] = address
    msg['Message-id'] = email.Utils.make_msgid()
    #s = smtplib.SMTP('smtp.gmail.com:587')
    #s.starttls()
    s = smtplib.SMTP('smtp.gmail.com')

    s.sendmail(address, [address], msg.as_string())
    s.quit()

#ordering is [i_mid, i_close, i_far]
def compute_min_pair(x0, x1, x2):
    x = np.asarray([x0,x1,x2])
    i_mid = (np.percentile(x,50) == x).nonzero()[0][0]
    x_mid = x[i_mid]
    di0 = abs(x0 - x_mid)
    di1 = abs(x1 - x_mid)
    di2 = abs(x2 - x_mid)
    d = np.asarray([di0,di1,di2])
    assert not (d==0).all()
    i_close = (np.percentile(d,50) == d).nonzero()[0][0]
    i_far = np.setdiff1d(np.asarray([0,1,2]), np.asarray([i_mid, i_close]))[0]
    x_ordered = (x[i_mid], x[i_close], x[i_far])
    return (i_mid, i_close, i_far)

def get_hostname():
    return socket.gethostname()

def flatten_list_of_lists(list_of_lists):
    return [item for sublist in list_of_lists for item in sublist]

def is_laptop():
    laptop_hostnames = {'LAPTOP-9Q14E7KT'}
    return get_hostname() in laptop_hostnames

def get_user_name():
    name = getpass.getuser()
    return name

#from http://stackoverflow.com/questions/483666/python-reverse-inverse-a-mapping
def invert_dict(d):
    inv_dict = {v : k for k,v in d.items()}
    return inv_dict

def delete_dir_if_empty(file_name):
    if os.path.isdir(file_name) and not os.listdir(file_name):
        delete_dir_if_exists(file_name)

def delete_file(file_name):
    try:
        assert os.path.isfile(file_name)
        os.remove(file_name)
    except:
        assert not os.path.exists(file_name)


def delete_dir_if_exists(dir_name):
    """
    Deletes dir_name if it exists
    :param dir_name: directory to delete
    :return:
    """
    if dir_name is not None and os.path.isdir(dir_name):
        shutil.rmtree(dir_name)

def remove_suffix(s, suffix):
    if s[-len(suffix):] == suffix:
        s = s[:-len(suffix)]
    return s

def make_dir_for_file_name(file_name):
    """
    Creates directory for file_name
    :param file_name: path for a file
    :return:
    """
    d = os.path.dirname(file_name)
    if d != '' and not os.path.exists(d):
        try:
            os.makedirs(d)
        except:
            assert os.path.exists(d)

def save_object(file_name,object):
    """
    Saves object to file_name using pickle
    :param object: object to save
    :param file_name: file to save object to
    :return:
    """
    make_dir_for_file_name(file_name)
    with open(file_name, 'wb') as f:
        pickle.dump(object, f, pickle.HIGHEST_PROTOCOL)

def load_object(file_name):
    """
    Loads a saved python object using pickle
    :param file_name: file the object is saved to
    :return: the loaded loaded object
    """
    with open(file_name, 'rb') as f:
        data = pickle.load(f)
    return data




#TODO: Have filename be read from a config file
def recall(path, filename):
    with open(path + filename, 'rb') as f:
        return pickle.load(f)

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def any_numbers(lst):
    for elem in lst:
        if isinstance(elem,float):
            return True
    return False


def no_numbers(lst):
    return not any_numbers(lst)

def convert_to_float(element):
    if is_number(element):
        return float(element)
    else:
        return element

def convert_list_to_floats(lst):
    return map(convert_to_float,lst)


def get_x_y_from_matrix(matrix):
    x = matrix[:,1:-1]
    y = matrix[:,-1]
    #y = y.reshape((y.shape[0],1))
    return x,y

def load_from_csv(filename):
    return np.genfromtxt(filename,delimiter=',')

def get_x_y_from_file(filename):
    data_matrix = load_from_csv(filename)
    return get_x_y_from_matrix(data_matrix)



def save_to_csv(filename,array):
    np.savetxt(filename,array,delimiter=',')

def append_to_csv(filename,array):
    with open(filename,'a') as f:
        np.savetxt(f,array,delimiter=',')


def num_unique(l):
    """
    Returns the number of unique elements in list l
    :param l: a list
    :return: numbers of unique elements in l
    """
    return len(set(l))

def check_input(*args):
    """
    Asserts that each ndarray in args has the same length
    :param args: 2 or more one dimensional ndarrays
    :return:
    """
    for arg in args[1:]:
        assert args[0].shape[0] == arg.shape[0]

def flatten_list_of_lists(list):
    """
    Converts a nested list to a list
    :param list: a list of lists
    :return: Flattened list
    """
    return [item for sublist in list for item in sublist]

def get_date_string():
    """
    Returns a string version of today's date
    :return: string version of today's date
    """
    t = time.localtime()
    return str(t.tm_mon) + '-' + str(t.tm_mday) + '-' + str(t.tm_year)

def get_temp_dir():
    """
    Returns the project's "temp" directory which can be used for saving temporary files
    :return: path to temporary directory
    """
    return os.getenv('ML_CASP_TEMP_DIR', 'temp') + '/'

def convert_to_list(val):
    """
    Converts val to a list.  If val is a string, then [val] is returned.  Otherwise, attempts to convert
    val to a list.  If this fails, then returns [val]
    :param val: an object
    :return: list version of val
    """
    if isinstance(val, str):
        val = [val]
    try:
        val = list(val)
    except:
        val = [val]
    return val

def is_list_of_floats(l):
    """
    Returns whether or not each element in l can be converted to a float
    :param l: list
    :return: Whether or not each element in l can be converted to a float
    """
    for value in l:
        try:
            float(value)
        except:
            return False
    return True
