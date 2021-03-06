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
import numpy as np

# Command line arguments for ProjectConfigs
arguments = None

def create_project_configs():
    return ProjectConfigs()

pc_fields_to_copy = bc.pc_fields_to_copy + [
    'disable_relaxed_guidance',
    'disable_tikhonov',
    'random_guidance',
    'use_training_corr',
    'use_transfer',
    'target_labels',
    'source_labels',
    'use_oracle'
]
data_set_to_use = bc.DATA_SYNTHETIC_LINEAR_REGRESSION_10
#data_set_to_use = bc.DATA_DROSOPHILIA
#data_set_to_use = bc.DATA_BOSTON_HOUSING
#data_set_to_use = bc.DATA_WINE_RED
#data_set_to_use = bc.DATA_CONCRETE
#data_set_to_use = bc.DATA_KC_HOUSING
#data_set_to_use = bc.DATA_DS2

viz_for_paper = False

run_experiments = False
run_batch_experiments = True
run_transfer_experiments = False

use_ridge = False
use_mean = False
use_quad_feats = False
run_alt_guidance_exps = True
mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
#mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_HARD_CONSTRAINT
#mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RIDGE
viz_w_error = False

VIZ_EXPERIMENT = 0
VIZ_PAPER_ERROR = 1
VIZ_PAPER_SIGNS = 2
VIZ_PAPER_RELATIVE = 3
VIZ_PAPER_TRAINING_CORR = 4
VIZ_PAPER_TRANSFER = 5
VIZ_PAPER_TRAINING_SINGLE = 6
VIZ_PAPER_HARD_CONSTRAINTS = 7
VIZ_DUAL = 8
VIZ_SAME_SIGN = 9

VIZ_PAPER_TABLE = 10
VIZ_PAPER_TABLE_TRANSFER = 11
VIZ_PAPER_TABLE_TRAINING_CORR = 12
VIZ_PAPER_TABLE_HARD_CONSTRAINTS = 13

viz_type = VIZ_PAPER_TRANSFER

if viz_type in {VIZ_PAPER_TRANSFER, VIZ_PAPER_TABLE_TRANSFER}:
    run_transfer_experiments = True

show_legend_on_all = False

max_rows = 1

if max_rows == 1:
    figsize = (18, 5)
    borders = (.05, .98, .95, .08)
    if run_transfer_experiments:
        figsize = (10, 5)
        borders = (.08, .98, .95, .08)
    if viz_type == VIZ_PAPER_TRAINING_SINGLE:
        figsize = (4, 3)
        borders = (.15, .9, .9, .15)

else:
    figsize = (10, 8.9)
    borders = (.05, .95, .95, .05)

all_data_sets = [data_set_to_use]
if run_batch_experiments:
    all_data_sets = [
        bc.DATA_SYNTHETIC_LINEAR_REGRESSION_10,
        bc.DATA_BOSTON_HOUSING,
        bc.DATA_WINE_RED,
        bc.DATA_CONCRETE,
        bc.DATA_KC_HOUSING,
        bc.DATA_DS2,
        #bc.DATA_PROSTATE,
        bc.DATA_HEART,
    ]
    if run_transfer_experiments:
        all_data_sets = [
            bc.DATA_BOSTON_HOUSING,
            bc.DATA_CONCRETE,
            bc.DATA_WINE,
        ]
    if viz_type == VIZ_PAPER_TRAINING_SINGLE:
        all_data_sets = [bc.DATA_SYNTHETIC_LINEAR_REGRESSION_10]


other_pc_configs = {
}

other_method_configs = {
    'num_random_pairs': 0,
    'num_random_signs': 1,
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
    'use_perfect_feature_selection': True,
    'mean_b': False,
    'solve_scipy': False,
    'solve_dual': False,
    'use_pairwise_same_signs': False,
    'use_hinge_primal': False,
    'fix_C2': False,
    'fix_C3': False,
}

if data_set_to_use == bc.DATA_DROSOPHILIA:
    other_method_configs['num_features'] = 50


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
        self.random_guidance = False
        self.use_transfer = run_transfer_experiments
        self.use_oracle = False
        if use_arguments and arguments is not None:
            apply_arguments(self)

        for key, value in other_method_configs.items():
            setattr(self, key, value)


    def set_data_set(self, data_set):
        self.data_set = data_set
        if run_transfer_experiments:
            if data_set == bc.DATA_BOSTON_HOUSING:
                self.set_data_set_defaults('boston_housing-13(transfer)')
                self.target_labels = np.asarray([0])
                self.source_labels = np.asarray([1])
                self.num_labels = [5, 10, 20]
            elif data_set == bc.DATA_WINE:
                self.set_data_set_defaults('wine-small-11')
                self.num_labels = [5, 10, 20]
                self.target_labels = np.asarray([0])
                self.source_labels = np.asarray([1])
            elif data_set == bc.DATA_CONCRETE:
                self.set_data_set_defaults('concrete-7')
                self.target_labels = np.asarray([1])
                self.source_labels = np.asarray([3])
                self.num_labels = [5, 10, 20]
            else:
                print 'Nnknown transfer data set!  May cause errors.'
        else:
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
            elif data_set == bc.DATA_DS2:
                self.set_data_set_defaults('DS2-processed')
                self.num_labels = [10, 20, 40]
            elif data_set == bc.DATA_PROSTATE:
                self.set_data_set_defaults('prostate')
                self.num_labels = [10, 20, 40]
            elif data_set == bc.DATA_HEART:
                self.set_data_set_defaults('heart')
                self.num_labels = [5, 10, 20, 40]
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

        method_configs.solve_scipy = pc.solve_scipy
        method_configs.solve_dual = pc.solve_dual
        method_configs.use_pairwise_same_signs = pc.use_pairwise_same_signs
        method_configs.use_hinge_primal = pc.use_hinge_primal
        method_configs.mean_b = pc.mean_b
        method_configs.fix_C2 = pc.fix_C2
        method_configs.fix_C3 = pc.fix_C3

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
            if run_transfer_experiments:
                for data_set in all_data_sets:
                    pc = ProjectConfigs(data_set)

                    p = deepcopy(pc)
                    p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
                    p.num_random_pairs = 0
                    p.num_random_signs = 1
                    self.config_list.append(MainConfigs(p))

                    p = deepcopy(pc)
                    p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
                    p.num_random_pairs = 0
                    p.num_random_signs = 1
                    p.use_transfer = False
                    self.config_list.append(MainConfigs(p))

                    p = deepcopy(pc)
                    p.disable_relaxed_guidance = False
                    p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RIDGE
                    self.config_list.append(MainConfigs(p))

                    p = deepcopy(pc)
                    p.disable_relaxed_guidance = False
                    p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_LASSO
                    self.config_list.append(MainConfigs(p))
            else:
                for data_set in all_data_sets:
                    pc = ProjectConfigs(data_set)

                    num_signs = [.25, .5, 1]
                    for i in num_signs:
                        p = deepcopy(pc)
                        p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
                        p.num_random_pairs = 0
                        p.num_random_signs = i
                        self.config_list.append(MainConfigs(p))

                    p = deepcopy(pc)
                    p.use_oracle = True
                    p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
                    p.num_random_pairs = 0
                    p.num_random_signs = 1
                    self.config_list.append(MainConfigs(p))

                    p = deepcopy(pc)
                    p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
                    p.num_random_pairs = 0
                    p.num_random_signs = 1
                    p.use_training_corr = True
                    self.config_list.append(MainConfigs(p))

                    p = deepcopy(pc)
                    p.disable_relaxed_guidance = True
                    p.num_random_signs = 1
                    self.config_list.append(MainConfigs(p))

                    num_pairs = num_signs
                    for i in num_pairs:
                        p = deepcopy(pc)
                        p.disable_relaxed_guidance = False
                        p.num_random_signs = 0
                        p.num_random_pairs = i
                        self.config_list.append(MainConfigs(p))

                    p = deepcopy(p)
                    p.disable_relaxed_guidance = False
                    p.num_random_signs = 0
                    p.num_random_pairs = 0
                    m = MainConfigs(p)
                    m.learner.use_nonneg = True
                    m.learner.use_corr = False
                    self.config_list.append(m)

                    p = deepcopy(pc)
                    p.disable_relaxed_guidance = True
                    p.num_random_signs = 0
                    p.num_random_pairs = 0
                    m = MainConfigs(p)
                    m.learner.use_nonneg = True
                    m.learner.use_corr = False
                    self.config_list.append(m)

                    p = deepcopy(pc)
                    p.disable_relaxed_guidance = False
                    p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RIDGE
                    self.config_list.append(MainConfigs(p))

                    p = deepcopy(pc)
                    p.disable_relaxed_guidance = False
                    p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_LASSO
                    self.config_list.append(MainConfigs(p))

                    if not run_alt_guidance_exps:
                        continue
                    #Dual and Primal Mean B exps
                    '''
                    p = deepcopy(pc)
                    p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
                    p.num_random_pairs = 0
                    p.num_random_signs = 1
                    p.solve_dual = True
                    p.mean_b = False
                    self.config_list.append(MainConfigs(p))

                    p = deepcopy(pc)
                    p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
                    p.num_random_pairs = 0
                    p.num_random_signs = 1
                    p.solve_dual = False
                    p.mean_b = False
                    self.config_list.append(MainConfigs(p))
                    '''
                    #Dual same sign exps
                    v = [.25, .5, 1, 2]
                    #v = [1, .5, .25]
                    v = [1]
                    for i in v:
                        p = deepcopy(pc)
                        p.mixed_feature_method = mixed_feature_guidance.MixedFeatureGuidanceMethod.METHOD_RELATIVE
                        p.num_random_pairs = i
                        p.num_random_signs = 0
                        p.solve_dual = False
                        p.mean_b = True
                        p.solve_scipy = True
                        p.use_pairwise_same_signs = True
                        p.use_hinge_primal = True
                        p.fix_C2 = False
                        p.fix_C3 = True
                        self.config_list.append(MainConfigs(p))
                    #assert False, 'Not Implemented Yet'

class VisualizationConfigs(bc.VisualizationConfigs):
    def __init__(self, data_set=None, **kwargs):
        super(VisualizationConfigs, self).__init__(data_set, **kwargs)
        self.max_rows = max_rows
        pc = ProjectConfigs(data_set)
        self.copy_fields(pc,pc_fields_to_copy)
        if viz_w_error:
            self.loss_function = loss_function.LossFunctionParamsMeanAbsoluteError()

        self.figsize = figsize
        self.borders = borders
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


        if viz_type == VIZ_SAME_SIGN:
            self.files['Mixed-feats_method=Ridge.pkl'] = 'Ridge'
            self.files['Mixed-feats_method=Rel_meanB-pairsSameSignPrimalHinge=1-use_sign_corr_l1.pkl'] = 'Our Method: 100% pairwise signs'
        elif viz_type == VIZ_DUAL:
            self.files['Mixed-feats_method=Ridge.pkl'] = 'Ridge'
            #self.files['Mixed-feats_method=Rel_meanB_signs=1-use_sign_corr_l1.pkl'] = 'Primal: Signs, meanB'
            ##self.files['Mixed-feats_method=Rel_dual_meanB_signs=1-use_sign_corr_l1.pkl'] = 'Dual: Signs, meanB'
            self.files['Mixed-feats_method=Rel_dual_signs=1-use_sign_corr_l1.pkl'] = 'Dual: Signs'
            #self.files['Mixed-feats_method=Rel_meanB_pairsSameSignPrimal=0.25-use_sign_corr_l1.pkl'] = 'Same Sign Primal: meanB, 25% pairs'
            #self.files['Mixed-feats_method=Rel_meanB_pairsSameSignPrimal=0.5-use_sign_corr_l1.pkl'] = 'Same Sign Primal: meanB, 50% pairs'
            #self.files['Mixed-feats_method=Rel_meanB_pairsSameSignPrimal=1-use_sign_corr_l1.pkl'] = 'Same Sign Primal: meanB, 100% pairs'
            #self.files['Mixed-feats_method=Rel_meanB_pairsSameSignPrimal=2-use_sign_corr_l1.pkl'] = 'Same Sign Primal: meanB, 200% pairs'
            #self.files['Mixed-feats_method=Rel_meanB-pairsSameSignQCQP=1-use_sign_corr_l1.pkl'] =  'Same sign QCQP'
            self.files['Mixed-feats_method=Rel_meanB-pairsSameSignPrimalHinge=1-use_sign_corr_l1.pkl'] = 'Same Sign Hinge'
            self.files['Mixed-feats_method=Rel_meanB-pairsSameSignPrimalHinge=1-use_sign_corr_l1_fixC3'] = 'Same Sign Hinge: Fix C2'
        elif viz_type == VIZ_EXPERIMENT:
            self.files['Mixed-feats_method=Ridge.pkl'] = 'Mixed: Ridge'
            self.files['Mixed-feats_method=Lasso.pkl'] = 'Mixed: Lasso'
            '''
            self.files['Mixed-feats_method=Rel_nonneg_l1.pkl'] = 'Mixed: Nonneg'
            self.files['Mixed-feats_method=Rel_nonneg_not-relaxed_l1.pkl'] = 'Mixed: Nonneg, not relaxed'
            '''
            self.files['Mixed-feats_method=Rel_signs=0.25-use_sign_corr_l1.pkl'] = 'Mixed: 25% signs'
            self.files['Mixed-feats_method=Rel_signs=0.5-use_sign_corr_l1.pkl'] = 'Mixed: 50% signs'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1.pkl'] = 'Mixed: 100% signs'
            '''
            self.files['Mixed-feats_method=Rel_pairs=0.25-use_sign_corr_l1.pkl'] = 'Mixed: 25% pairs'
            self.files['Mixed-feats_method=Rel_pairs=0.5-use_sign_corr_l1.pkl'] = 'Mixed: 50% pairs'
            self.files['Mixed-feats_method=Rel_pairs=1-use_sign_corr_l1.pkl'] = 'Mixed: 100% pairs'
            '''
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_trainCorr_l1.pkl'] = 'Mixed: 100% signs, train correlation'
        elif viz_type == VIZ_PAPER_ERROR:
            self.files['Mixed-feats_method=Rel-use_sign_nonneg_not-relaxed_l1.pkl'] = 'Nonnegative'
            self.files['Mixed-feats_method=Ridge.pkl'] = 'Ridge'
            self.files['Mixed-feats_method=Lasso.pkl'] = 'Lasso'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1.pkl'] = 'PSCR: $p$ signs'
            self.files['Mixed-feats_method=Rel_pairs=1-use_sign_corr_l1.pkl'] = 'PRCR: $p$ pairs'
            self.files['Mixed-feats_method=Rel_meanB-pairsSameSignPrimalHinge=1-use_sign_corr_l1.pkl'] = 'PPSCR: $p$ sign pairs'
        elif viz_type == VIZ_PAPER_SIGNS:
            self.files['Mixed-feats_method=Rel_signs=0.25-use_sign_corr_l1.pkl'] = 'PSCR: $.25p$ signs'
            self.files['Mixed-feats_method=Rel_signs=0.5-use_sign_corr_l1.pkl'] = 'PSCR: $.5p$ signs'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1.pkl'] = 'PSCR: $p$ signs'
        elif viz_type == VIZ_PAPER_RELATIVE:
            self.files['Mixed-feats_method=Rel_pairs=0.25-use_sign_corr_l1.pkl'] = 'PRCR: $.25p$ pairs'
            self.files['Mixed-feats_method=Rel_pairs=0.5-use_sign_corr_l1.pkl'] = 'PRCR: $.5p$ pairs'
            self.files['Mixed-feats_method=Rel_pairs=1-use_sign_corr_l1.pkl'] = 'PRCR: $p$ pairs'
        elif viz_type == VIZ_PAPER_TRAINING_CORR:
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1.pkl'] = 'PSCR: $p$ signs'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_trainCorr_l1.pkl'] = 'PSCR: $p$ signs, Training Guidance'
        elif viz_type == VIZ_PAPER_TRANSFER:
            self.files['Mixed-feats_method=Ridge_transfer'] = 'Ridge: Transfer'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1.pkl'] = 'PSCR: $p$ signs'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1_transfer.pkl'] = 'Transfer PSCR: $p$ signs'
        elif viz_type == VIZ_PAPER_TRAINING_SINGLE:
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1.pkl'] = 'With Outside Guidance'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_trainCorr_l1.pkl'] = 'Without Outside Guidance'
        elif viz_type == VIZ_PAPER_HARD_CONSTRAINTS:
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1.pkl'] = 'PSCR: $p$ signs'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_not-relaxed_l1.pkl'] = 'Signed Ridge: $p$'
        elif viz_type == VIZ_PAPER_TABLE:
            self.vis_table = True
            self.data_names_for_table = [
                'Synthetic', 'BH', 'Wine', 'Concrete', 'Housing', 'ITS', 'Heart'
            ]
            self.method_names_for_table = [
                'Nonnegative', 'Ridge', 'Lasso', 'PSCR: $p$ Signs', 'PRCR: $p$ Pairs', 'PPSCR: $p$ pairs'
            ]
            self.files = OrderedDict()

            self.files['Mixed-feats_method=Rel-use_sign_nonneg_not-relaxed_l1.pkl'] = 'Nonnegative'
            self.files['Mixed-feats_method=Ridge.pkl'] = 'Ridge'
            self.files['Mixed-feats_method=Lasso.pkl'] = 'Lasso'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1.pkl'] = 'Our Method: 100% signs'
            self.files['Mixed-feats_method=Rel_pairs=1-use_sign_corr_l1.pkl'] = 'Our Method: 100% pairs'
            self.files['Mixed-feats_method=Rel_meanB-pairsSameSignPrimalHinge=1-use_sign_corr_l1.pkl'] = 'Our Method: 100% pairwise signs'
        elif viz_type == VIZ_PAPER_TABLE_TRANSFER:
            self.vis_table = True
            self.data_names_for_table = [
                'Synthetic', 'BH', 'Wine', 'Concrete', 'Housing', 'ITS', 'Heart'
            ]
            self.method_names_for_table = [
                'Ridge', 'Lasso', 'Transfer Ridge', 'PSCR: $p$ Signs', 'Transfer PSCR: $p$ Signs'
            ]
            self.files['Mixed-feats_method=Ridge.pkl'] = 'Ridge'
            self.files['Mixed-feats_method=Lasso.pkl'] = 'Lasso'
            self.files['Mixed-feats_method=Ridge_transfer'] = 'Ridge: Transfer'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1.pkl'] = 'Our Method'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1_transfer.pkl'] = 'Our Method: Transfer'
        elif viz_type == VIZ_PAPER_TABLE_TRAINING_CORR:
            self.vis_table = True
            self.data_names_for_table = [
                'Synthetic', 'BH', 'Wine', 'Concrete', 'Housing', 'ITS', 'Heart'
            ]
            self.method_names_for_table = [
                'PSCR: $p$ Signs', 'PSCR: Training Set Guidance, $p$ Signs'
            ]
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1.pkl'] = 'Our Method'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_trainCorr_l1.pkl'] = 'Our Method: Training Set Signs'
        elif viz_type == VIZ_PAPER_TABLE_HARD_CONSTRAINTS:
            self.vis_table = True
            self.data_names_for_table = [
                'Synthetic', 'BH', 'Wine', 'Concrete', 'Housing', 'ITS', 'Heart'
            ]
            self.method_names_for_table = [
                'PSCR: $p$ Signs', 'Signed Ridge'
            ]
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_l1.pkl'] = 'Our Method: 100% signs'
            self.files['Mixed-feats_method=Rel_signs=1-use_sign_corr_not-relaxed_l1.pkl'] = 'Signed Ridge'


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
                    #leg = 'VALIDATION: ' + leg
                test_files[f] = leg
            self.files = test_files

        self.title = self.results_dir
        if viz_type > VIZ_EXPERIMENT:
            self.title = bc.data_name_dict[pc.data_set]
        #self.files['SKL-DumReg.pkl'] = 'Predict Mean'



viz_params = [
    {'data_set': d} for d in all_data_sets
]
