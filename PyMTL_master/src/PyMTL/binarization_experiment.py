#
# binarization_experiment.py
# Contains classes and methods for performing the experiment which compares
# the ERM multi-task learning (MTL) method with the attribute binarization
# techniques used when building decision trees.
#
# Copyright (C) 2013 Tadej Janez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author(s): Tadej Janez <tadej.janez@fri.uni-lj.si>
#

import logging, os.path, re, time
from collections import OrderedDict

import numpy as np
import sklearn
import Orange

from PyMTL import data, synthetic_data, test
from PyMTL.util import (logger, configure_logger, pickle_obj,
                        ignore_deprecation_warnings,
                        convert_svgs_to_pdfs, build_and_crop_tex_files)
from PyMTL.learning import prefiltering, learning, bin_exp
from PyMTL.orange_utils import (convert_numpy_data_to_orange,
                                OrangeClassifierWrapper)
from PyMTL.orange_visualizations import save_treegraph_image
from PyMTL.tikz_visualizations import draw_and_save_tikz_tree_document


def _add_id_and_merge_learn_data_orange(tasks):
    """Convert the given tasks' data to Orange format. Augment their data with
    the task id attribute, which marks the origin of each example.
    Return a tuple (learn_data_merged, test_data_with_id), where:
        learn_data_merged -- Orange.data.Table with all tasks' learning data
            merged together
        test_data_with_id -- Ordered dictionary mapping from tasks' ids to
            Orange.data.Tables corresponding to each task's testing data
    
    Arguments:
    tasks -- OrderedDictionary mapping from tasks' ids to their test.Task
        objects
    
    """
    # get the learning data of the first task
    t0_learn_data = tasks.values()[0].get_learn_data()
    # get the number of features of a task
    f = t0_learn_data[0].shape[1]
    # get the feature names of the first task or create generic names
    try:
        feat_names = tasks.values()[0].get_feature_names()
    except ValueError:
        feat_names = ["a{}".format(k) for k in range(f)]
    # create Orange feature objects
    orange_feat = []
    for k in range(f):
        if len(np.unique(t0_learn_data[0][:, k])) <= 2:
            feat = Orange.data.variable.Discrete(name=feat_names[k],
                                                 values=["0", "1"])
        else:
            feat = Orange.data.variable.Continuous(name=feat_names[k])
        orange_feat.append(feat)
    # create an Orange variable for the class attribute
    if len(np.unique(t0_learn_data[1])) <= 2:
        orange_class = Orange.data.variable.Discrete(name="cls",
                                                     values=["0", "1"])
    else:
        orange_class = Orange.data.variable.Continuous(name="cls")
    orange_domain = Orange.data.Domain(orange_feat, orange_class)
    # convert each task's data to Orange format
    orange_tasks = OrderedDict()
    for tid, task in tasks.items():
        learn_data = convert_numpy_data_to_orange(orange_domain,
                                                  *task.get_learn_data())
        test_data = convert_numpy_data_to_orange(orange_domain,
                                                 *task.get_test_data())
        orange_tasks[tid] = learn_data, test_data
    # add the task id attribute to learn and test data, merge the learn data
    # into one big table and create an OrderedDict mapping from tasks' ids to
    # their test data
    orange_id = Orange.data.variable.Discrete(name="id",
                                        values=orange_tasks.keys())
    orange_domain_id = Orange.data.Domain(orange_feat + [orange_id],
                                          orange_class)
    learn_data_merged = Orange.data.Table(orange_domain_id)
    test_data_with_id = OrderedDict()
    for tid, (learn_data, test_data) in orange_tasks.items():
        temp_learn = Orange.data.Table(orange_domain_id, learn_data)
        for ex in temp_learn:
            ex["id"] = tid
        learn_data_merged.extend(temp_learn)
        temp_test = Orange.data.Table(orange_domain_id, test_data)
        for ex in temp_test:
            ex["id"] = tid
        test_data_with_id[tid] = temp_test
    return learn_data_merged, test_data_with_id


class BinarizationExperimentMTLTester(test.PrepreparedTestSetsMTLTester):
    
    """A subclass of the PyMTL.test.PrepreparedTestSetsMTLTester class
    containing special versions of some of the methods to enable comparison
    between the standard ERM multi-task learning (MTL) method and other methods
    that add the id attribute to the input data, merge data of all tasks
    together and then use a decision tree learning method with attribute
    binarization on the merged data.
    
    """
    
    def _prepare_tasks_data(self, **kwargs):
        """In addition to calling the super class' _prepare_tasks_data()
        function, call the _add_id_and_merge_learn_data_orange() function.
        
        """
        super(BinarizationExperimentMTLTester, self)._prepare_tasks_data(
                                                        **kwargs)
        # prepare data with an added id attribute, merged together in one table
        # and converted to Orange format
        self._merged_learn_data_orange, self._test_data_orange = \
            _add_id_and_merge_learn_data_orange(self._tasks)
    
    def _save_orange_data(self, repetition, results_path):
        """Save the Orange data table stored at self._merged_learn_data_orange
        and Orange data tables stored at self._test_data_orange to the given
        results path.
        
        Arguments:
        repetition -- integer representing the repetition number of the
            binarization experiment
        results_path -- string representing the path where to save the Orange
            data tables
        
        """
        # save learn data
        learn_data_path = os.path.join(results_path, "orange_merged_learn-"
                                       "repetition{}.tab".format(repetition))
        self._merged_learn_data_orange.save(learn_data_path)
        # save test data
        for tid, test_data in self._test_data_orange.items():
            test_data_path = os.path.join(results_path, "orange_test-{}-"
                                "repetition{}.tab".format(tid, repetition))
            test_data.save(test_data_path)
    
    @ignore_deprecation_warnings
    def _test_tasks_orange(self, models, measures):
        """Test the given tasks' models on their testing data sets. Compute
        the given scoring measures of the testing results.
        Return a two-dimensional dictionary with the first key corresponding to
        the task's id and the second key corresponding to the measure's name.
        The value corresponds to the score for the given task and scoring
        measure.
        Note: If a particular scoring measure couldn't be computed for a task,
        its value is set to None.
        Note: This function works with Orange classifiers and Orange data
        tables.
        
        Arguments:
        models -- dictionary mapping from tasks' ids to their models
        measures -- list of strings representing measure's names (currently,
            only CA and AUC are supported)
        
        """
        scores = dict()
        comp_errors = {measure : 0 for measure in measures}
        for tid, task_test_data in self._test_data_orange.iteritems():
            scores[tid] = dict()
            test_res = Orange.evaluation.testing.test_on_data([models[tid]],
                                                              task_test_data)
            for measure in measures:
                if measure == "AUC":
                    try:
                        score = Orange.evaluation.scoring.AUC(test_res)[0]
                    except ValueError as e:
                        if (e.args[0] == 
                            "Cannot compute AUC on a single-class problem"):
                            # AUC cannot be computed because all instances
                            # belong to the same class
                            score = None
                            comp_errors[measure] += 1
                        else:
                            raise e
                elif measure == "CA":
                    score = Orange.evaluation.scoring.CA(test_res)[0]
                else:
                    raise ValueError("Unknown scoring measure: {}".\
                                     format(measure))
                scores[tid][measure] = score
        # report the number of errors when computing the scoring measures
        n = len(self._tasks)
        for m_name, m_errors in comp_errors.iteritems():
            if m_errors > 0:
                logger.info("Scoring measure {} could not be computed for {}"
                    " out of {} tasks ({:.1f}%)".format(m_name, m_errors, n,
                    100.*m_errors/n))
        return scores
    
    def _test_tasks(self, models, measures):
        """If the given models are scikit-learn estimators, call the super
        class' _test_tasks() function.
        If the given models are Orange classifiers, call the custom
        _test_tasks_orange() function.
        Else, raise an error.
        
        Arguments:
        models -- dictionary mapping from tasks' ids to their models
        measures -- list of strings representing measure's names (currently,
            only CA and AUC are supported)
        
        """
        model0 = models.values()[0]
        # if the tasks' models are scikit-learn estimators, use the super class'
        # _test_tasks() function
        if isinstance(model0, sklearn.base.BaseEstimator):
            return super(BinarizationExperimentMTLTester, self)._test_tasks(
                    models, measures)
        # if the tasks' models are Orange classifiers, use the custom
        # _test_tasks_orange() function
        elif isinstance(model0, Orange.core.Classifier):
            return self._test_tasks_orange(models, measures)
        else:
            raise ValueError("Unsupported model type: {}".format(type(model0)))
    
    def test_tasks(self, learners, base_learners, measures, results_path,
                   save_orange_data=False):
        """Repeat the following experiment self._repeats times:
        Prepare tasks' data with the _prepare_tasks_data() function.
        Test the performance of the given learning algorithms with the given
        base learning algorithms and compute the testing results using the
        given scoring measures.
        Process the obtained repetition scores with the
        _process_repetition_scores() function.
        Note: This function only test some specific combinations of
        base_learners and learners as used by the binarization experiment.
        
        Arguments:
        learners -- ordered dictionary with items of the form (name, learner),
            where name is a string representing the learner's name and
            learner is a MTL method (e.g. ERM, NoMerging, ...) 
        base learners -- ordered dictionary with items of the form (name,
            learner), where name is a string representing the base learner's
            name and learner is a scikit-learn estimator object
        measures -- list of strings representing measure's names (currently,
            only CA and AUC are supported)
        results_path -- string representing the path where to save any extra
            information about the running of this test (currently, only used
            for pickling the results when there is an error in calling the
            learner)
        save_orange_data -- boolean indicating whether to save the Orange data
            tables created with the call to self._prepare_tasks_data() function
        
        """
        rpt_scores = OrderedDict()
        dend_info = {bl : OrderedDict() for bl in base_learners.iterkeys()}
        for i in range(self._repeats):
            self._repetition_number = i
            self._prepare_tasks_data(**self._tasks_data_params)
            if save_orange_data:
                self._save_orange_data(i, results_path)
            rpt_scores[i] = {bl : dict() for bl in base_learners.iterkeys()}
            for bl in base_learners:
                for l in learners:
                    start = time.clock()
                    try: 
                        if isinstance(learners[l],
                                      bin_exp.TreeMarkedAndMergedLearner):
                            R = learners[l](self._tasks.keys(),
                                            self._merged_learn_data_orange,
                                            base_learners[bl])
                        elif isinstance(base_learners[bl], Orange.core.Learner):
                            wrapped_bl = OrangeClassifierWrapper(
                                            orange_learner=base_learners[bl])
                            R = learners[l](self._tasks, wrapped_bl)
                        else:
                            raise ValueError("An unexpected combination of "
                                    "base_learner and leaner detected: {} and "
                                    "{}".format(type(base_learners[bl]),
                                                type(learners[l])))
                    except Exception as e:
                        logger.exception("There was an error during repetition:"
                            " {} with base learner: {} and learner: {}.".\
                            format(i, bl, l))
                        if i > 0:
                            logger.info("Saving the results of previous "
                                        "repetitions.")
                            # remove the scores of the last repetition
                            del rpt_scores[i]
                            # process the remaining repetition scores
                            self._process_repetition_scores(rpt_scores,
                                                            dend_info)
                            # pickle them to a file
                            pickle_path_fmt = os.path.join(results_path,
                                                           "bl-{}.pkl")
                            self.pickle_test_results(pickle_path_fmt)
                        # re-raise the original exception
                        import sys
                        exc_info = sys.exc_info()
                        raise exc_info[1], None, exc_info[2]
                    rpt_scores[i][bl][l] = self._test_tasks(R["task_models"],
                                                            measures)
                    end = time.clock()
                    logger.debug("Finished repetition: {}, base learner: {}, "
                        "learner: {} in {:.2f}s".format(i, bl, l, end-start))
                    # store dendrogram info if the results contain it 
                    if "dend_info" in R:
                        dend_info[bl][i] = R["dend_info"]
                    # pickle and visualize the decision tree if the learner is a
                    # (sub)class of TreeMarkedAndMergedLearner
                    if isinstance(learners[l],
                                  bin_exp.TreeMarkedAndMergedLearner):
                        tree = R["task_models"].values()[0]
                        pickle_path = os.path.join(results_path, "{}-{}-"
                                        "repeat{}.pkl".format(bl, l, i))
                        svg_path = os.path.join(results_path, "{}-{}-repeat{}"
                                                ".svg".format(bl, l, i))
                        tikz_path = os.path.join(results_path, "{}-{}-repeat{}"
                                                 "-tikz.tex".format(bl, l, i))
                        pickle_obj(tree, pickle_path)
                        save_treegraph_image(tree, svg_path)
                        draw_and_save_tikz_tree_document(tree, tikz_path)
        self._process_repetition_scores(rpt_scores, dend_info)


def combine_dendrograms_and_trees(base_learners, path):
    """Find the PDF files of ERM's dendrograms and ForcedTree's trees for the
    given base learners in the given path, and
    create a TeX file with dendrograms and trees as side-by-side figures (one
    figure for each repetition).
    
    Parameters
    ----------
    base_learners : list 
        A list of strings representing the names of base learners.
    path : string
        The path where to search for PDF files of ERM's dendrograms and
        ForcedTree's trees.
    
    """
    for bl in base_learners:
        # find the PDFs of ERM's dendrograms and ForcedTree's trees
        dends = OrderedDict()
        trees = OrderedDict()
        for e in sorted(os.listdir(path)):
            match_dend = re.search(r"^dend-" + bl + r"-repeat(\d+).pdf$", e)
            if match_dend:
                # extract the values of the parenthesized subgroup
                repeat = match_dend.group(1)
                dends[repeat] = os.path.join(path, e)
        for e in sorted(os.listdir(path)):
            match_tree = re.search(r"^" + bl + r"-ForcedTree-repeat(\d+)-"
                                   r"tikz.pdf$", e)
            if match_tree:
                # extract the values of the parenthesized subgroup
                repeat = match_tree.group(1)
                trees[repeat] = os.path.join(path, e)
        # create a TeX file with dendrograms and trees as side-by-side figures
        # (one figure for each repetition) 
        tex_file = os.path.join(path, "comparison-{}-ForcedTree_vs_dend.tex".
                                format(bl))
        with open(tex_file, "w") as out:
            out.write(r"\documentclass[12pt,a4paper]{article}"
                      "\n\n"
                      r"\usepackage[margin=0cm, landscape]{geometry}"
                      "\n"
                      r"\usepackage{graphicx}"
                      "\n\n"
                      r"\begin{document}"
                      "\n\n")
            for repeat in trees:
                out.write(r"\begin{figure}"
                          "\n"
                          r"\centering"
                          "\n"
                          r"\begin{minipage}{0.45\textwidth}"
                          "\n"
                          r"\centering"
                          "\n"
                          r"\includegraphics[width=\textwidth]{")
                out.write(dends[repeat])
                out.write("}\n"
                          r"\end{minipage}"
                          "\n"                        
                          r"\begin{minipage}{0.45\textwidth}"
                          "\n"
                          r"\centering"
                          "\n"
                          r"\includegraphics[width=\textwidth]{")
                out.write(trees[repeat])
                out.write("}\n"
                          r"\end{minipage}"
                          "\n"
                          r"\caption{Dendrogram of ERM vs. ForcedTree, ")
                out.write("repetition: {}}}\n".format(repeat))
                out.write(r"\end{figure}"
                          "\n\n")
            out.write(r"\end{document}")


def run_experiment(attributes, disjunct_degree, n, task_groups, tasks_per_group,
                   noise, data_rnd_seed, n_learning_sets, rnd_seed,
                   results_path, base_learners, measures, learners,
                   test=True, unpickle=False, visualize=True,
                   weighting="all_equal", error_margin="std",
                   error_bars=True, separate_figs=True, cfg_logger=True):
    """Run the binarization experiment according to the given parameters and
    save the results where indicated.
    
    Parameters
    ----------
    attributes : int
        Number of attributes/variables of the generated Boolean functions.
    disjunct_degree : int
        The expected number of attributes/variables in a disjunct.
    n : int
        The number of examples for each task to generate.
    task_groups : int
        The number of task groups to generate. Each task group shares the
        same Boolean function.
    tasks_per_group : int
        The number of tasks (with their corresponding data) to generate for
        each task group.
    noise : float
        The proportion of examples of each task that have their class values
        determined randomly.
    data_rnd_seed : int
        The random seed with which to initialize a private Random object.
    n_learning_sets : int
        The number of different learning sets to create for each task.
    rnd_seed : int
        The random seed to be used for the BinarizationExperimentMTLTester
        object.
    results_path : string
        The path where to store the results (if it doesn't exist, it will be
        created).
    base_learners : OrderedDict
        An ordered dictionary with items of the form (name, learner), where
        name is a string representing the base learner's name and learner is a
        scikit-learn estimator object.
    measures : list
        A list of strings representing measure's names.
    learners : OrderedDict
        An ordered dictionary with items of the form (name, learner),
        where name is a string representing the learner's name and
        learner is a merging learning algorithm (e.g. ERM, NoMerging, ...).
    test : boolean 
        Indicates whether to perform tests on the MTL problem (with the given
        base_learners, measures and learners).
    unpickle : boolean
        Indicates whether to search for previously computed testing results and
        include them in the MTL problem.
    visualize : boolean
        Indicates whether to visualize the results of the current tasks (for
        each combination of base learners, measures and learners of the MTL
        problem).
    weighting : string
        Indicator of the type of weighting to use when computing the overall
        results.
    error_margin : string
        The measure to use for error margins when computing the overall results.
    error_bars : boolean
        Indicates whether to plot the error bars when visualizing the results.
    separate_figs : boolean
        Indicates whether to plot the results of each base learner as a separate
        figure or as one combined figure
    cfg_logger : boolean
        Indicates whether to re-configure the global logger object.
    
    """
    if not os.path.exists(results_path):
        os.makedirs(results_path)
    if cfg_logger:
        log_file = os.path.join(results_path,
                            "run-{}.log".format(time.strftime("%Y%m%d_%H%M%S")))
        configure_logger(logger, console_level=logging.INFO, file_name=log_file)
    pickle_path_fmt = os.path.join(results_path, "bl-{}.pkl")
    # generate boolean data with complete test sets
    funcs_pickle_path = os.path.join(results_path, "boolean_funcs.pkl")
    tasks_data, tasks_complete_test_sets = \
        synthetic_data.generate_boolean_data_with_complete_test_sets(
            attributes, disjunct_degree, n, task_groups, tasks_per_group,
            noise, random_seed=data_rnd_seed, n_learning_sets=n_learning_sets,
            funcs_pickle_path=funcs_pickle_path)
    # create a MTL tester with tasks' data
    mtlt = BinarizationExperimentMTLTester(tasks_data, rnd_seed, repeats=1,
            preprepared_test_sets=tasks_complete_test_sets)
    # test all combinations of learners and base learners (compute the testing
    # results with the defined measures) and save the results if test == True
    if test:
        mtlt.test_tasks(learners, base_learners, measures, results_path,
                        save_orange_data=True)
        mtlt.pickle_test_results(pickle_path_fmt)
    # find previously computed testing results and check if they were computed
    # using the same data tables and cross-validation indices if
    # unpickle == True
    if unpickle:
        mtlt.find_pickled_test_results(pickle_path_fmt)
        if not mtlt.check_test_results_compatible():
            raise ValueError("Test results for different base learners are not "
                             "compatible.")
    # visualize the results of the current tasks for each combination of base
    # learners, learners and measures that are in the MTL problem; in addition,
    # visualize the dendrograms showing merging history of ERM
    if visualize:
        if not mtlt.contains_test_results():
            raise ValueError("The MTLTester object doesn't contain any testing"
                             " results.")
        bls = mtlt.get_base_learners()
        ls = mtlt.get_learners()
        ms = mtlt.get_measures()
        mtlt.visualize_results(bls, ls, ms, results_path,
            {"ForcedTree": "blue", "Tree": "green", "ERM": "red"},
            error_bars=error_bars, separate_figs=separate_figs)
        mtlt.visualize_dendrograms(bls, results_path)
        mtlt.compute_overall_results(bls, ls, ms, results_path,
                weighting=weighting, error_margin=error_margin)
        convert_svgs_to_pdfs(results_path)
        build_and_crop_tex_files(results_path, r"-tikz.tex$")
        combine_dendrograms_and_trees(bls, results_path)
        build_and_crop_tex_files(results_path, r"^comparison.*.tex$",
                                 crop=False)


if __name__ == "__main__":
    # initialize Qt application
    # NOTE: Needed by the save_treegraph_image() function.
    import sys
    from OWWidget import QApplication
    a = QApplication(sys.argv)
    
    # find out the current file's location so it can be used to compute the
    # location of other files/directories
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    path_prefix = os.path.abspath(os.path.join(cur_dir, "../../"))
    
    base_learners = OrderedDict()
    import Orange.classification.tree as octree
    import Orange.feature.scoring as fscoring
    split_const = octree.SplitConstructor_ExhaustiveBinary(measure=
                                                           fscoring.InfoGain())
    base_learners["orange_tree"] = octree.TreeLearner(split=split_const,
        store_instances=True)
    base_learners["orange_tree_pruned"] = octree.TreeLearner(split=split_const,
        min_instances=10, same_majority_pruning=True, store_instances=True)
    
    measures = []
    measures.append("CA")
    measures.append("AUC")
    
    learners = OrderedDict()
    learners["Tree"] = bin_exp.TreeMarkedAndMergedLearner()
    learners["ForcedTree"] = bin_exp.ForcedFirstSplitMTLLearner(
                                        first_split_attr="id")
    no_filter = prefiltering.NoFilter()
    learners["ERM"] = learning.ERMLearner(folds=5, seed=33, prefilter=no_filter,
                                          error_func=None)
    
    # boolean indicating whether to perform the tests on the MTL problem
    test = True
    # boolean indicating whether to find previously computed testing results
    # and unpickling them
    unpickle = False
    # boolean indicating whether to visualize the results of the MTL problem
    visualize = True
    
    test_config = 1
    
    if test_config == 1:
        # parameters of the synthetic Boolean MTL problem
        attributes = 8
        disjunct_degree = 4
        n = 100
        task_groups = 2
        tasks_per_group = 5
        noise = 0.0
        data_rnd_seed = 14
        n_learning_sets = 3
        # parameters for the MTL problem tester
        rnd_seed = 63
        results_path = os.path.join(path_prefix, "results/binarization_"
            "experiment/bool_func-a{}d{}n{}g{}tg{}nse{}rs{}nls{}-seed{}-"
            "complete_test".\
            format(attributes, disjunct_degree, n, task_groups, tasks_per_group,
                   noise, data_rnd_seed, n_learning_sets, rnd_seed))
        run_experiment(attributes, disjunct_degree, n, task_groups,
            tasks_per_group, noise, data_rnd_seed, n_learning_sets, rnd_seed,
            results_path, base_learners, measures, learners,
            test, unpickle, visualize)
    
    if test_config == 2:
        # static parameters of the synthetic Boolean MTL problem
        attributes = 8
        disjunct_degree = 4
        n = 100
        task_groups = 2
        tasks_per_group = 5
        n_learning_sets = 10
        # parameters for the MTL problem tester
        rnd_seed = 63
        # dynamic parameters of the synthetic Boolean MTL problem
        noise_values = [0.0, 0.1, 0.2, 0.3, 0.5]
        data_rnd_seed_values = range(15, 25)
        # remove the non-pruning orange tree learner
        if "orange_tree" in base_learners:
            del base_learners["orange_tree"]
        for noise in noise_values:
            for data_rnd_seed in data_rnd_seed_values:
                results_path = os.path.join(path_prefix, "results/binarization_"
                    "experiment/bool_func-a{}d{}n{}g{}tg{}nse{}rs{}nls{}-seed{}"
                    "-complete_test".\
                    format(attributes, disjunct_degree, n, task_groups,
                    tasks_per_group, noise, data_rnd_seed, n_learning_sets,
                    rnd_seed))
                run_experiment(attributes, disjunct_degree, n, task_groups,
                    tasks_per_group, noise, data_rnd_seed, n_learning_sets,
                    rnd_seed, results_path, base_learners, measures, learners,
                    test, unpickle, visualize)
    
    if test_config == 3:
        # parameters of the synthetic Boolean MTL problem
        attributes = 16
        disjunct_degree = 8
        n = 100
        task_groups = 2
        tasks_per_group = 5
        noise = 0.0
        data_rnd_seed = 16
        n_learning_sets = 3
        # parameters for the MTL problem tester
        rnd_seed = 63
        results_path = os.path.join(path_prefix, "results/binarization_"
            "experiment/bool_func-a{}d{}n{}g{}tg{}nse{}rs{}nls{}-seed{}-"
            "complete_test".\
            format(attributes, disjunct_degree, n, task_groups, tasks_per_group,
                   noise, data_rnd_seed, n_learning_sets, rnd_seed))
        run_experiment(attributes, disjunct_degree, n, task_groups,
            tasks_per_group, noise, data_rnd_seed, n_learning_sets, rnd_seed,
            results_path, base_learners, measures, learners,
            test, unpickle, visualize)
    
    if test_config == 4:
        # parameters of the synthetic Boolean MTL problem
        attributes = 12
        disjunct_degree = 6
        n = 200
        task_groups = 2
        tasks_per_group = 5
        noise = 0.0
        data_rnd_seed = 16
        # parameters for the MTL problem tester
        rnd_seed = 63
        results_path = os.path.join(path_prefix, "results/binarization_"
            "experiment/bool_func-a{}d{}n{}g{}tg{}nse{}rs{}nls{}-seed{}-"
            "complete_test".\
            format(attributes, disjunct_degree, n, task_groups, tasks_per_group,
                   noise, data_rnd_seed, n_learning_sets, rnd_seed))
        run_experiment(attributes, disjunct_degree, n, task_groups,
            tasks_per_group, noise, data_rnd_seed, n_learning_sets, rnd_seed,
            results_path, base_learners, measures, learners,
            test, unpickle, visualize)
