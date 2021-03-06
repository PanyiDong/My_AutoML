"""
File: _advance.py
Author: Panyi Dong
GitHub: https://github.com/PanyiDong/
Mathematics Department, University of Illinois at Urbana-Champaign (UIUC)

Project: My_AutoML
Latest Version: 0.2.0
Relative Path: /My_AutoML/_feature_selection/_advance.py
File Created: Tuesday, 5th April 2022 11:36:15 pm
Author: Panyi Dong (panyid2@illinois.edu)

-----
Last Modified: Wednesday, 11th May 2022 9:57:27 am
Modified By: Panyi Dong (panyid2@illinois.edu)

-----
MIT License

Copyright (c) 2022 - 2022, Panyi Dong

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from inspect import isclass
from typing import Callable
from itertools import combinations
from collections import Counter
from My_AutoML._utils._base import has_method
import warnings
import numpy as np
import pandas as pd
import itertools

from My_AutoML._utils import (
    minloc,
    maxloc,
    True_index,
    Pearson_Corr,
    MI,
    t_score,
    ANOVA,
    random_index,
)
from My_AutoML._utils._optimize import (
    get_estimator,
    get_metrics,
)
from My_AutoML._constant import UNI_CLASS


class FeatureFilter:

    """
    Use certain criteria to score each feature and select most relevent ones

    Parameters
    ----------
    criteria: use what criteria to score features, default = 'Pearson'
    supported {'Pearson', 'MI'}
    'Pearson': Pearson Correlation Coefficient
    'MI': 'Mutual Information'

    n_components: threshold to retain features, default = None
    will be set to n_features

    n_prop: float, default = None
    proprotion of features to select, if None, no limit
    n_components have higher priority than n_prop
    """

    def __init__(
        self,
        criteria="Pearson",
        n_components=None,
        n_prop=None,
    ):
        self.criteria = criteria
        self.n_components = n_components
        self.n_prop = n_prop

        self._fitted = False

    def fit(self, X, y=None):

        # check whether y is empty
        if isinstance(y, pd.DataFrame):
            _empty = y.isnull().all().all()
        elif isinstance(y, pd.Series):
            _empty = y.isnull().all()
        elif isinstance(y, np.ndarray):
            _empty = np.all(np.isnan(y))
        else:
            _empty = y == None

        if _empty:
            raise ValueError("Must have response!")

        if self.criteria == "Pearson":
            self._score = Pearson_Corr(X, y)
        elif self.criteria == "MI":
            self._score = MI(X, y)

        self._fitted = True

        return self

    def transform(self, X):

        # check whether n_components/n_prop is valid
        if self.n_components is None and self.n_prop is None:
            self.n_components = X.shape[1]
        elif self.n_components is not None:
            self.n_components = min(self.n_components, X.shape[1])
        # make sure selected features is at least 1
        elif self.n_prop is not None:
            self.n_components = max(1, int(self.n_prop * X.shape[1]))

        _columns = np.argsort(self._score)[: self.n_components]

        return X.iloc[:, _columns]


# FeatureWrapper

# Exhaustive search for optimal feature combination

# Sequential Feature Selection (SFS)
# Sequential Backward Selection (SBS)
# Sequential Floating Forward Selection (SFFS)
# Adapative Sequential Forward Floating Selection (ASFFS)
class ASFFS:

    """
    Adaptive Sequential Forward Floating Selection (ASFFS)
    Mostly, ASFFS performs the same as Sequential Floating Forward Selection (SFFS),
    where only one feature is considered as a time. But, when the selected features are coming
    close to the predefined maximum, a adaptive generalization limit will be activated, and
    more than one features can be considered at one time. The idea is to consider the correlation
    between features. [1]

    [1] Somol, P., Pudil, P., Novovi??ov??, J. and Pacl??k, P., 1999. Adaptive floating search
    methods in feature selection. Pattern recognition letters, 20(11-13), pp.1157-1163.

    Parameters
    ----------
    d: maximum features retained, default = None
    will be calculated as max(max(20, n), 0.5 * n)

    Delta: dynamic of maximum number of features, default = 0
    d + Delta features will be retained

    b: range for adaptive generalization limit to activate, default = None
    will be calculated as max(5, 0.05 * n)

    r_max: maximum of generalization limit, default = 5
    maximum features to be considered as one step

    model: the model used to evaluate the objective function, default = 'linear'
    supproted ('Linear', 'Lasso', 'Ridge')

    objective: the objective function of significance of the features, default = 'MSE'
    supported {'MSE', 'MAE'}
    """

    def __init__(
        self,
        n_components=None,
        Delta=0,
        b=None,
        r_max=5,
        model="Linear",
        objective="MSE",
    ):
        self.n_components = n_components
        self.Delta = Delta
        self.b = b
        self.r_max = r_max
        self.model = model
        self.objective = objective

        self._fitted = False

    def generalization_limit(self, k, d, b):

        if np.abs(k - d) < b:
            r = self.r_max
        elif np.abs(k - d) < self.r_max + b:
            r = self.r_max + b - np.abs(k - d)
        else:
            r = 1

        return r

    def _Forward_Objective(self, selected, unselected, o, X, y):

        _subset = list(itertools.combinations(unselected, o))
        _comb_subset = [
            selected + list(item) for item in _subset
        ]  # concat selected features with new features

        _objective_list = []
        if self.model == "Linear":
            from sklearn.linear_model import LinearRegression

            _model = LinearRegression()
        elif self.model == "Lasso":
            from sklearn.linear_model import Lasso

            _model = Lasso()
        elif self.model == "Ridge":
            from sklearn.linear_model import Ridge

            _model = Ridge()
        else:
            raise ValueError("Not recognizing model!")

        if self.objective == "MSE":
            from sklearn.metrics import mean_squared_error

            _obj = mean_squared_error
        elif self.objective == "MAE":
            from sklearn.metrics import mean_absolute_error

            _obj = mean_absolute_error

        for _set in _comb_subset:
            _model.fit(X[_set], y)
            _predict = _model.predict(X[_set])
            _objective_list.append(
                1 / _obj(y, _predict)
            )  # the goal is to maximize the objective function

        return (
            _subset[maxloc(_objective_list)],
            _objective_list[maxloc(_objective_list)],
        )

    def _Backward_Objective(self, selected, o, X, y):

        _subset = list(itertools.combinations(selected, o))
        _comb_subset = [
            [_full for _full in selected if _full not in item] for item in _subset
        ]  # remove new features from selected features

        _objective_list = []
        if self.model == "Linear":
            from sklearn.linear_model import LinearRegression

            _model = LinearRegression()
        elif self.model == "Lasso":
            from sklearn.linear_model import Lasso

            _model = Lasso()
        elif self.model == "Ridge":
            from sklearn.linear_model import Ridge

            _model = Ridge()
        else:
            raise ValueError("Not recognizing model!")

        if self.objective == "MSE":
            from sklearn.metrics import mean_squared_error

            _obj = mean_squared_error
        elif self.objective == "MAE":
            from sklearn.metrics import mean_absolute_error

            _obj = mean_absolute_error

        for _set in _comb_subset:
            _model.fit(X[_set], y)
            _predict = _model.predict(X[_set])
            _objective_list.append(
                1 / _obj(y, _predict)
            )  # the goal is to maximize the objective function

        return (
            _subset[maxloc(_objective_list)],
            _objective_list[maxloc(_objective_list)],
        )

    def fit(self, X, y):

        n, p = X.shape
        features = list(X.columns)

        if self.n_components == None:
            _n_components = min(max(20, p), int(0.5 * p))
        else:
            _n_components = self.n_components
        if self.b == None:
            _b = min(5, int(0.05 * p))

        _k = 0
        self.J_max = [
            0 for _ in range(p + 1)
        ]  # mark the most significant objective function value
        self._subset_max = [
            [] for _ in range(p + 1)
        ]  # mark the best performing subset features
        _unselected = features.copy()
        _selected = (
            []
        )  # selected  feature stored here, not selected will be stored in features

        while True:

            # Forward Phase
            _r = self.generalization_limit(_k, _n_components, _b)
            _o = 1

            while (
                _o <= _r and len(_unselected) >= 1
            ):  # not reasonable to add feature when all selected

                _new_feature, _max_obj = self._Forward_Objective(
                    _selected, _unselected, _o, X, y
                )

                if _max_obj > self.J_max[_k + _o]:
                    self.J_max[_k + _o] = _max_obj.copy()
                    _k += _o
                    for (
                        _f
                    ) in (
                        _new_feature
                    ):  # add new features and remove these features from the pool
                        _selected.append(_f)
                    for _f in _new_feature:
                        _unselected.remove(_f)
                    self._subset_max[_k] = _selected.copy()
                    break
                else:
                    if _o < _r:
                        _o += 1
                    else:
                        _k += 1  # the marked in J_max and _subset_max are considered as best for _k features
                        _selected = self._subset_max[
                            _k
                        ].copy()  # read stored best subset
                        _unselected = features.copy()
                        for _f in _selected:
                            _unselected.remove(_f)
                        break

            # Termination Condition
            if _k >= _n_components + self.Delta:
                break

            # Backward Phase
            _r = self.generalization_limit(_k, _n_components, _b)
            _o = 1

            while (
                _o <= _r and _o < _k
            ):  # not reasonable to remove when only _o feature selected

                _new_feature, _max_obj = self._Backward_Objective(_selected, _o, X, y)

                if _max_obj > self.J_max[_k - _o]:
                    self.J_max[_k - _o] = _max_obj.copy()
                    _k -= _o
                    for (
                        _f
                    ) in (
                        _new_feature
                    ):  # add new features and remove these features from the pool
                        _unselected.append(_f)
                    for _f in _new_feature:
                        _selected.remove(_f)
                    self._subset_max[_k] = _selected.copy()

                    _o = 1  # return to the start of backward phase, make sure the best subset is selected
                else:
                    if _o < _r:
                        _o += 1
                    else:
                        break

        self.selected_ = _selected

        self._fitted = True

        return self

    def transform(self, X):

        return X.loc[:, self.selected_]


# Genetic Algorithm (GA)
class GeneticAlgorithm:

    """
    Use Genetic Algorithm (GA) to select best subset features [1]

    Procedure: (1) Train a feature pool where every individual is trained on predefined methods,
    result is pool of binary lists where 1 for feature selected, 0 for not selected

    (2) Use Genetic Algorithm to generate a new selection binary list
        (a) Selection: Roulette wheel selection, use fitness function to randomly select one individual
        (b) Crossover: Single-point Crossover operator, create child selection list from parents list
        (c) Mutation: Mutate the selection of n bits by certain percentage

    [1] Tan, F., Fu, X., Zhang, Y. and Bourgeois, A.G., 2008. A genetic algorithm-based method for
    feature subset selection. Soft Computing, 12(2), pp.111-120.

    Parameters
    ----------
    n_components: Number of features to retain, default = 20

    n_prop: float, default = None
    proprotion of features to select, if None, no limit
    n_components have higher priority than n_prop

    n_generations: Number of looping generation for GA, default = 10

    feature_selection: Feature selection methods to generate a pool of selections, default = 'auto'
    support ('auto', 'random', 'Entropy', 't_statistics', 'SVM_RFE')

    n_initial: Number of random feature selection rules to initialize, default = 10

    fitness_func: Fitness function, default None
    deafult will set as w * Accuracy + (1 - w) / regularization, all functions must be maximization optimization

    fitness_fit: Model to fit selection and calculate accuracy for fitness, default = 'SVM'
    support ('Linear', 'Logistic', 'Random Forest', 'SVM')

    fitness_weight: Default fitness function weight for accuracy, default = 0.9

    n_pair: Number of pairs of new selection rules to generate, default = 5

    ga_selection: How to perform selection in GA, default = 'Roulette Wheel'
    support ('Roulette Wheel', 'Rank', 'Steady State', 'Tournament', 'Elitism', 'Boltzmann')

    p_crossover: Probability to perform crossover, default = 1

    ga_crossover: How to perform crossover in GA, default = 'Single-point'
    support ('Single-point', 'Two-point', 'Uniform')

    crossover_n: Place of crossover points to perform, default = None
    deafult will set to p / 4 for single-point crossover

    p_mutation: Probability to perform mutation (flip bit in selection list), default = 0.001

    mutation_n: Number of mutation points to perform, default = None
    default will set to p / 10

    seed = 1
    """

    def __init__(
        self,
        n_components=None,
        n_prop=None,
        n_generations=10,
        feature_selection="random",
        n_initial=10,
        fitness_func=None,
        fitness_fit="SVM",
        fitness_weight=0.9,
        n_pair=5,
        ga_selection="Roulette Wheel",
        p_crossover=1,
        ga_crossover="Single-point",
        crossover_n=None,
        p_mutation=0.001,
        mutation_n=None,
        seed=1,
    ):
        self.n_components = n_components
        self.n_prop = n_prop
        self.n_generations = n_generations
        self.feature_selection = feature_selection
        self.n_initial = n_initial
        self.fitness_func = fitness_func
        self.fitness_fit = fitness_fit
        self.fitness_weight = fitness_weight
        self.n_pair = n_pair
        self.ga_selection = ga_selection
        self.p_crossover = p_crossover
        self.ga_crossover = ga_crossover
        self.crossover_n = crossover_n
        self.p_mutation = p_mutation
        self.mutation_n = mutation_n
        self.seed = seed

        self._auto_sel = {
            "Entropy": self._entropy,
            "t_statistics": self._t_statistics,
            "SVM_RFE": self._SVM_RFE,
        }

        self._fitted = False

    def _random(self, X, y, n):

        # randomly select n features from X
        _, p = X.shape

        if n > p:
            raise ValueError(
                "Selected features can not be larger than dataset limit {}, get {}.".format(
                    p, n
                )
            )

        _index = random_index(n, p)

        _selected = [0 for _ in range(p)]  # default all as 0
        for i in range(n):  # select n_components as selected
            _selected[_index[i]] = 1

        return _selected

    def _entropy(self, X, y, n):

        # call Mutual Information from FeatureFilter
        _score = MI(X, y)

        # select highest scored features
        _score_sort = np.flip(np.argsort(_score))

        _selected = [0 for _ in range(len(_score_sort))]  # default all as 0
        for i in range(n):  # select n_components as selected
            _selected[_score_sort[i]] = 1

        return _selected

    def _t_statistics(self, X, y, n):

        # for 2 group dataset, use t-statistics; otherwise, use ANOVA
        if len(np.unique(y)) == 2:
            _score = t_score(X, y)
        elif len(np.unique(y)) > 2:
            _score = ANOVA(X, y)
        else:
            raise ValueError("Only support for more than 2 groups, get only 1 group!")

        # select lowest scored features
        _score_sort = np.argsort(_score)

        _selected = [0 for _ in range(len(_score_sort))]  # default all as 0
        for i in range(n):  # select n_components as selected
            _selected[_score_sort[i]] = 1

        return _selected

    def _SVM_RFE(self, X, y, n):

        from sklearn.feature_selection import RFE

        # make a difference when fitting regression/classification models
        if len(pd.unique(y.values.ravel())) <= UNI_CLASS:
            from sklearn.svm import SVC

            _estimator = SVC(kernel="linear")
        else:
            from sklearn.svm import SVR

            _estimator = SVR(kernel="linear")

        # using sklearn RFE to recursively remove one feature using SVR, until n_components left
        _selector = RFE(_estimator, n_features_to_select=n, step=1)
        _selector = _selector.fit(X.values, y.values.ravel())

        _selected = (
            _selector.support_.tolist()
        )  # retunr the mask list of feature selection
        _selected = [int(item) for item in _selected]

        return _selected

    def _cal_fitness(self, X, y, selection):

        if not self.fitness_func:  # fit selected features and calcualte accuracy score
            if self.fitness_fit == "Linear":
                if len(pd.unique(y.values.ravel())) <= UNI_CLASS:
                    from sklearn.linear_model import LogisticRegression
                    from sklearn.metrics import accuracy_score

                    model = LogisticRegression()
                    metric = accuracy_score
                else:
                    from sklearn.linear_model import LinearRegression
                    from sklearn.metrics import mean_squared_error

                    model = LinearRegression()
                    metric = mean_squared_error
            elif self.fitness_fit == "Decision Tree":
                if len(pd.unique(y.values.ravel())) <= UNI_CLASS:
                    from sklearn.tree import DecisionTreeClassifier
                    from sklearn.metrics import accuracy_score

                    model = DecisionTreeClassifier()
                    metric = accuracy_score
                else:
                    from sklearn.tree import DecisionTreeRegressor
                    from sklearn.metrics import mean_squared_error

                    model = DecisionTreeRegressor()
                    metric = mean_squared_error
            elif self.fitness_fit == "Random Forest":
                if len(pd.unique(y.values.ravel())) <= UNI_CLASS:
                    from sklearn.ensemble import RandomForestClassifier
                    from sklearn.metrics import accuracy_score

                    model = RandomForestClassifier()
                    metric = accuracy_score
                else:
                    from sklearn.ensemble import RandomForestRegressor
                    from sklearn.metrics import mean_squared_error

                    model = RandomForestRegressor()
                    metric = mean_squared_error
            elif self.fitness_fit == "SVM":  # select by y using SVC and SVR
                if len(pd.unique(y.values.ravel())) <= UNI_CLASS:
                    from sklearn.svm import SVC
                    from sklearn.metrics import accuracy_score

                    model = SVC()
                    metric = accuracy_score
                else:
                    from sklearn.svm import SVR
                    from sklearn.metrics import mean_squared_error

                    model = SVR()
                    metric = mean_squared_error
            else:
                raise ValueError(
                    'Only support ["Linear", "Decision Tree", "Random Forest", "SVM"], get {}'.format(
                        self.fitness_fit
                    )
                )

            # if none of the features are selected, use mean as prediction
            if (np.array(selection) == 0).all():
                y_pred = [np.mean(y) for _ in range(len(y))]
            # otherwise, use selected features to fit a model and predict
            else:
                model.fit(X.iloc[:, True_index(selection)].values, y.values.ravel())
                y_pred = model.predict(X.iloc[:, True_index(selection)])
            _accuracy_score = metric(y, y_pred)

            return self.fitness_weight * _accuracy_score + (
                1 - self.fitness_weight
            ) / max(sum(selection), 1)
        else:
            return self.fitness_func(X, y, selection)

    def _GeneticAlgorithm(self, X, y, selection_pool):

        n, p = X.shape

        # calculate the fitness of all feature selection in the pool
        try:  # self._fitness from None value to np.array, type change
            _fitness_empty = not self._fitness
        except ValueError:
            _fitness_empty = not self._fitness.any()

        if (
            _fitness_empty
        ):  # first round of calculating fitness for all feature selections
            self._fitness = []
            for _seletion in selection_pool:
                self._fitness.append(self._cal_fitness(X, y, _seletion))

            # normalize the fitness
            self._fitness = np.array(self._fitness)
            self._sum_fitness = sum(self._fitness)
            self._fitness /= self._sum_fitness
        else:
            self._fitness *= self._sum_fitness
            for i in range(2 * self.n_pair):
                self._fitness = np.append(
                    self._fitness, self._cal_fitness(X, y, selection_pool[-(i + 1)])
                )  # only need to calculate the newly added ones
                self._sum_fitness += self._fitness[-1]
            # normalize the fitness
            self._fitness /= self._sum_fitness

        # Selection
        if self.ga_selection == "Roulette Wheel":
            # select two individuals from selection pool based on probability (self._fitness)
            # insert into selection_pool (last two), will be the placeholder for offsprings
            for _ in range(2 * self.n_pair):
                selection_pool.append(
                    selection_pool[
                        np.random.choice(len(self._fitness), 1, p=self._fitness)[0]
                    ]
                )

        # Crossover, generate offsprings
        if (
            np.random.rand() < self.p_crossover
        ):  # only certain probability of executing crossover
            if self.ga_crossover == "Single-point":
                if not self.crossover_n:
                    self.crossover_n = int(
                        p / 4
                    )  # default crossover point is first quarter point
                else:
                    if self.crossover_n > p:
                        raise ValueError(
                            "Place of cross points must be smaller than p = {}, get {}.".format(
                                p, self.crossover_n
                            )
                        )
                    self.crossover_n == int(self.crossover_n)

                for i in range(self.n_pair):
                    _tmp1 = selection_pool[-(2 * i + 2)]
                    _tmp2 = selection_pool[-(2 * i + 1)]
                    selection_pool[-(2 * i + 2)] = (
                        _tmp2[: self.crossover_n] + _tmp1[self.crossover_n :]
                    )  # exchange first crossover_n bits from parents
                    selection_pool[-(2 * i + 1)] = (
                        _tmp1[: self.crossover_n] + _tmp2[self.crossover_n :]
                    )

        # Mutation
        for i in range(2 * self.n_pair):  # for two offsprings
            if (
                np.random.rand() < self.p_mutation
            ):  # only certain probability of executing mutation
                if not self.mutation_n:
                    self.mutation_n = int(
                        p / 10
                    )  # default number of mutation point is first quarter point
                else:
                    if self.mutation_n > p:
                        raise ValueError(
                            "Number of mutation points must be smaller than p = {}, get {}.".format(
                                p, self.mutation_n
                            )
                        )
                    self.mutation_n == int(self.mutation_n)

                _mutation_index = random_index(
                    self.mutation_n, p, seed=None
                )  # randomly select mutation points
                selection_pool[-(i + 1)] = [
                    selection_pool[-(i + 1)][j]
                    if j not in _mutation_index
                    else 1 - selection_pool[-(i + 1)][j]
                    for j in range(p)
                ]  # flip mutation points (0 to 1, 1 to 0)

        return selection_pool

    def _early_stopping(
        self,
    ):  # only the difference between the best 10 selection rules are smaller than 0.001 will early stop

        if len(self._fitness) < 10:
            return False
        else:
            _performance_order = np.flip(
                np.argsort(self._fitness)
            )  # select performance from highest to lowest
            if (
                self._fitness[_performance_order[0]]
                - self._fitness[_performance_order[9]]
                < 0.001
            ):
                return True
            else:
                return False

    def fit(self, X, y):

        np.random.seed(self.seed)  # set random seed

        n, p = X.shape
        # check whether n_components/n_prop is valid
        if self.n_components is None and self.n_prop is None:
            self.n_components = X.shape[1]
        elif self.n_components is not None:
            self.n_components = min(self.n_components, p)
        # make sure selected features is at least 1
        elif self.n_prop is not None:
            self.n_components = max(1, int(self.n_prop * p))
        if self.n_components == p:
            warnings.warn("All features selected, no selection performed!")
            self.selection_ = [1 for _ in range(self.n_components)]
            return self

        self.n_generations = int(self.n_generations)

        # both probability of crossover and mutation must within range [0, 1]
        self.p_crossover = float(self.p_crossover)
        if self.p_crossover > 1 or self.p_crossover < 0:
            raise ValueError(
                "Probability of crossover must in [0, 1], get {}.".format(
                    self.p_crossover
                )
            )

        self.p_mutation = float(self.p_mutation)
        if self.p_mutation > 1 or self.p_mutation < 0:
            raise ValueError(
                "Probability of mutation must in [0, 1], get {}.".format(
                    self.p_mutation
                )
            )

        # select feature selection methods
        # if auto, all default methods will be used; if not, use predefined one
        if self.feature_selection == "auto":
            self._feature_sel_methods = self._auto_sel
        elif self.feature_selection == "random":
            self.n_initial = int(self.n_initial)
            self._feature_sel_methods = {}
            for i in range(
                self.n_initial
            ):  # get n_initial random feature selection rule
                self._feature_sel_methods["random_" + str(i + 1)] = self._random
        else:
            self.feature_selection = (
                [self.feature_selection]
                if not isinstance(self.feature_selection, list)
                else self.feature_selection
            )
            self._feature_sel_methods = {}

            # check if all methods are available
            for _method in self.feature_selection:
                if _method not in [*self._auto_sel]:
                    raise ValueError(
                        "Not recognizing feature selection methods, only support {}, get {}.".format(
                            [*self._auto_sel], _method
                        )
                    )
                self._feature_sel_methods[_method] = self._auto_sel[_method]

        self._fit(X, y)

        self._fitted = True

        return self

    def _fit(self, X, y):

        # generate the feature selection pool using
        _sel_methods = [*self._feature_sel_methods]
        _sel_pool = []  # store all selection rules
        self._fitness = None  # store the fitness of every individual

        # keep diversity for the pool, selection rule can have different number of features retained
        _iter = max(1, int(np.log2(self.n_components)))
        for i in range(_iter):
            n = 2 ** (i + 1)
            for _method in _sel_methods:
                _sel_pool.append(self._feature_sel_methods[_method](X, y, n))

        # loop through generations to run Genetic algorithm and Induction algorithm
        for _ in range(self.n_generations):
            _sel_pool = self._GeneticAlgorithm(X, y, _sel_pool)

            if self._early_stopping():
                break

        self.selection_ = _sel_pool[
            np.flip(np.argsort(self._fitness))[0]
        ]  # selected features, {1, 0} list

        return self

    def transform(self, X):

        # check for all/no feature removed cases
        if self.selection_.count(self.selection_[0]) == len(self.selection_):
            if self.selection_[0] == 0:
                warnings.warn("All features removed.")
            elif self.selection_[1] == 1:
                warnings.warn("No feature removed.")
            else:
                raise ValueError("Not recognizing the selection list!")

        return X.iloc[:, True_index(self.selection_)]


# CHCGA

# Exhaustive search is practically impossible to implement in a reasonable time,
# so it's not included in the package, but it can be used.
# class ExhaustiveFS:

#     """
#     Exhaustive Feature Selection

#     Parameters
#     ----------
#     estimator: str or sklearn estimator, default = "Lasso"
#     estimator must have fit/predict methods

#     criteria: str or sklearn metric, default = "accuracy"
#     """

#     def __init__(
#         self,
#         estimator="Lasso",
#         criteria="neg_accuracy",
#     ):
#         self.estimator = estimator
#         self.criteria = criteria

#         self._fitted = False

#     def fit(self, X, y):

#         # make sure estimator is recognized
#         if self.estimator == "Lasso":
#             from sklearn.linear_model import Lasso

#             self.estimator = Lasso()
#         elif self.estimator == "Ridge":
#             from sklearn.linear_model import Ridge

#             self.estimator = Ridge()
#         elif isclass(type(self.estimator)):
#             # if estimator is recognized as a class
#             # make sure it has fit/predict methods
#             if not has_method(self.estimator, "fit") or not has_method(
#                 self.estimator, "predict"
#             ):
#                 raise ValueError("Estimator must have fit/predict methods!")
#         else:
#             raise AttributeError("Unrecognized estimator!")

#         # check whether criteria is valid
#         if self.criteria == "neg_accuracy":
#             from My_AutoML._utils._stat import neg_accuracy

#             self.criteria = neg_accuracy
#         elif self.criteria == "MSE":
#             from sklearn.metrics import mean_squared_error

#             self.criteria = mean_squared_error
#         elif isinstance(self.criteria, Callable):
#             # if callable, pass
#             pass
#         else:
#             raise ValueError("Unrecognized criteria!")

#         # get all combinations of features
#         all_comb = []
#         for i in range(1, X.shape[1] + 1):
#             for item in list(combinations(list(range(X.shape[1])), i)):
#                 all_comb.append(list(item))
#         all_comb = np.array(all_comb).flatten()  # flatten 2D to 1D

#         # initialize results
#         results = []

#         for comb in all_comb:
#             self.estimator.fit(X.iloc[:, comb], y)
#             results.append(self.criteria(y, self.estimator.predict(X.iloc[:, comb])))

#         self.selected_features = all_comb[np.argmin(results)]

#         self._fitted = True

#         return self

#     def transform(self, X):

#         return X[:, self.selected_features]


class SFS:

    """
    Use Sequential Forward Selection/SFS to select subset of features.

    Parameters
    ----------
    estimators: str or estimator, default = "Lasso"
    string for some pre-defined estimator, or a estimator contains fit/predict methods

    n_components: int, default = None
    limit maximum number of features to select, if None, no limit

    n_prop: float, default = None
    proprotion of features to select, if None, no limit
    n_components have higher priority than n_prop

    criteria: str, default = "accuracy"
    criteria used to select features, can be "accuracy"
    """

    def __init__(
        self,
        estimator="Lasso",
        n_components=None,
        n_prop=None,
        criteria="neg_accuracy",
    ):
        self.estimator = estimator
        self.n_components = n_components
        self.n_prop = n_prop
        self.criteria = criteria

        self._fitted = False

    def select_feature(self, X, y, estimator, selected_features, unselected_features):

        # select one feature as step, get all possible combinations
        test_item = list(combinations(unselected_features, 1))
        # concat new test_comb with selected_features
        test_comb = [list(item) + selected_features for item in test_item]

        # initialize test results
        results = []
        for _comb in test_comb:
            # fit estimator
            estimator.fit(X.iloc[:, _comb], y)
            # get test results
            test_results = self.criteria(y, estimator.predict(X.iloc[:, _comb]))
            # append test results
            results.append(test_results)

        return (
            results[minloc(results)],
            test_item[minloc(results)][0],
        )  # use 0 to select item instead of tuple

    def fit(self, X, y=None):

        # check whether y is empty
        # for SFS, y is required to train a model
        if isinstance(y, pd.DataFrame):
            _empty = y.isnull().all().all()
        elif isinstance(y, pd.Series):
            _empty = y.isnull().all()
        elif isinstance(y, np.ndarray):
            _empty = np.all(np.isnan(y))
        else:
            _empty = y == None

        # if empty, raise error
        if _empty:
            raise ValueError("Must have response!")

        # make sure estimator is recognized
        estimator = get_estimator(self.estimator)

        # check whether n_components/n_prop is valid
        if self.n_components is None and self.n_prop is None:
            self.n_components = X.shape[1]
        elif self.n_components is not None:
            self.n_components = min(self.n_components, X.shape[1])
        # make sure selected features is at least 1
        elif self.n_prop is not None:
            self.n_components = max(1, int(self.n_prop * X.shape[1]))

        # check whether criteria is valid
        self.criteria = get_metrics(self.criteria)

        # initialize selected/unselected features
        selected_features = []
        optimal_loss = np.inf
        unselected_features = list(range(X.shape[1]))

        # iterate until n_components are selected
        for _ in range(self.n_components):
            # get the current optimal loss and feature
            loss, new_feature = self.select_feature(
                X, y, estimator, selected_features, unselected_features
            )
            if loss > optimal_loss:  # if no better combination is found, stop
                break
            else:
                optimal_loss = loss
                selected_features.append(new_feature)
                unselected_features.remove(new_feature)

        # record selected features
        self.selected_features = selected_features

        self._fitted = True

        return self

    def transform(self, X):

        return X.iloc[:, self.selected_features]


class mRMR:

    """
    mRMR [1] minimal-redundancy-maximal-relevance as criteria for filter-based
    feature selection

    [1] Peng, H., Long, F., & Ding, C. (2005). Feature selection based on mutual
    information criteria of max-dependency, max-relevance, and min-redundancy.
    IEEE Transactions on pattern analysis and machine intelligence, 27(8), 1226-1238.

    Parameters
    ----------
    n_components: int, default = None
    number of components to select, if None, no limit

    n_prop: float, default = None
    proprotion of features to select, if None, no limit
    n_components have higher priority than n_prop
    """

    def __init__(
        self,
        n_components=None,
        n_prop=None,
    ):
        self.n_components = n_components
        self.n_prop = n_prop

        self._fitted = False

    def select_feature(self, X, y, selected_features, unselected_features):

        # select one feature as step, get all possible combinations
        test_item = list(combinations(unselected_features, 1))

        # initialize test results
        results = []
        for _comb in test_item:
            dependency = MI(X.iloc[:, _comb[0]], y)
            if len(selected_features) > 0:
                redundancy = np.mean(
                    [
                        MI(X.iloc[:, item], X.iloc[:, _comb[0]])
                        for item in selected_features
                    ]
                )
                # append test results
                results.append(dependency - redundancy)
            # at initial, no selected feature, so no redundancy
            else:
                results.append(dependency)

        return test_item[maxloc(results)][0]  # use 0 to select item instead of tuple

    def fit(self, X, y=None):

        # check whether n_components/n_prop is valid
        if self.n_components is None and self.n_prop is None:
            self.n_components = X.shape[1]
        elif self.n_components is not None:
            self.n_components = min(self.n_components, X.shape[1])
        # make sure selected features is at least 1
        elif self.n_prop is not None:
            self.n_components = max(1, int(self.n_prop * X.shape[1]))

        # initialize selected/unselected features
        selected_features = []
        unselected_features = list(range(X.shape[1]))

        for _ in range(self.n_components):
            # get the current optimal loss and feature
            new_feature = self.select_feature(
                X, y, selected_features, unselected_features
            )
            selected_features.append(new_feature)
            unselected_features.remove(new_feature)

        # record selected features
        self.select_features = selected_features

        self._fitted = True

        return self

    def transform(self, X):

        return X.iloc[:, self.select_features]


class CBFS:

    """
    CBFS Copula-based Feature Selection [1]

    [1] Lall, S., Sinha, D., Ghosh, A., Sengupta, D., & Bandyopadhyay, S. (2021).
    Stable feature selection using copula based mutual information. Pattern Recognition,
    112, 107697.

    Parameters
    ----------
    copula: str, default = "empirical"
    what type of copula to use for feature selection

    n_components: int, default = None
    number of components to select, if None, no limit

    n_prop: float, default = None
    proprotion of features to select, if None, no limit
    n_components have higher priority than n_prop
    """

    def __init__(
        self,
        copula="empirical",
        n_components=None,
        n_prop=None,
    ):
        self.copula = copula
        self.n_components = n_components
        self.n_prop = n_prop

        self._fitted = False

    def Empirical_Copula(self, data):

        # make sure it's a dataframe
        if not isinstance(data, pd.DataFrame):
            try:
                data = pd.DataFrame(data)
            except:
                raise ValueError(
                    "data must be a pandas DataFrame or convertable to one!"
                )

        p = []
        for idx in data.index:
            p.append((data <= data.iloc[idx, :]).all(axis=1).sum() / data.shape[0])

        return p

    def select_feature(self, X, y, selected_features, unselected_features):

        # select one feature as step, get all possible combinations
        test_item = list(combinations(unselected_features, 1))
        # concat new test_comb with selected_features
        test_comb = [list(item) + selected_features for item in test_item]

        # initialize test results
        results = []
        for col, comb in zip(test_item, test_comb):
            # at initial, no selected feature, so no redundancy
            if len(selected_features) == 0:
                if self.copula == "empirical":
                    p_dependent = self.Empirical_Copula(
                        pd.concat([X.iloc[:, col[0]], y], axis=1)
                    )
                # calculate dependency based on empirical copula
                entropy_dependent = np.sum(
                    [-item * np.log2(item) for item in Counter(p_dependent).values()]
                )
                # append test results
                results.append(entropy_dependent)
            else:
                if self.copula == "empirical":
                    p_dependent = self.Empirical_Copula(
                        pd.concat([X.iloc[:, col[0]], y], axis=1)
                    )
                    p_redundant = self.Empirical_Copula(X.iloc[:, comb])

                # calculate dependency based on empirical copula
                entropy_dependent = np.sum(
                    [-item * np.log2(item) for item in Counter(p_dependent).values()]
                )
                # calculate redundancy based on empirical copula
                entropy_redundant = np.sum(
                    [-item * np.log2(item) for item in Counter(p_redundant).values()]
                )
                # append test results
                results.append(entropy_dependent - entropy_redundant)

        return (
            results[maxloc(results)],
            test_item[maxloc(results)][0],
        )  # use 0 to select item instead of tuple

    def fit(self, X, y=None):

        # check whether n_components/n_prop is valid
        if self.n_components is None and self.n_prop is None:
            self.n_components = X.shape[1]
        elif self.n_components is not None:
            self.n_components = min(self.n_components, X.shape[1])
        elif self.n_prop is not None:
            self.n_components = max(1, int(self.n_prop * X.shape[1]))

        # initialize selected/unselected features
        selected_features = []
        optimal_loss = -np.inf
        unselected_features = list(range(X.shape[1]))

        # iterate until n_components are selected
        for _ in range(self.n_components):
            # get the current optimal loss and feature
            loss, new_feature = self.select_feature(
                X, y, selected_features, unselected_features
            )
            if loss < optimal_loss:  # if no better combination is found, stop
                break
            else:
                optimal_loss = loss
                selected_features.append(new_feature)
                unselected_features.remove(new_feature)

        # record selected features
        self.selected_features = selected_features

        self._fitted = True

        return self

    def transform(self, X):

        return X.iloc[:, self.selected_features]
