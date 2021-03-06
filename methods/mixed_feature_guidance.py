import numpy as np
from numpy.linalg import norm, inv, eig
import cvxpy as cvx
from utility import cvx_functions
import method
import scipy
from utility import array_functions
from utility.array_functions import relative_error
from configs.base_configs import MethodConfigs
from results_class.results import Output
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn import linear_model
import logistic_difference_optimize
import scipy.optimize as optimize
from utility.capturing import Capturing
from copy import deepcopy
import preprocessing
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.linear_model import Lasso
from qcqp import *

class optimize_data(object):
    def __init__(self, x, y, reg_ridge, reg_a, reg_mixed):
        self.x = x
        self.y = y
        self.reg_ridge = reg_ridge
        self.reg_a = reg_a
        self.reg_mixed = reg_mixed

    def get_xy(self):
        return self.x, self.y

    def get_reg(self):
        return self.reg_ridge, self.reg_a, self.reg_mixed


def compute_quad_matrices(alpha, opt_data):
    assert False, 'Using different E - update this!'
    E = opt_data['E']
    x = opt_data['x']
    y = opt_data['y']
    n = opt_data['n']
    p = opt_data['p']
    C = opt_data['C']
    D_alpha = np.diag(alpha)
    F = D_alpha.T.dot(E)
    A = 2 * C * np.eye(p) - F - F.T
    try:
        A_inv = inv(A)
    except:
        try:
            A_inv = inv(A + 1e-3 * np.eye(A.shape[0]))
        except:
            A_inv = np.eye(A.shape[0])
    B = A_inv.dot(x.T)
    V = .5 * n * np.eye(n) - 2 * C * B.T.dot(B) + 2 * B.T.dot(F).dot(B)
    try:
        V_inv = inv(V)
    except:
        try:
            V_inv = inv(V + 1e-3*np.eye(V.shape[0]))
        except:
            V_inv = np.eye(V.shape[0])
    delta = V_inv.dot(y)
    return A_inv, B, F, delta

def eval_quad(alpha, opt_data):
    C = opt_data['C']
    y_dual = opt_data['y']
    if not opt_data['use_pairwise_same_signs']:
        M = opt_data['M']
        B = opt_data['B']
        Q = opt_data['Q']
        dual_objective = (.25 / C) * alpha.T.dot(Q).dot(alpha) + y_dual.T.dot(M).dot(B).dot(alpha)
    else:
        n = opt_data['n']
        x = opt_data['x']
        A_inv, B, F, delta = compute_quad_matrices(alpha, opt_data)
        dual_objective = -.25*n*norm(delta)**2 + C*norm(B.dot(delta))**2 - delta.T.dot(x).dot(B).dot(delta) \
                         + delta.dot(y_dual) - delta.T.dot(B.T).dot(F).dot(B).dot(delta)
    return dual_objective


def eval_same_sign_primal(w, opt_data):
    assert False, 'Using different E - update this!'
    x = opt_data['x']
    y = opt_data['y']
    E = opt_data['E']
    C = opt_data['C']
    C2 = opt_data['C2']
    if np.isinf(C2):
        return 0
    loss = (norm(x.dot(w) - y)**2).mean()
    reg1 = C*norm(w)**2
    reg2 = C2*w.T.dot(E).dot(w)
    return loss + reg1 - reg2

def grad_same_sign_primal(w, opt_data):
    assert False, 'Using different E - update this!'
    x = opt_data['x']
    y = opt_data['y']
    E = opt_data['E']
    C = opt_data['C']
    C2 = opt_data['C2']
    if np.isinf(C2):
        return np.zeros(w.shape)
    n = opt_data['n']
    loss_grad = (2.0/n)*x.T.dot(x.dot(w)) - 2*x.T.dot(y)
    reg1_grad = 2*C*w
    reg2_grad = C2*(E.dot(w) + E.T.dot(w))
    return loss_grad + reg1_grad - reg2_grad


def unpack_same_sign_hinge_primal(v, opt_data):
    p = opt_data['p']
    w = v[:p]
    z = v[p:]
    return w, z

def pack_same_sign_hinge_primal(w, z, opt_data):
    return np.concatenate((w, z))

def eval_same_sign_hinge_primal(v, opt_data):
    n = opt_data['n']
    x = opt_data['x']
    y = opt_data['y']
    E = opt_data['E']
    C = opt_data['C']
    C2 = opt_data['C2']
    C3 = opt_data['C3']

    w, z = unpack_same_sign_hinge_primal(v, opt_data)
    loss = (1.0/n)*norm(x.dot(w) - y)**2
    reg1 = C*norm(w)**2
    reg2 = C2*z.sum()
    loss_guidance = 0
    for idx, ei in enumerate(E):
        #w_ei = ei*w
        i,j = ei.nonzero()[0]
        s = ei[i]
        l = s*w[i]*w[j]
        l += z[idx]
        loss_guidance += max(-l, 0)
    loss_guidance *= C3
    return loss + loss_guidance + reg1 + reg2

class MixedFeatureGuidanceMethod(method.Method):
    METHOD_RELATIVE = 1
    METHOD_HARD_CONSTRAINT = 2
    METHOD_RIDGE = 10
    METHOD_ORACLE = 11
    METHOD_ORACLE_SPARSITY = 12
    METHOD_LASSO = 13
    '''
    METHODS_UNIFORM_C = {
        METHOD_NO_RELATIVE, METHOD_ORACLE_SPARSITY
    }
    '''
    METHODS_UNIFORM_C = {}
    METHODS_NO_C2 = {
        METHOD_RIDGE, METHOD_ORACLE, METHOD_HARD_CONSTRAINT, METHOD_LASSO
    }
    METHODS_NO_C3 = {
        METHOD_RELATIVE, METHOD_RIDGE, METHOD_ORACLE, METHOD_ORACLE_SPARSITY, METHOD_HARD_CONSTRAINT, METHOD_LASSO
    }
    METHODS_USES_PAIRS = {
        METHOD_RELATIVE, METHOD_HARD_CONSTRAINT
    }
    METHODS_USES_SIGNS = {
        METHOD_RELATIVE, METHOD_HARD_CONSTRAINT
    }
    def __init__(self,configs=MethodConfigs()):
        super(MixedFeatureGuidanceMethod, self).__init__(configs)
        #self.cv_params['C'] = self.create_cv_params(-5, 5, append_zero=True)
        self.cv_params['C'] = self.create_cv_params(-5, 5, append_zero=False)
        #self.cv_params['C2'] = self.create_cv_params(-8, 8, append_zero=True, prepend_inf=True)
        self.cv_params['C2'] = self.create_cv_params(-8, 8, append_zero=True, prepend_inf=False)
        #self.cv_params['C2'] = np.asarray([np.inf])
        self.cv_params['C3'] = self.create_cv_params(-5, 5, append_zero=True)
        self.transform = StandardScaler()
        #self.preprocessor = preprocessing.BasisQuadraticFewPreprocessor()
        if hasattr(configs, 'method'):
            self.method = configs.method
        else:
            self.method = MixedFeatureGuidanceMethod.METHOD_RELATIVE
            #self.method = MixedFeatureGuidanceMethod.METHOD_RIDGE
            #self.method = MixedFeatureGuidanceMethod.METHOD_ORACLE
            #self.method = MixedFeatureGuidanceMethod.METHOD_ORACLE_SPARSITY
        self.use_sign = getattr(configs, 'use_sign', True)
        self.use_corr = getattr(configs, 'use_corr', False)
        self.use_training_corr = getattr(configs, 'use_training_corr', False)
        self.use_oracle = getattr(configs, 'use_oracle', False)
        self.use_nonneg = getattr(configs, 'use_nonneg', False)
        self.use_stacking = getattr(configs, 'use_stacking', False)
        self.can_use_test_error_for_model_selection = True
        self.use_test_error_for_model_selection = configs.use_test_error_for_model_selection
        self.use_validation = configs.use_validation
        self.num_random_pairs = getattr(configs, 'num_random_pairs', 0)
        self.num_random_signs = getattr(configs, 'num_random_signs', 0)
        self.disable_relaxed_guidance = getattr(configs, 'disable_relaxed_guidance', False)
        self.disable_tikhonov = getattr(configs, 'disable_tikhonov', False)
        self.random_guidance = getattr(configs, 'random_guidance', False)
        self.use_transfer = getattr(configs, 'use_transfer', False)
        self.w = None
        self.b = None
        self.stacking_method = method.NadarayaWatsonMethod(configs)
        self.trained_stacked_methods = list()
        self.cvx_method = getattr(configs, 'cvx_method', 'SCS')
        self.num_features = getattr(configs, 'num_features', -1)
        self.use_l1 = getattr(configs, 'use_l1', False)
        self.solve_dual = getattr(configs, 'solve_dual', False)
        self.mean_b = getattr(configs, 'mean_b', False)
        self.solve_scipy = getattr(configs, 'solve_scipy', False)
        self.use_pairwise_same_signs = getattr(configs, 'use_pairwise_same_signs', False)
        self.use_hinge_primal = getattr(configs, 'use_hinge_primal', False)
        self.fix_C2 = getattr(configs, 'fix_C2', False)
        self.fix_C3 = getattr(configs, 'fix_C3', False)
        if self.method == MixedFeatureGuidanceMethod.METHOD_HARD_CONSTRAINT:
            self.configs.scipy_opt_method = 'SLSQP'
        if self.method in MixedFeatureGuidanceMethod.METHODS_UNIFORM_C:
            self.C = 1
            del self.cv_params['C']
        if (self.method in MixedFeatureGuidanceMethod.METHODS_NO_C3 and not self.use_hinge_primal) or self.fix_C3:
            self.C3 = 1
            del self.cv_params['C3']
        if self.method in MixedFeatureGuidanceMethod.METHODS_NO_C2 or self.fix_C2:
            self.C2 = 1
            del self.cv_params['C2']
        if self.disable_relaxed_guidance:
            self.C2 = np.inf
            if 'C2' in self.cv_params:
                del self.cv_params['C2']
        if self.disable_tikhonov:
            self.C = 0
            if 'C' in self.cv_params:
                del self.cv_params['C']
        self.quiet = False
        self.pairs = None
        self.feats_to_constrain = None
        self.learner_lasso = Lasso()

    def train_and_test(self, data):
        #data = deepcopy(data)
        #data = self.preprocessor.preprocess(data, self.configs)
        data = deepcopy(data)
        if self.num_features > 0:
            select_k_best = SelectKBest(f_regression, self.num_features)
            data.x = select_k_best.fit_transform(data.x, data.true_y)
        metadata = getattr(data, 'metadata', dict())

        source_data = None
        if self.configs.source_labels is not None:
            source_data = data.get_transfer_subset(self.configs.source_labels, include_unlabeled=False)
        if self.configs.target_labels is not None:
            data = data.get_transfer_subset(self.configs.target_labels, include_unlabeled=True)
        if not 'metadata' in metadata:
            ridge = method.SKLRidgeRegression(self.configs)
            ridge.quiet = True
            ridge.preprocessor = self.preprocessor
            ridge.use_validation = False
            ridge.use_test_error_for_model_selection = False
            ridge.configs.use_validation = False
            ridge.configs.use_test_error_for_model_selection = False
            data_copy = deepcopy(data)
            data_copy.set_train()
            data_copy.set_true_y()
            ridge.train_and_test(data_copy)
            metadata['true_w'] = ridge.w
        data.metadata = metadata
        p = data.x.shape[1]
        corr = np.zeros(p)
        training_corr = np.zeros(p)
        stat_func = scipy.stats.pearsonr
        if self.use_sign:
            stat_func = scipy.stats.linregress
        w_oracle = self.solve_w(data.x, data.true_y, 1)
        for i in range(p):
            Xi = data.x[:, i]
            Yi = data.true_y
            I = data.is_labeled & data.is_train
            training_corr[i] = stat_func(Xi[I], Yi[I])[0]
            if self.use_transfer:
                Xi = source_data.x[:, i]
                Yi = source_data.true_y
            if self.use_oracle:
                corr[i] = w_oracle[i]
            else:
                corr[i] = stat_func(Xi, Yi)[0]

        if self.method in {
            MixedFeatureGuidanceMethod.METHOD_RIDGE,
            MixedFeatureGuidanceMethod.METHOD_LASSO
        } and self.use_transfer:
            ridge = method.SKLRidgeRegression(self.configs)
            ridge.quiet = True
            ridge.use_validation = False
            ridge.use_test_error_for_model_selection = False
            ridge.configs.use_validation = False
            ridge.configs.use_test_error_for_model_selection = False
            source_data.data_set_ids[:] = self.configs.target_labels[0]
            ridge.train_and_test(source_data)
            source_pred = ridge.predict(data).y
            data.x = np.append(data.x, source_pred, axis=1)
        #print corr
        training_corr[~np.isfinite(training_corr)] = 0
        assert (np.isfinite(training_corr)).all()
        metadata['corr'] = corr
        metadata['training_corr'] = training_corr
        num_random_pairs = int(np.ceil(self.num_random_pairs*p))
        num_signs = int(np.ceil(self.num_random_signs*p))
        self.pairs = self.create_random_pairs(data.metadata['true_w'], num_pairs=num_random_pairs)
        if num_signs > p:
            num_signs = p
        self.feats_to_constrain = np.random.choice(p, num_signs, replace=False)
        return super(MixedFeatureGuidanceMethod, self).train_and_test(data)

    def get_stacking_x(self, data):
        x = np.zeros(data.x.shape)
        for i, t in enumerate(self.trained_stacked_methods):
            data_copy = deepcopy(data)
            data_copy.x = np.expand_dims(data_copy.x[:, i], 1)
            x[:, i] = t.predict(data_copy).y
        return x

    def train(self, data):
        assert data.is_regression
        self.is_classifier = not data.is_regression
        if self.use_stacking:
            self.trained_stacked_methods = list()
            I = data.is_labeled & data.is_train
            for i in range(data.p):
                t = deepcopy(self.stacking_method)
                data_copy = deepcopy(data)
                data_copy.x = np.expand_dims(data_copy.x[:, i], 1)
                o = t.train_and_test(data_copy)
                self.trained_stacked_methods.append(t)
            x_stacked = self.get_stacking_x(data)
            data = deepcopy(data)
            data.x = x_stacked
        return self.solve(data)

    @staticmethod
    def solve_w(x, y, C):
        try:
            p = x.shape[1]
            w = np.linalg.lstsq(x.T.dot(x) + C * np.eye(p), x.T.dot(y))[0]
        except Exception as e:
            w = np.zeros(x.shape[1])
            print 'solve_w error'
        return w

    @staticmethod
    #def eval(a, x, y, C, C2, C3):
    def eval_variance(data, a):
        x, y = data.get_xy()
        C, C2, C3 = data.get_reg()
        n = x.shape[0]
        p = x.shape[1]
        t = StandardScaler()
        loss = 0

        #C = 1000
        #a[:] = 1
        for i in range(n):
            I = array_functions.true(n)
            I[i] = False
            xi = x[i, :]
            yi = y[i]
            xmi = t.fit_transform(x[I, :])
            ymi = y[I]
            bi = ymi.mean()
            #w = np.linalg.lstsq(xmi.T.dot(xmi) + C*D_a, xmi.T.dot(ymi))[0]
            w = MixedFeatureGuidanceMethod.solve_w(a, xmi, ymi, C)
            loss += (xi.T.dot(w) + bi - yi)**2
            '''
            ridge = linear_model.Ridge(C, normalize=False)
            ridge.fit(xmi, ymi)
            b_ridge = ridge.intercept_
            w_ridge = ridge.coef_
            rel_err = array_functions.relative_error(w_ridge, w)
            '''
            pass
        loss = loss / n
        reg = 0
        #reg = C2*norm(a - C*np.ones(p))**2
        reg = C2 * norm(a) ** 2
        #reg = C2 * norm(a, 1)
        return loss + reg

    @staticmethod
    def eval(data, w):
        x, y = data.get_xy()
        C, C2, C3 = data.get_reg()
        n = x.shape[0]
        p = x.shape[1]

        b = y.mean()
        loss = norm(x.dot(w) + b - y) ** 2
        loss /= n

        loss2 = 0
        for i, j in data.pairs:
            loss2 += np.log(1 + np.exp(-(w[i]-w[j])))
        if len(data.pairs) > 0:
            loss2 /= len(data.pairs)
        reg = norm(w) ** 2
        return loss + C*reg + C2*loss2

    def create_grad(self, x, y, C, C2, C3):
        pass

    def create_random_pairs(self, w, num_pairs=10):
        pairs = list()
        p = w.size
        for i in range(num_pairs):
            j, k = np.random.choice(p, size=2, replace=False)
            if w[j] > w[k]:
                pairs.append((j,k))
            else:
                pairs.append((k, j))
            pass
        return pairs

    def solve(self, data):
        is_labeled_train = data.is_train & data.is_labeled
        x = data.x[is_labeled_train, :]
        #self.transform.with_mean = False
        #self.transform.with_std = False
        x = self.transform.fit_transform(x)
        y = data.y[is_labeled_train]
        n = float(x.shape[0])
        p = x.shape[1]
        #n = 50

        '''
        self.feats_to_constrain = np.arange(0, p)
        self.use_nonneg = False
        self.C = self.C2 = 1.0
        self.C = .001
        self.C2 = 1
        '''
        '''
        self.C = .001
        self.C2 = 1
        '''
        no_constraints = False
        self.C = float(self.C)
        self.C2 = float(self.C2)


        C = self.C
        C2 = self.C2
        C3 = self.C3
        #C = .001
        #C2 = 0
        use_nonneg_ridge = self.method == MixedFeatureGuidanceMethod.METHOD_RIDGE and self.use_nonneg
        if self.method == MixedFeatureGuidanceMethod.METHOD_ORACLE:
            assert False, 'Update this'
            #Refit with standardized data to clear transform
            #Is there a better way of doing this?
            self.transform.fit_transform(x)
            self.w = data.metadata['true_w']
            self.b = 0
            return
        elif self.method in {MixedFeatureGuidanceMethod.METHOD_RELATIVE, MixedFeatureGuidanceMethod.METHOD_HARD_CONSTRAINT}\
                or use_nonneg_ridge:
            opt_data = optimize_data(x, y, C, C2, C3)
            '''
            opt_data.pairs = [
                (0, 9),
                (1, 8),
                (2, 7),
                (3, 6)
            ]
            '''
            opt_data.pairs = list()
            constraints = list()
            pairs = self.pairs
            feats_to_constraint = self.feats_to_constrain
            true_w = data.metadata['true_w']
            if self.method == MixedFeatureGuidanceMethod.METHOD_HARD_CONSTRAINT:
                assert not self.use_corr
                constraints = list()

                for j, k in pairs:
                    if self.random_guidance and np.random.rand() > .5:
                        temp = j
                        j = k
                        k = temp
                    constraints.append({
                        'fun': lambda w, j=j, k=k: w[j] - w[k],
                        'type': 'ineq'
                    })
                #for i in range(num_signs):
                #    j = np.random.choice(p)

                for j in feats_to_constraint:
                    assert not self.random_guidance
                    fun = lambda w, j=j: w[j]*np.sign(true_w[j])
                    constraints.append({
                        'fun': fun,
                        'type': 'ineq',
                        'idx': j
                    })
            else:
                opt_data.pairs = pairs


            if self.method == MixedFeatureGuidanceMethod.METHOD_RELATIVE or use_nonneg_ridge:
                if self.use_nonneg:
                    feats_to_constraint = range(x.shape[1])
                assert len(feats_to_constraint) == 0 or len(pairs) == 0
                w = cvx.Variable(p)
                b = cvx.Variable(1)
                z = cvx.Variable(len(feats_to_constraint) + len(pairs))

                E = np.zeros((z.size[0], p))
                if len(pairs) > 0:
                    E = np.zeros((p, p))
                #if self.solve_dual and not self.use_pairwise_same_signs:
                if self.solve_dual:
                    assert len(pairs) == 0
                    alpha = cvx.Variable(z.size[0])
                '''
                loss = cvx.sum_entries(
                    cvx.power(
                        x*w + b - y,
                        2
                    )
                )
                '''
                v = x*w + b - y
                loss = (1.0/n) * cvx.sum_squares(v)
                #loss /= n
                constraints = list()
                idx = 0
                corr = data.metadata['corr']
                if self.use_training_corr:
                    corr = data.metadata['training_corr']
                if self.method != MixedFeatureGuidanceMethod.METHOD_RIDGE:
                    w_constraints = corr.copy()
                    if not self.use_corr:
                        w_constraints = true_w.copy()
                    for j, k in pairs:
                        jk_order = w_constraints[j] > w_constraints[k]
                        if self.random_guidance and np.random.rand() > .5:
                            jk_order = not jk_order
                        if self.use_pairwise_same_signs:
                            s = np.sign(w_constraints[j] * w_constraints[k])
                            #E[j, k] = s
                            E[idx, j] = s
                            E[idx, k] = s
                            constraints.append(w[j]*w[k] + z[idx] >= 0)
                        else:
                            if jk_order:
                                constraints.append(w[j] - w[k] + z[idx] >= 0)
                            else:
                                constraints.append(w[k] - w[j] + z[idx] >= 0)
                        idx += 1
                    if self.use_nonneg:
                        w_constraints[:] = 1
                    for j in feats_to_constraint:
                        s = np.sign(corr[j])
                        if self.random_guidance and np.random.rand() > .5:
                            s *= -1
                        constraints.append(w[j] * s + z[idx] >= 0)
                        E[idx, j] = s
                        idx += 1
                if not self.solve_dual:
                    if self.use_pairwise_same_signs and self.solve_scipy:
                        assert self.solve_scipy
                        y_primal = y.copy()
                        if self.mean_b:
                            y_primal -= y_primal.mean()
                        opt_data = {
                            'C': C,
                            'C2': C2,
                            'C3': C3,
                            'x': x,
                            'y': y_primal,
                            'E': E,
                            'n': n,
                            'p': p,
                        }
                        if self.use_hinge_primal:
                            v0 = np.zeros(p + E.shape[0])
                            bounds = [(None, None)]*p + [(0, None)]*E.shape[0]
                            results = optimize.minimize(
                                lambda v: eval_same_sign_hinge_primal(v, opt_data),
                                v0,
                                method=self.configs.scipy_opt_method,
                                jac=None,
                                # jac=lambda w: grad_same_sign_primal(w, opt_data),
                                options=None,
                                bounds=bounds,
                                constraints=None
                            )
                            # print results_eval.x
                            # print results.x
                            w, z = unpack_same_sign_hinge_primal(results.x, opt_data)
                            pass
                        else:
                            w0 = np.zeros(p)
                            results = optimize.minimize(
                                lambda w: eval_same_sign_primal(w, opt_data),
                                w0,
                                method=self.configs.scipy_opt_method,
                                jac=None,
                                #jac=lambda w: grad_same_sign_primal(w, opt_data),
                                options=None,
                                bounds=None,
                                constraints=None
                            )
                            #print results_eval.x
                            #print results.x
                            w = results.x
                        self.w = w
                    else:
                        #reg = cvx.norm2(w) ** 2
                        reg = cvx.sum_squares(w)

                        if self.use_l1:
                            #reg_guidance = cvx.norm1(z)
                            reg_guidance = cvx.sum_entries(z)
                        else:
                            reg_guidance = cvx.norm2(z) ** 2
                        if np.isinf(C2):
                            constraints.append(z == 0)
                            obj = cvx.Minimize(loss + C * reg)
                        else:
                            constraints.append(z >= 0)
                            obj = cvx.Minimize(loss + C * reg + C2 * reg_guidance)
                        if self.use_nonneg:
                            constraints.append(w >= 0)
                        if self.mean_b:
                            constraints.append(b == y.mean())
                        prob = cvx.Problem(obj, constraints)
                        if self.use_pairwise_same_signs:
                            qcqp = QCQP(prob)
                            num_runs = 1
                            if not self.running_cv:
                                num_runs = 10
                            best_value = np.inf
                            for run_idx in range(num_runs):
                                qcqp.suggest()
                                f_cd, v_cd = qcqp.improve(DCCP)
                                assert w.value is not None
                                if obj.value < best_value:
                                    self.w = np.squeeze(np.asarray(w.value))
                                    best_value = obj.value
                            if not self.running_cv:
                                print self.w
                                print np.squeeze(np.asarray(z.value))
                        else:
                            try:
                                prob.solve(solver=self.cvx_method)
                                assert w.value is not None
                                self.w = np.squeeze(np.asarray(w.value))
                            except:
                                self.w = np.zeros(p)
                if self.solve_dual:
                    if no_constraints:
                        C2 = 0
                    y_dual = y.copy()
                    if self.mean_b:
                        y_dual -= y_dual.mean()
                    #new math
                    try:
                        M = np.linalg.inv(n*C*np.eye(x.shape[0]) + x.dot(x.T))
                    except:
                        M = np.linalg.inv(n * (C + 1e-6) * np.eye(x.shape[0]) + x.dot(x.T))
                    B = x.dot(E.T)
                    Q = E.dot(E.T) - B.T.dot(M).dot(B)
                    if not self.solve_scipy:
                        delta = 2 * C * M.dot(y_dual) - M.dot(x).dot(E.T) * alpha
                        dual_objective = (.25 / C) * cvx.quad_form(alpha, Q) + y_dual.T.dot(M).dot(B) * alpha
                        dual_constraints = [
                            alpha >= 0
                        ]
                        if np.isfinite(C2):
                            dual_constraints.append(alpha <= C2)
                        if not self.mean_b:
                            constraints.append(cvx.sum_entries(delta) == 0)
                        if no_constraints:
                            dual_constraints += [alpha == 0]
                        dual_obj = cvx.Minimize(dual_objective)
                        dual_problem = cvx.Problem(dual_obj, dual_constraints)
                        try:
                            #cvx.SCS
                            dual_problem.solve(
                                solver=self.cvx_method,
                                verbose=False,
                                eps=1e-6,
                                alpha=1.8
                            )
                            w_dual = (1 / (2 * C)) * (x.T.dot(delta.value) + E.T.dot(alpha.value))
                            w_dual = np.squeeze(np.asarray(w_dual).T)
                            w_primal = self.w
                            w_anal = inv(x.T.dot(x) / n + C * np.eye(p)).dot(x.T).dot(y) / n
                            self.w = w_dual
                        except:
                            self.w = np.zeros(p)
                            self.b = 0
                            if not self.running_cv:
                                print 'Dual solver failed - setting to 0'
                        if not self.mean_b:
                            K = x.dot(self.w) - y_dual
                            self.b = -K.mean()
                    else:
                        opt_data = {
                            'C': C,
                            'C2': C2,
                            'x': x,
                            'y': y_dual,
                            'E': E,
                            'n': n,
                            'p': p,
                            'Q': Q,
                            'M': M,
                            'B': B,
                            'use_pairwise_same_signs': self.use_pairwise_same_signs
                        }
                        x0 = np.zeros(E.shape[0])
                        bounds = [(0, C2)] * E.shape[0]
                        results = optimize.minimize(
                            lambda x: eval_quad(x, opt_data),
                            x0,
                            method=self.configs.scipy_opt_method,
                            jac=None,
                            options=None,
                            bounds=bounds,
                            constraints=None
                        )
                        alpha_dual_scipy = results.x
                        if self.use_pairwise_same_signs:
                            A_inv, B, F, delta = compute_quad_matrices(alpha_dual_scipy, opt_data)
                            w_dual_scipy = A_inv.dot(x.T).dot(delta)
                        else:
                            delta = 2 * C * M.dot(y_dual) - M.dot(x).dot(E.T).dot(alpha_dual_scipy)
                            w_dual_scipy = (1 / (2 * C)) * (x.T.dot(delta) + E.T.dot(alpha_dual_scipy))
                        self.w = w_dual_scipy
                        #print ''
                    '''
                if b.value is not None:
                    assert abs(b.value - y.mean())/abs(b.value) <= 1e-3
                '''
            else:
                assert not self.use_corr
                eval_func = lambda a: MixedFeatureGuidanceMethod.eval(opt_data, a)

                w0 = np.zeros(p)
                options = dict()
                options['maxiter'] = 1000
                options['disp'] = False
                bounds = [(None, None)] * p

                '''
                w1 = optimize.minimize(
                    eval_func,
                    a0,
                    method=self.configs.scipy_opt_method,
                    jac=None,
                    options=options,
                    bounds = bounds,
                    constraints=constraints
                ).x
                '''
                if self.method == MixedFeatureGuidanceMethod.METHOD_ORACLE_SPARSITY:
                    assert False



                #with Capturing() as output:
                results = optimize.minimize(
                    eval_func,
                    w0,
                    method=self.configs.scipy_opt_method,
                    jac=None,
                    options=options,
                    bounds = bounds,
                    constraints=constraints
                )
                w2 = results.x
                self.w = np.asarray(results.x)
        else:
            #assert not self.use_corr
            if self.method == MixedFeatureGuidanceMethod.METHOD_LASSO:
                self.learner_lasso.set_params(alpha=C)
                self.learner_lasso.fit(x, y)
            else:
                assert self.method == MixedFeatureGuidanceMethod.METHOD_RIDGE
                self.w = self.solve_w(x, y, C)
        if self.mean_b or self.method in {MixedFeatureGuidanceMethod.METHOD_RIDGE, MixedFeatureGuidanceMethod.METHOD_LASSO}:
            self.b = y.mean()
        else:
            if not self.solve_dual:
                self.b = b.value
            else:
                assert False
        if not self.running_cv:
            try:
                print prob.status
                if prob.status == 'optimal_inaccurate':
                    #print 'Optimization failed, using ridge'
                    pass
            except:
                pass

        compare_to_ridge = False
        if compare_to_ridge and not self.running_cv and self.method not in {
            MixedFeatureGuidanceMethod.METHOD_RIDGE,
            MixedFeatureGuidanceMethod.METHOD_LASSO
        }:
            w2 = self.solve_w(x,y,C)
            true_w = data.metadata['true_w']
            err1 = array_functions.normalized_error(self.w, true_w)
            err2 = array_functions.normalized_error(w2, true_w)
            print str(err1 - err2)
            c2 = deepcopy(self.configs)
            c2.method = MixedFeatureGuidanceMethod.METHOD_RIDGE
            t2 = MixedFeatureGuidanceMethod(c2)
            t2.quiet = True
            t2.train_and_test(data)
            w = self.w
            w2 = t2.w
            pass
        #print self.w
        self.true_w = data.metadata['true_w']
        pass



    def predict(self, data):
        o = Output(data)
        #W = pairwise.rbf_kernel(data.x,self.x,self.sigma)
        x = data.x
        if self.use_stacking:
            x = self.get_stacking_x(data)
        x = self.transform.transform(x)
        if self.method == MixedFeatureGuidanceMethod.METHOD_LASSO:
            o.y = self.learner_lasso.predict(x)
            o.fu = o.y
        else:
            o.y = x.dot(self.w) + self.b
            o.fu = o.y
            o.w = self.w
            o.true_w = self.true_w
        return o


    @property
    def prefix(self):
        s = 'Mixed-feats'
        use_pairs = False
        use_signs = False
        try:
            if self.preprocessor.prefix() is not None:
                s += '_' + self.preprocessor.prefix()
        except:
            pass
        num_pairs = getattr(self, 'num_random_pairs', 0)
        num_signs = getattr(self, 'num_random_signs', 0)
        if self.method == MixedFeatureGuidanceMethod.METHOD_RIDGE:
            s += '_method=Ridge'
        elif self.method == MixedFeatureGuidanceMethod.METHOD_LASSO:
            s += '_method=Lasso'
        elif self.method == MixedFeatureGuidanceMethod.METHOD_RELATIVE:
            s += '_method=Rel'
            if getattr(self, 'solve_dual') and num_signs > 0:
                s += '_dual'
                if getattr(self, 'solve_scipy'):
                    s += 'Scipy'
            if getattr(self, 'mean_b'):
                s += '_meanB'
        elif self.method == MixedFeatureGuidanceMethod.METHOD_ORACLE:
            s += '_method=Oracle'
        elif self.method == MixedFeatureGuidanceMethod.METHOD_ORACLE_SPARSITY:
            s += '_method=OracleSparsity'
        elif self.method == MixedFeatureGuidanceMethod.METHOD_HARD_CONSTRAINT:
            s += '_method=HardConstraints'
        if self.method in MixedFeatureGuidanceMethod.METHODS_USES_SIGNS and num_signs > 0:
            s += '_signs=' + str(num_signs)
        if self.method in MixedFeatureGuidanceMethod.METHODS_USES_PAIRS and num_pairs > 0:
            if getattr(self, 'use_pairwise_same_signs'):
                if not self.solve_dual:
                    if self.solve_scipy:
                        if getattr(self, 'use_hinge_primal'):
                            s += '-pairsSameSignPrimalHinge=' + str(num_pairs)
                        else:
                            s += '_pairsSameSignPrimal=' + str(num_pairs)
                    else:
                        s += '-pairsSameSignQCQP=' + str(num_pairs)
                else:
                    s += '_pairsSameSign=' + str(num_pairs)
            else:
                s += '_pairs=' + str(num_pairs)
        if getattr(self, 'random_guidance', False) and self.method != MixedFeatureGuidanceMethod.METHOD_RIDGE:
            s += '_random'
        if getattr(self, 'use_sign', False) and self.method == MixedFeatureGuidanceMethod.METHOD_RELATIVE:
            s += '-use_sign'
        if getattr(self, 'use_corr', False) and \
                        self.method not in {MixedFeatureGuidanceMethod.METHOD_RIDGE, MixedFeatureGuidanceMethod.METHOD_LASSO}:
            if getattr(self, 'use_training_corr', False):
                s += '_trainCorr'
            elif getattr(self, 'use_oracle', False):
                s += '_oracle'
            else:
                s += '_corr'
        if getattr(self, 'use_nonneg', False):
            s += '_nonneg'
        if self.method != MixedFeatureGuidanceMethod.METHOD_RIDGE and getattr(self, 'disable_relaxed_guidance', False):
            s += '_not-relaxed'
        if getattr(self, 'disable_tikhonov', False):
            s += '_no-tikhonov'
        if getattr(self, 'use_stacking', False):
            s += '_stacked'
        if getattr(self, 'cvx_method', 'SCS') != 'SCS':
            s += '_' + self.cvx_method
        if getattr(self, 'use_l1', False) and self.method == MixedFeatureGuidanceMethod.METHOD_RELATIVE:
            s += '_l1'
        if getattr(self, 'fix_C2'):
            s += '_fixC2'
        if getattr(self, 'fix_C3'):
            s += '_fixC3'
        if getattr(self, 'use_transfer', False):
            s += '_transfer'
        if getattr(self, 'num_features', -1) > 0:
            s += '_' + str(self.num_features)
        if self.use_validation:
            s += '-VAL'
        elif self.use_test_error_for_model_selection:
            s += '-TEST'
        return s