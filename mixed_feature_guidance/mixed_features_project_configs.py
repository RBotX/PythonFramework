__author__ = 'Aubrey'
from collections import OrderedDict
from configs import base_configs as bc
from loss_functions import loss_function
from utility import helper_functions
from results_class import results as results_lib
from sklearn import grid_search
from utility import helper_functions
from methods import mixed_feature_guidance
from copy import deepcopy
# Command line arguments for ProjectConfigs
arguments = None

def create_project_configs():
    return ProjectConfigs()

pc_fields_to_copy = bc.pc_fields_to_copy + [
    'disable_relaxed_guidance',
    'disable_tikhonov',
    'random_guidance',
    'use_training_corr'
]
#data_set_to_use = bc.DATA_SYNTHETIC_LINEAR_REGRESSION_10_nnz4
#data_set_to_use = bc.DATA_SYNTHETIC_LINEAR_REGRESSION
#data_set_to_use = bc.DATA_SYNTHETIC_LINEAR_REGRESSION_10
#data_set_to_use = bc.DATA_DROSOPHILIA
#data_set_to_use = bc.DATA_BOSTON_HOUSING
#data_set_to_use = bc.DATA_WINE_RED
data_set_to_use = bc.DATA_CONCRETE
#data_set_to_use = bc.DATA_KC_HOUSING

viz_for_paper = False

run_experiments = True
run_batch_experiments = True

use_ridge = False
use_mean = False
use_quad_feats = False
mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
#mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_HARD_CONSTRAINT
#mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RIDGE

viz_w_error = False

all_data_sets = [data_set_to_use]
if run_batch_experiments:
    all_data_sets = [
        bc.DATA_BOSTON_HOUSING,
        #bc.DATA_DROSOPHILIA,
        bc.DATA_KC_HOUSING,
        bc.DATA_WINE_RED,
        bc.DATA_SYNTHETIC_LINEAR_REGRESSION_10,
        bc.DATA_CONCRETE
    ]


other_pc_configs = {
}

other_method_configs = {
    'num_random_pairs': 0,
    'num_random_signs': 10,
    'use_l1': True,
    'num_features': None,
    'use_nonneg': False,
    'use_stacking': False,
    'use_corr': True,
    'use_training_corr': False,
    'include_size_in_file_name': False,
    'num_features': -1,
    'use_validation': True,
    'use_test_error_for_model_selection': False,
    'y_scale_min_max': False,
    'y_scale_standard': False,
    'scipy_opt_method': 'L-BFGS-B',
    'cvx_method': 'SCS',
    'num_cv_splits': 10,
    'eps': 1e-10,
    'use_perfect_feature_selection': True
}

if data_set_to_use == bc.DATA_DROSOPHILIA:
    other_method_configs['num_features'] = 50

show_legend_on_all = True

max_rows = 3

if helper_functions.is_laptop():
    use_pool = False
    pool_size = 1
else:
    use_pool = False
    pool_size = 1

arguments = None
def apply_arguments(configs):
    if arguments.num_labels is not None:
        configs.overwrite_num_labels = arguments.num_labels
    if arguments.split_idx is not None:
        configs.split_idx = arguments.split_idx


class ProjectConfigs(bc.ProjectConfigs):
    def __init__(self, data_set=None, use_arguments=True):
        super(ProjectConfigs, self).__init__()
        self.project_dir = 'mixed_feature_guidance'
        self.use_pool = use_pool
        self.pool_size = pool_size
        if data_set is None:
            data_set = data_set_to_use
        self.set_data_set(data_set)
        self.num_splits = 30
        self.disable_relaxed_guidance = False
        self.disable_tikhonov = False
        self.random_guidance = True
        if use_arguments and arguments is not None:
            apply_arguments(self)

        for key, value in other_method_configs.items():
            setattr(self, key, value)


    def set_data_set(self, data_set):
        self.data_set = data_set
        if data_set == bc.DATA_BOSTON_HOUSING:
            self.set_data_set_defaults('boston_housing')
            self.num_labels = [10, 20, 40, 80]
            #self.num_labels = [80]
        elif data_set == bc.DATA_SYNTHETIC_LINEAR_REGRESSION:
            self.set_data_set_defaults('synthetic_linear_reg500-50-1.01')
            self.num_labels = [5, 10, 20, 40]
        elif data_set == bc.DATA_SYNTHETIC_LINEAR_REGRESSION_10:
            self.set_data_set_defaults('synthetic_linear_reg500-10-1.01')
            self.num_labels = [5, 10, 20, 40]
        elif data_set == bc.DATA_SYNTHETIC_LINEAR_REGRESSION_10_nnz4:
            self.set_data_set_defaults('synthetic_linear_reg500-10-1-nnz=4')
            self.num_labels = [10, 20, 40]
            #self.num_labels = [10]
        elif data_set == bc.DATA_ADIENCE_ALIGNED_CNN_1:
            self.set_data_set_defaults('adience_aligned_cnn_1_per_instance_id')
            self.num_labels = [10, 20, 40]
        elif data_set == bc.DATA_WINE_RED:
            self.set_data_set_defaults('wine-red')
            self.num_labels = [10, 20, 40]
            #self.num_labels = [160]
        elif data_set == bc.DATA_CONCRETE:
            self.set_data_set_defaults('concrete')
            self.num_labels = [5, 10, 20, 40]
        elif data_set == bc.DATA_DROSOPHILIA:
            self.set_data_set_defaults('drosophilia')
            self.num_labels = [10,20,40]
            #self.num_labels = [10, 20, 40, 80, 160]
        elif data_set == bc.DATA_KC_HOUSING:
            self.set_data_set_defaults('kc_housing')
            self.num_labels = [10, 20, 40]
            #self.num_labels = [160]
        '''
        if self.include_size_in_file_name:
            assert len(self.num_labels) == 1
        '''




class MainConfigs(bc.MainConfigs):
    def __init__(self, pc):
        super(MainConfigs, self).__init__()
        #pc = create_project_configs()
        self.copy_fields(pc,pc_fields_to_copy)
        from methods import method
        from methods import active_methods
        from methods import semisupervised
        from methods import preprocessing
        from methods import mixed_feature_guidance
        method_configs = MethodConfigs(pc)
        for key in other_method_configs.keys():
            setattr(method_configs, key, getattr(pc,key))

        ridge = method.SKLRidgeRegression(method_configs)
        mean_estimator = method.SKLMeanRegressor(method_configs)
        if use_quad_feats:
            ridge.preprocessor = preprocessing.BasisQuadraticPreprocessor()
            #ridge.preprocessor = preprocessing.BasisQuadraticFewPreprocessor()
        if use_mean:
            self.learner = mean_estimator
        elif use_ridge:
            self.learner = ridge
        else:
            method_configs.method = getattr(pc, 'mixed_feature_method', mixed_feature_method)
            self.learner = mixed_feature_guidance.MixedFeatureGuidanceMethod(method_configs)


class MethodConfigs(bc.MethodConfigs):
    def __init__(self, pc):
        super(MethodConfigs, self).__init__()
        self.copy_fields(pc,pc_fields_to_copy)

class BatchConfigs(bc.BatchConfigs):
    def __init__(self, pc):
        super(BatchConfigs, self).__init__()
        from experiment.experiment_manager import MethodExperimentManager
        self.method_experiment_manager_class = MethodExperimentManager
        if not run_batch_experiments:
            self.config_list = [MainConfigs(pc)]
            return
        else:
            self.config_list = []
            for data_set in all_data_sets:
                pc = ProjectConfigs(data_set)

                p = deepcopy(pc)
                p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
                p.num_random_pairs = 0
                p.num_random_signs = 10
                self.config_list.append(MainConfigs(p))
                if data_set in {bc.DATA_SYNTHETIC_LINEAR_REGRESSION, bc.DATA_DROSOPHILIA}:
                    p = deepcopy(p)
                    p.num_random_pairs = 0
                    p.num_random_signs = 50
                    self.config_list.append(MainConfigs(p))

                p = deepcopy(pc)
                p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
                p.num_random_pairs = 0
                p.num_random_signs = 10
                p.use_training_corr = True
                self.config_list.append(MainConfigs(p))

                p = deepcopy(pc)
                p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
                p.num_random_pairs = 0
                p.num_random_signs = 5
                self.config_list.append(MainConfigs(p))

                p = deepcopy(p)
                p.disable_relaxed_guidance = True
                p.num_random_signs = 10
                self.config_list.append(MainConfigs(p))
                if data_set in {bc.DATA_SYNTHETIC_LINEAR_REGRESSION, bc.DATA_DROSOPHILIA}:
                    p = deepcopy(p)
                    p.num_random_pairs = 0
                    p.num_random_signs = 50
                    self.config_list.append(MainConfigs(p))

                p = deepcopy(p)
                p.disable_relaxed_guidance = False
                p.num_random_signs = 0
                p.num_random_pairs = 10
                self.config_list.append(MainConfigs(p))

                p = deepcopy(p)
                p.disable_relaxed_guidance = False
                p.num_random_signs = 0
                p.num_random_pairs = 0
                m = MainConfigs(p)
                m.learner.use_nonneg = True
                m.learner.use_corr = False
                self.config_list.append(m)

                p = deepcopy(p)
                p.disable_relaxed_guidance = True
                p.num_random_signs = 0
                m = MainConfigs(p)
                m.learner.use_nonneg = True
                m.learner.use_corr = False
                self.config_list.append(m)
                '''
                p = deepcopy(p)
                p.num_random_pairs = 10
                p.num_random_signs = 0
                self.config_list.append(MainConfigs(p))
                '''

                p = deepcopy(pc)
                p.disable_relaxed_guidance = False
                p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RIDGE
                self.config_list.append(MainConfigs(p))
                #assert False, 'Not Implemented Yet'

class VisualizationConfigs(bc.VisualizationConfigs):
    def __init__(self, data_set=None, **kwargs):
        super(VisualizationConfigs, self).__init__(data_set, **kwargs)
        self.max_rows = 2
        pc = ProjectConfigs(data_set)
        self.copy_fields(pc,pc_fields_to_copy)
        if viz_w_error:
            self.loss_function = loss_function.LossFunctionParamsMeanAbsoluteError()

        self.figsize = (10,8.9)
        self.borders = (.05,.95,.95,.05)
        self.data_set_to_use = pc.data_set
        self.title = bc.data_name_dict.get(self.data_set_to_use, 'Unknown Data Set')
        self.show_legend_on_all = show_legend_on_all
        self.x_axis_string = 'Number of labeled instances'
        self.ylims = None
        '''
        if pc.data_set == bc.DATA_SYNTHETIC_LINEAR_REGRESSION:
            self.ylims = [0,12]
        elif pc.data_set == bc.DATA_ADIENCE_ALIGNED_CNN_1:
            self.ylims = [0,1000]
        elif pc.data_set == bc.DATA_BOSTON_HOUSING:
            self.ylims = [0,100]
        elif pc.data_set == bc.DATA_CONCRETE:
            self.ylims = [0,1000]
        elif pc.data_set == bc.DATA_DROSOPHILIA:
            self.ylims = [0,3]
        '''
        self.generate_file_names(pc)

    def generate_file_names(self, pc):
        self.files = OrderedDict()
        base_file_name = 'RelReg-cvx-constraints-%s=%s'
        use_test = other_method_configs['use_test_error_for_model_selection']
        use_val = other_method_configs['use_validation']

        #self.files['Mixed-feats_QuadFeatsFew_method=HardConstraints_signs=20.pkl'] = 'Mixed: Hard Constraints, Quad Feats Few, 20 signs'
        #self.files['SKL-RidgeReg-QuadFeatsFew.pkl'] = 'SKL Ridge Regression, Quad Feats Few'
        #self.files['SLL-NW.pkl'] = 'LLGC'
        #self.files['NW.pkl'] = 'NW'


        self.files['Mixed-feats_method=Ridge.pkl'] = 'Mixed: Ridge'
        self.files['Mixed-feats_method=Rel_nonneg_l1.pkl'] = 'Mixed: Nonneg'
        self.files['Mixed-feats_method=Rel_nonneg_not-relaxed_l1.pkl'] = 'Mixed: Nonneg, not relaxed'
        self.files['Mixed-feats_method=Rel_signs=5_corr_l1.pkl'] = 'Mixed: 5 signs'
        self.files['Mixed-feats_method=Rel_signs=10_corr_l1.pkl'] = 'Mixed: 10 signs'
        self.files['Mixed-feats_method=Rel_signs=10_corr_not-relaxed_l1.pkl'] = 'Mixed: 10 signs, not relaxed'

        self.files['Mixed-feats_method=Rel_pairs=10_corr_l1.pkl'] = 'Mixed: 10 pairs'
        #self.files['Mixed-feats_method=Rel_pairs=10_corr_no-tikhonov_l1.pkl'] = 'Mixed: 10 pairs, no tikhonov'

        #self.files['SKL-DumReg.pkl'] = 'Predict Mean'

        if use_test or use_val:
            test_files = OrderedDict()
            for f, leg in self.files.iteritems():
                f = helper_functions.remove_suffix(f, '.pkl')
                if data_set_to_use == bc.DATA_DROSOPHILIA:
                    f += '_50'
                if use_test:
                    f += '-TEST.pkl'
                    leg = 'TEST: ' + leg
                else:
                    f += '-VAL.pkl'
                    leg = 'VALIDATION: ' + leg
                test_files[f] = leg
            self.files = test_files

        self.title = self.results_dir
        self.files['SKL-DumReg.pkl'] = 'Predict Mean'



viz_params = [
    {'data_set': d} for d in all_data_sets
]