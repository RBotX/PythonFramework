import copy
from copy import deepcopy
import numpy as np
from numpy.linalg import norm
import method
from preprocessing import NanLabelEncoding, NanLabelBinarizer
from data import data as data_lib
from sklearn.neighbors import KernelDensity
from sklearn.grid_search import GridSearchCV
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import StandardScaler
from results_class.results import Output
import cvxpy as cvx
import scipy
import transfer_methods

class GraphTransfer(method.Method):
    def __init__(self, configs=None):
        super(GraphTransfer, self).__init__(configs)
        self.cv_params = dict()
        self.sigma_nw = 0
        self.sigma_tr = 0
        self.alpha = 0
        self.just_transfer = False
        self.just_target = False
        #self.cv_params['sigma_nw'] = self.create_cv_params(-5, 5)
        #self.cv_params['sigma_tr'] = self.create_cv_params(-5, 5)
        self.cv_params['alpha'] = [0, .2, .4, .6, .8, 1]
        configs = deepcopy(configs)
        #configs.cv_use_data_type = False
        self.source_learner = method.NadarayaWatsonMethod(deepcopy(configs))

        self.nw_transfer = method.NadarayaWatsonMethod(deepcopy(configs))
        self.nw_target = method.NadarayaWatsonMethod(deepcopy(configs))
        assert not (self.just_transfer and self.just_target)
        if self.just_transfer:
            del self.cv_params['alpha']
            self.alpha = 0
        if self.just_target:
            del self.cv_params['alpha']
            self.alpha = 1


    def train_and_test(self, data):
        is_source = data.data_set_ids == self.configs.source_labels[0]
        is_target = data.data_set_ids == self.configs.target_labels[0]
        source_data = data.get_subset(is_source)
        target_data = data.get_subset(is_target)
        source_data.y = source_data.true_y
        source_data.set_target()
        source_data.data_set_ids[:] = self.configs.target_labels[0]
        self.source_learner.train_and_test(source_data)
        y_pred = self.source_learner.predict(target_data).y
        target_data.source_y_pred = y_pred
        return super(GraphTransfer, self).train_and_test(target_data)

    def train(self, data):
        I = data.is_labeled
        y_pred_source = data.source_y_pred[I]

        transfer_data = data.get_subset(I)
        transfer_data.x = np.expand_dims(y_pred_source, 1)
        self.nw_transfer.train_and_test(transfer_data)

        target_data = data.get_subset(I)
        self.nw_target.train_and_test(target_data)

    def predict(self, data):
        #d = data_lib.Data(np.expand_dims(data.source_y_pred, 1), data.y)
        transfer_data = deepcopy(data)
        transfer_data.x = np.expand_dims(data.source_y_pred, 1)
        transfer_pred =  self.nw_transfer.predict(transfer_data)
        target_pred = self.nw_target.predict(data)
        alpha = self.alpha
        if self.just_target:
            alpha = 1
        elif self.just_transfer:
            alpha = 0
        transfer_pred.y = (1-alpha)*transfer_pred.y + alpha*target_pred.y
        transfer_pred.fu = (1-alpha)*transfer_pred.fu + alpha*target_pred.fu
        return transfer_pred

    @property
    def prefix(self):
        s = 'GraphTransfer'
        if self.just_transfer:
            s += '_tr'
        if getattr(self, 'just_target', False):
            s += '_ta'
        return s