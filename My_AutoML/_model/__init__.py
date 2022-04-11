"""
File: __init__.py
Author: Panyi Dong
GitHub: https://github.com/PanyiDong/
Mathematics Department, University of Illinois at Urbana-Champaign (UIUC)

Project: My_AutoML
Latest Version: 0.2.0
Relative Path: /My_AutoML/_model/__init__.py
File Created: Friday, 8th April 2022 9:04:05 pm
Author: Panyi Dong (panyid2@illinois.edu)

-----
Last Modified: Sunday, 10th April 2022 10:57:51 pm
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

import autosklearn.pipeline.components.classification
import autosklearn.pipeline.components.regression
from sklearn.linear_model import (
    LinearRegression,
    Lasso,
    Ridge,
    ElasticNet,
    BayesianRidge,
    LogisticRegression,
)
from sklearn.naive_bayes import ComplementNB

# need to enable hist gradient boosting features first
# no need for sklearn version >= 1.0.0
from sklearn.experimental import enable_hist_gradient_boosting
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)

####################################################################################################
# classifiers

classifiers = {
    # classification models from autosklearn
    "AdaboostClassifier": autosklearn.pipeline.components.classification.adaboost.AdaboostClassifier,
    "BernoulliNB": autosklearn.pipeline.components.classification.bernoulli_nb.BernoulliNB,
    "DecisionTree": autosklearn.pipeline.components.classification.decision_tree.DecisionTree,
    "ExtraTreesClassifier": autosklearn.pipeline.components.classification.extra_trees.ExtraTreesClassifier,
    "GaussianNB": autosklearn.pipeline.components.classification.gaussian_nb.GaussianNB,
    "GradientBoostingClassifier": autosklearn.pipeline.components.classification.gradient_boosting.GradientBoostingClassifier,
    "KNearestNeighborsClassifier": autosklearn.pipeline.components.classification.k_nearest_neighbors.KNearestNeighborsClassifier,
    "LDA": autosklearn.pipeline.components.classification.lda.LDA,
    "LibLinear_SVC": autosklearn.pipeline.components.classification.liblinear_svc.LibLinear_SVC,
    "LibSVM_SVC": autosklearn.pipeline.components.classification.libsvm_svc.LibSVM_SVC,
    "MLPClassifier": autosklearn.pipeline.components.classification.mlp.MLPClassifier,
    "MultinomialNB": autosklearn.pipeline.components.classification.multinomial_nb.MultinomialNB,
    "PassiveAggressive": autosklearn.pipeline.components.classification.passive_aggressive.PassiveAggressive,
    "QDA": autosklearn.pipeline.components.classification.qda.QDA,
    "RandomForest": autosklearn.pipeline.components.classification.random_forest.RandomForest,
    "SGD": autosklearn.pipeline.components.classification.sgd.SGD,
    # classification models from sklearn
    "LogisticRegression": LogisticRegression,
    # "ComplementNB": ComplementNB,
    "HistGradientBoostingClassifier": HistGradientBoostingClassifier,
    # self-defined models
}

# regressors
regressors = {
    # regression models from autosklearn
    "AdaboostRegressor": autosklearn.pipeline.components.regression.adaboost.AdaboostRegressor,
    "ARDRegression": autosklearn.pipeline.components.regression.ard_regression.ARDRegression,
    "DecisionTree": autosklearn.pipeline.components.regression.decision_tree.DecisionTree,
    "ExtraTreesRegressor": autosklearn.pipeline.components.regression.extra_trees.ExtraTreesRegressor,
    "GaussianProcess": autosklearn.pipeline.components.regression.gaussian_process.GaussianProcess,
    "GradientBoosting": autosklearn.pipeline.components.regression.gradient_boosting.GradientBoosting,
    "KNearestNeighborsRegressor": autosklearn.pipeline.components.regression.k_nearest_neighbors.KNearestNeighborsRegressor,
    "LibLinear_SVR": autosklearn.pipeline.components.regression.liblinear_svr.LibLinear_SVR,
    # "LibSVM_SVR": autosklearn.pipeline.components.regression.libsvm_svr.LibSVM_SVR,
    # "MLPRegressor": autosklearn.pipeline.components.regression.mlp.MLPRegressor,
    "RandomForest": autosklearn.pipeline.components.regression.random_forest.RandomForest,
    # "SGD": autosklearn.pipeline.components.regression.sgd.SGD,
    # regression models from sklearn
    "LinearRegression": LinearRegression,
    "Lasso": Lasso,
    "RidgeRegression": Ridge,
    "ElasticNet": ElasticNet,
    "BayesianRidge": BayesianRidge,
    # "HistGradientBoostingRegressor": HistGradientBoostingRegressor, # not well-supported by package conflicts
    # self-defined models
}


"""
LibSVM_SVR, MLP and SGD have problems of requiring inverse_transform 
of StandardScaler while having 1D array
https://github.com/automl/auto-sklearn/issues/1297
problem solved
"""

import importlib

torch_spec = importlib.util.find_spec("torch")
if torch_spec is not None:
    from ._FNN import MLP_Classifier, MLP_Regressor
    from ._RNN import RNN_Classifier

    classifiers["MLP_Classifier"] = MLP_Classifier
    #     classifiers["RNN_Classifier"] = RNN_Classifier

    regressors["MLP_Regressor"] = MLP_Regressor
