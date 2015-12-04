__author__ = 'Aubrey'

from configs import base_configs as bc
import numpy as np
from data_sets import create_data_set
from loss_functions import loss_function
CR = []
for i in range(0,4):
    a = [create_data_set.ng_c[i],create_data_set.ng_r[i]]
    CR.append(np.asarray(a))

def create_project_configs():
    return ProjectConfigs()

pc_fields_to_copy = bc.pc_fields_to_copy + [
    'target_labels',
    'source_labels'
]

#data_set_to_use = bc.DATA_BOSTONG_HOUSING
data_set_to_use = bc.DATA_NG




class ProjectConfigs(bc.ProjectConfigs):
    def __init__(self):
        super(ProjectConfigs, self).__init__()
        self.target_labels = []
        self.source_labels = []
        self.project_dir = 'base'
        self.num_labels = range(40,201,40)


        if data_set_to_use == bc.DATA_NG:
            self.set_ng_transfer()
        elif data_set_to_use == bc.DATA_BOSTONG_HOUSING:
            self.set_boston_housing()
        else:
            assert False

        self.num_labels = range(20,61,20)

    def set_ng_transfer(self):
        self.loss_function = loss_function.ZeroOneError()
        self.set_ng()
        self.target_labels = CR[0]
        self.source_labels = CR[1]
        self.labels_to_keep = np.concatenate((self.target_labels,self.source_labels))
        self.labels_to_not_sample = self.source_labels

class MainConfigs(bc.MainConfigs):
    def __init__(self):
        super(MainConfigs, self).__init__()
        pc = create_project_configs()
        self.copy_fields(pc,pc_fields_to_copy)
        from methods import transfer_methods
        from methods import method
        method_configs = MethodConfigs()

        fuse_log_reg = transfer_methods.FuseTransfer(method_configs)
        target_nw = transfer_methods.TargetTranfer(method_configs)
        target_nw.base_learner = method.NadarayaWatsonMethod(method_configs)
        nw = method.NadarayaWatsonMethod(method_configs)
        log_reg = method.SKLLogisticRegression(MethodConfigs())
        target_knn = transfer_methods.TargetTranfer(method_configs)
        target_knn.base_learner = method.SKLKNN(method_configs)

        self.learner = target_knn


class MethodConfigs(bc.MethodConfigs):
    def __init__(self):
        super(MethodConfigs, self).__init__()
        pc = create_project_configs()
        self.copy_fields(pc,pc_fields_to_copy)
        self.target_labels = pc.target_labels
        self.source_labels = pc.source_labels

class VisualizationConfigs(bc.VisualizationConfigs):
    def __init__(self):
        super(VisualizationConfigs, self).__init__()
        pc = create_project_configs()
        self.copy_fields(pc,pc_fields_to_copy)
        self.files = [
            'TargetTransfer+SKL-LogReg.pkl',
            'FuseTransfer+SKL-LogReg.pkl',
            'SKL-LogReg.pkl',
            'TargetTransfer+NW.pkl',
            'NW.pkl',
            'SKL-RidgeReg.pkl',
            'TargetTransfer+SKL-KNN.pkl'
        ]

class BatchConfigs(bc.BatchConfigs):
    def __init__(self):
        super(BatchConfigs, self).__init__()
        self.config_list = [MainConfigs()]