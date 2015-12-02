__author__ = 'Aubrey'

from sklearn import datasets
from sklearn.feature_extraction.text import TfidfVectorizer
from data import data as data_class
from utility import helper_functions
from utility import array_functions
import numpy as np

ng_a = np.asarray(0)
ng_c = np.asarray(range(1,6))
ng_m = np.asarray(6)
ng_r = np.asarray(range(7,11))
ng_s = np.asarray(range(11,15))
ng_o = np.asarray(15)
ng_t = np.asarray(range(16,20))

boston_housing_raw_data_file = 'boston_housing/raw_data.pkl'
ng_raw_data_file = '20ng/raw_data.pkl'

def create_uci_yeast():
    pass

def create_iris():
    pass

def create_20ng_data(file_dir=''):
    newsgroups_train = datasets.fetch_20newsgroups(
        subset='train',
        remove=('headers', 'footers', 'quotes')
    )
    data = data_class.Data()
    short_names = [
        #0
        'A',
        #1-5
        'C1','C2','C3','C4','C5',
        #6
        'M',
        #7-10
        'R1','R2','R3','R4',
        #11-14
        'S1','S2','S3','S4',
        #15
        'O',
        #16-19
        'T1','T2','T3','T4'
    ]
    data.label_names = short_names
    tf_idf = TfidfVectorizer(
        stop_words='english',
        max_df=.9,
        min_df=.001,
        max_features=5000
    )
    vectors = tf_idf.fit_transform(newsgroups_train.data)
    feature_counts = (vectors > 0).sum(0)
    data.x = vectors
    data.y = newsgroups_train.target
    data.set_defaults()
    data.is_regression = False
    class_counts = array_functions.histogram_unique(data.y)
    s = ng_raw_data_file
    if file_dir != '':
        s = file_dir + '/' + s
    helper_functions.save_object(s,data)

def create_boston_housing(file_dir=''):
    boston_data = datasets.load_boston()
    data = data_class.Data()
    data.x = boston_data.data
    data.y = boston_data.target
    data.feature_names = list(boston_data.feature_names)
    data.set_defaults()
    data.is_regression = True
    s = boston_housing_raw_data_file
    if file_dir != '':
        s = file_dir + '/' + s
    helper_functions.save_object(s,data)

if __name__ == "__main__":
    #create_boston_housing()
    create_20ng_data()
