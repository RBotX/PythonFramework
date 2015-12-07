from loss_functions import loss_function

DATA_NG = 1
DATA_BOSTONG_HOUSING = 2
DATA_SYNTHETIC_STEP_TRANSFER = 3
DATA_SYNTHETIC_STEP_LINEAR_TRANSFER = 4

class Configs(object):
    def __init__(self):
        pass

    def has(self,key):
        return hasattr(self,key)

    def get(self,key,default_value):
        if ~self.has(key):
            assert default_value in locals()
            return default_value
        return getattr(key)

    def stringify_fields(self,fields):
        assert False

    def copy_fields(self,other,keys):
        for k in keys:
            setattr(self,k,getattr(other,k))

    def set_uci_yeast(self):
        self.data_dir = 'data_sets/uci_yeast'
        self.data_name = 'uci_yeast'
        self.data_set_file_name = 'split_data.pkl'
        self.results_dir = 'uci_yeast'

    def set_boston_housing(self):
        self.data_dir = 'data_sets/boston_housing'
        self.data_name = 'boston_housing'
        self.data_set_file_name = 'split_data.pkl'
        self.results_dir = 'boston_housing'

    def set_ng(self):
        self.data_dir = 'data_sets/20ng'
        self.data_name = 'ng_data'
        self.data_set_file_name = 'split_data.pkl'
        self.results_dir = '20ng'

    @property
    def data_file(self):
        pc = create_project_configs()
        s = self.data_dir + '/' + self.data_set_file_name
        return s

    @property
    def results_directory(self):
        pc = create_project_configs()
        s = pc.project_dir + '/' + self.results_dir
        return s


def create_project_configs():
    return ProjectConfigs()

class ProjectConfigs(Configs):
    def __init__(self):
        self.project_dir = 'base'
        self.loss_function = loss_function.MeanSquaredError()
        self.data_dir = ''
        self.data_name = ''
        self.data_set_file_name = ''
        self.results_dir = ''
        self.include_name_in_results = False
        self.labels_to_use = None
        self.num_labels = range(40,201,40)
        #self.num_labels = range(40,81,40)
        self.set_boston_housing()
        self.num_splits = 30
        self.labels_to_keep = None
        self.labels_to_not_sample = {}


pc_fields_to_copy = ['data_dir',
                     'data_name',
                     'data_set_file_name',
                     'results_dir',
                     'include_name_in_results',
                     'labels_to_use',
                     'num_labels',
                     'num_splits',
                     'loss_function',
                     'labels_to_keep',
                     'labels_to_not_sample']

class BatchConfigs(Configs):
    def __init__(self):
        self.config_list = [MainConfigs()]

class MainConfigs(Configs):
    def __init__(self):
        pc = create_project_configs()
        self.copy_fields(pc,pc_fields_to_copy)
        self.learner = None
        self.set_ridge_regression()

    @property
    def results_file(self):
        return self.results_directory + '/' + self.learner.name_string + '.pkl'

    def set_ridge_regression(self):
        from methods import method
        self.learner = method.SKLRidgeRegression(MethodConfigs())

    def set_l2_logistic_regression(self):
        from methods import method
        self.learner = method.SKLLogisticRegression()

    def set_l2_svm(self):
        assert False

    def set_mean(self):
        from methods import method
        self.learner = method.SKLGuessClassifier()

    def set_median(self):
        assert False

    def set_nadaraya_watson(self):
        assert False


class MethodConfigs(Configs):
    def __init__(self):
        pc = create_project_configs()
        self.z_score = False
        self.quiet = False
        self.loss_function = pc.loss_function

    @property
    def results_file_name(self):
        assert False

class DataProcessingConfigs(Configs):
    def __init__(self):
        pc = create_project_configs()
        self.copy_fields(pc,pc_fields_to_copy)
        self.splits = 30
        self.is_regression = False
        self.labels_to_use = None

class VisualizationConfigs(Configs):
    def __init__(self):
        pc = create_project_configs()
        self.title = 'My Plot'
        self.copy_fields(pc,pc_fields_to_copy)
        self.axis_to_use = None
        self.show_legend = True
        self.sizes_to_use = None
        self.x_axis_field = 'num_labels'
        self.x_axis_string = 'Size'
        self.y_axis_string = 'Error'
        self.files = [
            'SKL-RidgeReg.pkl'
        ]

    @property
    def results_files(self):
        dir = self.results_directory
        files = [dir + '/' + s for s in self.files]
        return files


if __name__ == "__main__":
    c = Configs()