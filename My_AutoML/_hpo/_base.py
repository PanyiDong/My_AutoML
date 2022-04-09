"""
File: _base.py
Author: Panyi Dong
GitHub: https://github.com/PanyiDong/
Mathematics Department, University of Illinois at Urbana-Champaign (UIUC)

Project: My_AutoML
Latest Version: 0.2.0
Relative Path: /My_AutoML/_hpo/_base.py
File Created: Tuesday, 5th April 2022 10:49:30 pm
Author: Panyi Dong (panyid2@illinois.edu)

-----
Last Modified: Friday, 8th April 2022 10:21:42 pm
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

import ray
from ray import tune

import os
import shutil
import importlib
import warnings
import ast
import numpy as np
import pandas as pd
import scipy
from sklearn.utils._testing import ignore_warnings
from sklearn.exceptions import ConvergenceWarning

from My_AutoML._encoding import encoders
from My_AutoML._imputation import imputers
from My_AutoML._balancing import balancings
from My_AutoML._scaling import scalings
from My_AutoML._feature_selection import feature_selections
from My_AutoML._model import (
    classifiers,
    regressors,
)
from My_AutoML._hyperparameters import (
    encoder_hyperparameter,
    imputer_hyperparameter,
    scaling_hyperparameter,
    balancing_hyperparameter,
    feature_selection_hyperparameter,
    classifier_hyperparameter,
    regressor_hyperparameter,
)

from My_AutoML._base import no_processing
from My_AutoML._utils._file import save_model

# filter certain warnings
warnings.filterwarnings("ignore", message="The dataset is balanced, no change.")
warnings.filterwarnings("ignore", message="Variables are collinear")
warnings.filterwarnings("ignore", message="Function checkpointing is disabled")
warnings.filterwarnings(
    "ignore", message="The TensorboardX logger cannot be instantiated"
)
warnings.filterwarnings("ignore", category=UserWarning)
from typing import Callable

# check whether gpu device available
import importlib

torch_spec = importlib.util.find_spec("torch")
if torch_spec is None:
    import torch

    device_count = torch.cuda.device_count()
else:
    device_count = 0


class AutoTabularBase:

    """ "
    Base class module for AutoTabular (for classification and regression tasks)

    Parameters
    ----------
    task_mode: Mode of tasks, default: "classification"
    when called by AutoTabularClassification/AutoTabularRegression,
    task mode will be determined without reading data
    support ("classification", "regression")

    timeout: Total time limit for the job in seconds, default = 360

    max_evals: Maximum number of function evaluations allowed, default = 32

    allow_error_prop: proportion of tasks allows failure, default = 0.1
    allowed number of failures is int(max_evals * allow_error_prop)

    temp_directory: folder path to store temporary model, default = 'tmp'

    delete_temp_after_terminate: whether to delete temporary information, default = False

    save: whether to save model after training, default = True

    model_name: saved model name, default = 'model'

    ignore_warning: whether to ignore warning, default = True

    encoder: Encoders selected for the job, default = 'auto'
    support ('DataEncoding')
    'auto' will select all default encoders, or use a list to select

    imputer: Imputers selected for the job, default = 'auto'
    support ('SimpleImputer', 'JointImputer', 'ExpectationMaximization', 'KNNImputer',
    'MissForestImputer', 'MICE', 'GAIN')
    'auto' will select all default imputers, or use a list to select

    balancing: Balancings selected for the job, default = 'auto'
    support ('no_processing', 'SimpleRandomOverSampling', 'SimpleRandomUnderSampling',
    'TomekLink', 'EditedNearestNeighbor', 'CondensedNearestNeighbor', 'OneSidedSelection',
    'CNN_TomekLink', 'Smote', 'Smote_TomekLink', 'Smote_ENN')
    'auto' will select all default balancings, or use a list to select

    scaling: Scalings selected for the job, default = 'auto'
    support ('no_processing', 'MinMaxScale', 'Standardize', 'Normalize', 'RobustScale',
    'PowerTransformer', 'QuantileTransformer', 'Winsorization')
    'auto' will select all default scalings, or use a list to select

    feature_selection: Feature selections selected for the job, default = 'auto'
    support ('no_processing', 'LDASelection', 'PCA_FeatureSelection', 'RBFSampler',
    'FeatureFilter', 'ASFFS', 'GeneticAlgorithm', 'extra_trees_preproc_for_classification',
    'fast_ica', 'feature_agglomeration', 'kernel_pca', 'kitchen_sinks',
    'liblinear_svc_preprocessor', 'nystroem_sampler', 'pca', 'polynomial',
    'random_trees_embedding', 'select_percentile_classification','select_rates_classification',
    'truncatedSVD')
    'auto' will select all default feature selections, or use a list to select

    models: Models selected for the job, default = 'auto'
    support classifiers ('AdaboostClassifier', 'BernoulliNB', 'DecisionTree',
            'ExtraTreesClassifier', 'GaussianNB', 'GradientBoostingClassifier',
            'KNearestNeighborsClassifier', 'LDA', 'LibLinear_SVC', 'LibSVM_SVC',
            'MLPClassifier', 'MultinomialNB','PassiveAggressive', 'QDA',
            'RandomForest',  'SGD')
    support regressors ("AdaboostRegressor", "ARDRegression", "DecisionTree",
            "ExtraTreesRegressor", "GaussianProcess", "GradientBoosting",
            "KNearestNeighborsRegressor", "LibLinear_SVR", "LibSVM_SVR",
            "MLPRegressor", "RandomForest", "SGD")
    'auto' will select all default models, or use a list to select

    validation: Whether to use train_test_split to test performance on test set, default = True

    valid_size: Test percentage used to evaluate the performance, default = 0.15
    only effective when validation = True

    objective: Objective function to test performance, default = 'accuracy'
    support metrics for regression ("MSE", "MAE", "MSLE", "R2", "MAX")
    support metrics for classification ("accuracy", "precision", "auc", "hinge", "f1")

    search_algo: search algorithm used for hyperparameter optimization, deafult = "HyperOpt"
    support ("RandomSearch", "GridSearch", "BayesOptSearch", "AxSearch", "BOHB",
            "BlendSearch", "CFO", "DragonflySearch", "HEBO", "HyperOpt", "Nevergrad",
            "Optuna", "SigOpt", "Scikit-Optimize", "ZOOpt", "Reapter",
            "ConcurrencyLimiter", callable)

    search_algo_setttings: search algorithm settings, default = {}
    need manual configuration for each search algorithm

    search_scheduler: search scheduler used, default = "FIFOScheduler"
    support ("FIFOScheduler", "ASHAScheduler", "HyperBandScheduler", "MedianStoppingRule"
            "PopulationBasedTraining", "PopulationBasedTrainingReplay", "PB2",
            "HyperBandForBOHB", callable)

    search_scheduler_settings: search scheduler settings, default = {}
    need manual configuration for each search scheduler

    progress_reporter: progress reporter, default = "CLIReporter"
    support ("CLIReporter", "JupyterNotebookReporter")

    full_status: whether to print full status, default = False

    verbose: display for output, default = 1
    support (0, 1, 2, 3)

    cpu_threads: number of cpu threads to use, default = None
    if None, get all available cpu threads

    use_gpu: whether to use gpu, default = False

    seed: random seed, default = 1
    """

    def __init__(
        self,
        task_mode="classification",
        timeout=360,
        max_evals=64,
        allow_error_prop=0.1,
        temp_directory="tmp",
        delete_temp_after_terminate=False,
        save=True,
        model_name="model",
        ignore_warning=True,
        encoder="auto",
        imputer="auto",
        balancing="auto",
        scaling="auto",
        feature_selection="auto",
        models="auto",
        validation=True,
        valid_size=0.15,
        objective="accuracy",
        search_algo="HyperOpt",
        search_algo_setttings={},
        search_scheduler="FIFOScheduler",
        search_scheduler_settings={},
        progress_reporter="CLIReporter",
        full_status=False,
        verbose=1,
        cpu_threads=None,
        use_gpu=False,
        seed=1,
    ):
        self.task_mode = task_mode
        self.timeout = timeout
        self.max_evals = max_evals
        self.allow_error_prop = allow_error_prop
        self.temp_directory = temp_directory
        self.delete_temp_after_terminate = delete_temp_after_terminate
        self.save = save
        self.model_name = model_name
        self.ignore_warning = ignore_warning
        self.encoder = encoder
        self.imputer = imputer
        self.balancing = balancing
        self.scaling = scaling
        self.feature_selection = feature_selection
        self.models = models
        self.validation = validation
        self.valid_size = valid_size
        self.objective = objective
        self.search_algo = search_algo
        self.search_algo_setttings = search_algo_setttings
        self.search_scheduler = search_scheduler
        self.search_scheduler_settings = search_scheduler_settings
        self.progress_reporter = progress_reporter
        self.full_status = full_status
        self.verbose = verbose
        self.cpu_threads = cpu_threads
        self.use_gpu = use_gpu
        self.seed = seed

        self._iter = 0  # record iteration number

    # create hyperparameter space using ray.tune.choice
    # the pipeline of AutoClassifier is [encoder, imputer, scaling, balancing, feature_selection, model]
    # only chosen ones will be added to hyperparameter space
    def _get_hyperparameter_space(
        self,
        X,
        encoders_hyperparameters,
        encoder,
        imputers_hyperparameters,
        imputer,
        balancings_hyperparameters,
        balancing,
        scalings_hyperparameters,
        scaling,
        feature_selection_hyperparameters,
        feature_selection,
        models_hyperparameters,
        models,
    ):

        # encoding space
        _encoding_hyperparameter = []
        for _encoder in [*encoder]:
            for (
                item
            ) in encoders_hyperparameters:  # search the encoders' hyperparameters
                # find encoder key
                for _key in item.keys():
                    if "encoder_" in _key:
                        _encoder_key = _key
                        break
                if item[_encoder_key] == _encoder:
                    # convert string to tune.choice
                    item[_encoder_key] = tune.choice([item[_encoder_key]])
                    _encoding_hyperparameter.append(item)
        _encoding_hyperparameter = tune.choice(_encoding_hyperparameter)

        # imputation space
        _imputer_hyperparameter = []
        if not X.isnull().values.any():  # if no missing, no need for imputation
            _imputer_hyperparameter = tune.choice(
                [{"imputer_0": tune.choice(["no_processing"])}]
            )
        else:
            for _imputer in [*imputer]:
                for (
                    item
                ) in imputers_hyperparameters:  # search the imputer' hyperparameters
                    # find imputer key
                    for _key in item.keys():
                        if "imputer_" in _key:
                            _imputer_key = _key
                            break
                    if item[_imputer_key] == _imputer:
                        # convert string to tune.choice
                        item[_imputer_key] = tune.choice([item[_imputer_key]])
                        _imputer_hyperparameter.append(item)

            _imputer_hyperparameter = tune.choice(_imputer_hyperparameter)

        # balancing space
        _balancing_hyperparameter = []
        for _balancing in [*balancing]:
            for (
                item
            ) in balancings_hyperparameters:  # search the balancings' hyperparameters
                # find balancing key
                for _key in item.keys():
                    if "balancing_" in _key:
                        _balancing_key = _key
                        break
                if item[_balancing_key] == _balancing:
                    # convert string to tune.choice
                    item[_balancing_key] = tune.choice([item[_balancing_key]])
                    _balancing_hyperparameter.append(item)

        _balancing_hyperparameter = tune.choice(_balancing_hyperparameter)

        # scaling space
        _scaling_hyperparameter = []
        for _scaling in [*scaling]:
            for (
                item
            ) in scalings_hyperparameters:  # search the scalings' hyperparameters
                # find scaling key
                for _key in item.keys():
                    if "scaling_" in _key:
                        _scaling_key = _key
                        break
                if item[_scaling_key] == _scaling:
                    # convert string to tune.choice
                    item[_scaling_key] = tune.choice([item[_scaling_key]])
                    _scaling_hyperparameter.append(item)

        _scaling_hyperparameter = tune.choice(_scaling_hyperparameter)

        # feature selection space
        _feature_selection_hyperparameter = []
        for _feature_selection in [*feature_selection]:
            for (
                item
            ) in (
                feature_selection_hyperparameters
            ):  # search the feature selections' hyperparameters
                # find feature_selection key
                for _key in item.keys():
                    if "feature_selection_" in _key:
                        _feature_selection_key = _key
                        break
                if item[_feature_selection_key] == _feature_selection:
                    # convert string to tune.choice
                    item[_feature_selection_key] = tune.choice(
                        [item[_feature_selection_key]]
                    )
                    _feature_selection_hyperparameter.append(item)

        _feature_selection_hyperparameter = tune.choice(
            _feature_selection_hyperparameter
        )

        # model selection and hyperparameter optimization space
        _model_hyperparameter = []
        for _model in [*models]:
            # checked before at models that all models are in default space
            for item in models_hyperparameters:  # search the models' hyperparameters
                # find model key
                for _key in item.keys():
                    if "model_" in _key:
                        _model_key = _key
                        break
                if item[_model_key] == _model:
                    # convert string to tune.choice
                    item[_model_key] = tune.choice([item[_model_key]])
                    _model_hyperparameter.append(item)

        _model_hyperparameter = tune.choice(_model_hyperparameter)

        # the pipeline search space
        # select one of the method/hyperparameter setting from each part
        return {
            "task_type": "tabular_" + self.task_mode,
            "encoder": _encoding_hyperparameter,
            "imputer": _imputer_hyperparameter,
            "balancing": _balancing_hyperparameter,
            "scaling": _scaling_hyperparameter,
            "feature_selection": _feature_selection_hyperparameter,
            "model": _model_hyperparameter,
        }

    def get_hyperparameter_space(self, X, y):

        # initialize default search options
        # and select the search options based on the input restrictions
        # use copy to allows multiple manipulation

        # Encoding: convert string types to numerical type
        # all encoders available
        self._all_encoders = encoders.copy()

        # get default encoder methods space
        if self.encoder == "auto":
            encoder = self._all_encoders.copy()
        else:
            encoder = {}  # if specified, check if encoders in default encoders
            for _encoder in self.encoder:
                if _encoder not in [*self._all_encoders]:
                    raise ValueError(
                        "Only supported encoders are {}, get {}.".format(
                            [*self._all_encoders], _encoder
                        )
                    )
                encoder[_encoder] = self._all_encoders[_encoder]

        # all hyperparameters for encoders
        self._all_encoders_hyperparameters = encoder_hyperparameter.copy()

        # initialize encoders hyperparameter space
        _all_encoders_hyperparameters = self._all_encoders_hyperparameters.copy()

        # Imputer: fill missing values
        # all imputers available
        self._all_imputers = imputers.copy()

        # get default imputer methods space
        if self.imputer == "auto":
            if not X.isnull().values.any():  # if no missing values
                imputer = {"no_processing": no_processing}
                self._all_imputers = imputer  # limit default imputer space
            else:
                imputer = self._all_imputers.copy()
        else:
            if not X.isnull().values.any():  # if no missing values
                imputer = {"no_processing": no_processing}
                self._all_imputers = imputer
            else:
                imputer = {}  # if specified, check if imputers in default imputers
                for _imputer in self.imputer:
                    if _imputer not in [*self._all_imputers]:
                        raise ValueError(
                            "Only supported imputers are {}, get {}.".format(
                                [*self._all_imputers], _imputer
                            )
                        )
                    imputer[_imputer] = self._all_imputers[_imputer]

        # all hyperparemeters for imputers
        self._all_imputers_hyperparameters = imputer_hyperparameter.copy()

        # initialize imputers hyperparameter space
        _all_imputers_hyperparameters = self._all_imputers_hyperparameters.copy()

        # Balancing: deal with imbalanced dataset, using over-/under-sampling methods
        # all balancings available
        self._all_balancings = balancings.copy()

        # get default balancing methods space
        if self.balancing == "auto":
            balancing = self._all_balancings.copy()
        else:
            balancing = {}  # if specified, check if balancings in default balancings
            for _balancing in self.balancing:
                if _balancing not in [*self._all_balancings]:
                    raise ValueError(
                        "Only supported balancings are {}, get {}.".format(
                            [*self._all_balancings], _balancing
                        )
                    )
                balancing[_balancing] = self._all_balancings[_balancing]

        # all hyperparameters for balancing methods
        self._all_balancings_hyperparameters = balancing_hyperparameter.copy()

        # initialize balancing hyperparameter space
        _all_balancings_hyperparameters = self._all_balancings_hyperparameters.copy()

        # Scaling
        # all scalings available
        self._all_scalings = scalings.copy()

        # get default scaling methods space
        if self.scaling == "auto":
            scaling = self._all_scalings.copy()
        else:
            scaling = {}  # if specified, check if scalings in default scalings
            for _scaling in self.scaling:
                if _scaling not in [*self._all_scalings]:
                    raise ValueError(
                        "Only supported scalings are {}, get {}.".format(
                            [*self._all_scalings], _scaling
                        )
                    )
                scaling[_scaling] = self._all_scalings[_scaling]

        # all hyperparameters for scalings
        self._all_scalings_hyperparameters = scaling_hyperparameter.copy()

        # initialize scaling hyperparameter space
        _all_scalings_hyperparameters = self._all_scalings_hyperparameters.copy()

        # Feature selection: Remove redundant features, reduce dimensionality
        # all feature selections available
        self._all_feature_selection = feature_selections.copy()
        if self.task_mode == "classification":
            # special treatment, if classification
            # remove some feature selection for regression
            del self._all_feature_selection["extra_trees_preproc_for_regression"]
            del self._all_feature_selection["select_percentile_regression"]
            del self._all_feature_selection["select_rates_regression"]
        elif self.task_mode == "regression":
            # special treatment, if regression
            # remove some feature selection for classification
            del self._all_feature_selection["extra_trees_preproc_for_classification"]
            del self._all_feature_selection["select_percentile_classification"]
            del self._all_feature_selection["select_rates_classification"]

        if X.shape[0] * X.shape[1] > 10000:
            del self._all_feature_selection["liblinear_svc_preprocessor"]

        # get default feature selection methods space
        if self.feature_selection == "auto":
            feature_selection = self._all_feature_selection.copy()
        else:
            feature_selection = (
                {}
            )  # if specified, check if balancings in default balancings
            for _feature_selection in self.feature_selection:
                if _feature_selection not in [*self._all_feature_selection]:
                    raise ValueError(
                        "Only supported feature selections are {}, get {}.".format(
                            [*self._all_feature_selection], _feature_selection
                        )
                    )
                feature_selection[_feature_selection] = self._all_feature_selection[
                    _feature_selection
                ]

        # all hyperparameters for feature selections
        self._all_feature_selection_hyperparameters = (
            feature_selection_hyperparameter.copy()
        )

        # initialize feature selection hyperparameter space
        _all_feature_selection_hyperparameters = (
            self._all_feature_selection_hyperparameters.copy()
        )

        # Model selection/Hyperparameter optimization
        # using Bayesian Optimization
        # all models available
        # if mode is classification, use classification models
        # if mode is regression, use regression models
        if self.task_mode == "classification":
            self._all_models = classifiers.copy()
        elif self.task_mode == "regression":
            self._all_models = regressors.copy()

        # special treatment, remove SVM methods when observations are large
        # SVM suffers from the complexity o(n_samples^2 * n_features),
        # which is time-consuming for large datasets
        if X.shape[0] * X.shape[1] > 10000:
            # in case the methods are not included, will check before delete
            if self.task_mode == "classification":
                del self._all_models["LibLinear_SVC"]
                del self._all_models["LibSVM_SVC"]
            elif self.task_mode == "regression":
                del self._all_models["LibLinear_SVR"]
                del self._all_models["LibSVM_SVR"]

        # model space, only select chosen models to space
        if self.models == "auto":  # if auto, model pool will be all default models
            models = self._all_models.copy()
        else:
            models = {}  # if specified, check if models in default models
            for _model in self.models:
                if _model not in [*self._all_models]:
                    raise ValueError(
                        "Only supported models are {}, get {}.".format(
                            [*self._all_models], _model
                        )
                    )
                models[_model] = self._all_models[_model]

        # all hyperparameters for the models by mode
        if self.task_mode == "classification":
            self._all_models_hyperparameters = classifier_hyperparameter.copy()
        elif self.task_mode == "regression":
            self._all_models_hyperparameters = regressor_hyperparameter.copy()

        # initialize model hyperparameter space
        _all_models_hyperparameters = self._all_models_hyperparameters.copy()

        # initialize default search space
        self.hyperparameter_space = None

        # generate the hyperparameter space
        if self.hyperparameter_space is None:
            self.hyperparameter_space = self._get_hyperparameter_space(
                X,
                _all_encoders_hyperparameters,
                encoder,
                _all_imputers_hyperparameters,
                imputer,
                _all_balancings_hyperparameters,
                balancing,
                _all_scalings_hyperparameters,
                scaling,
                _all_feature_selection_hyperparameters,
                feature_selection,
                _all_models_hyperparameters,
                models,
            )  # _X to choose whether include imputer
            # others are the combinations of default hyperparameter space & methods selected

        return encoder, imputer, balancing, scaling, feature_selection, models

    # get the hyperparameter optimization algorithm
    def get_algo(self):

        if self.search_algo == "RandomSearch" or self.search_algo == "GridSearch":

            # Random Search and Grid Search
            from ray.tune.suggest.basic_variant import BasicVariantGenerator

            algo = BasicVariantGenerator
        elif self.search_algo == "BayesOptSearch":

            # check whether bayes_opt is installed
            bayes_opt_spec = importlib.util.find_spec("bayes_opt")
            if bayes_opt_spec is None:
                raise ImportError(
                    "BayesOpt is not installed. Please install it first to use BayesOptSearch. \
                    Command to install: pip install bayesian-optimization"
                )

            # Bayesian Search
            from ray.tune.suggest.bayesopt import BayesOptSearch

            algo = BayesOptSearch
        elif self.search_algo == "AxSearch":

            # check whether Ax and sqlalchemy are installed
            Ax_spec = importlib.util.find_spec("ax")
            sqlalchemy_spec = importlib.util.find_spec("sqlalchemy")
            if Ax_spec is None or sqlalchemy_spec is None:
                raise ImportError(
                    "Ax or sqlalchemy not installed. Please install these packages to use AxSearch. \
                    Command to install: pip install ax-platform sqlalchemy"
                )

            # Ax Search
            from ray.tune.suggest.ax import AxSearch

            algo = AxSearch
        elif self.search_algo == "BOHB":

            # check whether HpBandSter and ConfigSpace are installed
            hpbandster_spec = importlib.util.find_spec("hpbandster")
            ConfigSpace_spec = importlib.util.find_spec("ConfigSpace")
            if hpbandster_spec is None or ConfigSpace_spec is None:
                raise ImportError(
                    "HpBandSter or ConfigSpace not installed. Please install these packages to use BOHB. \
                    Command to install: pip install hpbandster ConfigSpace"
                )

            # Bayesian Optimization HyperBand/BOHB
            from ray.tune.suggest.bohb import TuneBOHB

            algo = TuneBOHB
        elif self.search_algo == "BlendSearch":

            # check whether flaml is installed
            flaml_spec = importlib.util.find_spec("flaml")
            if flaml_spec is None:
                raise ImportError(
                    "flaml not installed. Please install it first to use BlendSearch. \
                    Command to install: pip install 'flaml[blendsearch]'"
                )

            # Blend Search
            from ray.tune.suggest.flaml import BlendSearch

            algo = BlendSearch
        elif self.search_algo == "CFO":

            # check whether flaml is installed
            flaml_spec = importlib.util.find_spec("flaml")
            if flaml_spec is None:
                raise ImportError(
                    "flaml not installed. Please install it first to use BlendSearch. \
                    Command to install: pip install 'flaml[blendsearch]'"
                )

            # Blend Search
            from ray.tune.suggest.flaml import CFO

            algo = CFO
        elif self.search_algo == "DragonflySearch":

            # check whether dragonfly-opt is installed
            dragonfly_spec = importlib.util.find_spec("dragonfly")
            if dragonfly_spec is None:
                raise ImportError(
                    "dragonfly-opt not installed. Please install it first to use DragonflySearch. \
                    Command to install: pip install dragonfly-opt"
                )

            # Dragonfly Search
            from ray.tune.suggest.dragonfly import DragonflySearch

            algo = DragonflySearch
        elif self.search_algo == "HEBO":

            # Heteroscedastic Evolutionary Bayesian Optimization/HEBO
            from ray.tune.suggest.hebo import HEBOSearch

            algo = HEBOSearch
        elif self.search_algo == "HyperOpt":

            # check whether hyperopt is installed
            hyperopt_spec = importlib.util.find_spec("hyperopt")
            if hyperopt_spec is None:
                raise ImportError(
                    "hyperopt not installed. Please install it first to use HyperOpt. \
                    Command to install: pip install -U hyperopt"
                )

            # HyperOpt Search
            from ray.tune.suggest.hyperopt import HyperOptSearch

            algo = HyperOptSearch
        elif self.search_algo == "Nevergrad":

            # check whether nevergrad is installed
            nevergrad_spec = importlib.util.find_spec("nevergrad")
            if nevergrad_spec is None:
                raise ImportError(
                    "nevergrad not installed. Please install it first to use Nevergrad. \
                    Command to install: pip install nevergrad"
                )

            # Nevergrad Search
            from ray.tune.suggest.nevergrad import NevergradSearch

            algo = NevergradSearch
        elif self.search_algo == "Optuna":

            # check whether optuna is installed
            optuna_spec = importlib.util.find_spec("optuna")
            if optuna_spec is None:
                raise ImportError(
                    "optuna not installed. Please install it first to use Optuna. \
                    Command to install: pip install optuna"
                )

            # Optuna Search
            from ray.tune.suggest.optuna import OptunaSearch

            algo = OptunaSearch
        elif self.search_algo == "SigOpt":

            # check whether sigopt is installed
            sigopt_spec = importlib.util.find_spec("sigopt")
            if sigopt_spec is None:
                raise ImportError(
                    "sigopt not installed. Please install it first to use SigOpt. \
                    Command to install: pip install sigopt \
                    Set SigOpt API: export SIGOPT_KEY= ..."
                )

            # SigOpt Search
            from ray.tune.suggest.sigopt import SigOptSearch

            algo = SigOptSearch
        elif self.search_algo == "Scikit-Optimize":

            # check whether scikit-optimize is installed
            skopt_spec = importlib.util.find_spec("skopt")
            if skopt_spec is None:
                raise ImportError(
                    "scikit-optimize not installed. Please install it first to use Scikit-Optimize. \
                    Command to install: pip install scikit-optimize"
                )

            # Scikit-Optimize Search
            from ray.tune.suggest.skopt import SkOptSearch

            algo = SkOptSearch
        elif self.search_algo == "ZOOpt":

            # check whether zoopt is installed
            zoopt_spec = importlib.util.find_spec("zoopt")
            if zoopt_spec is None:
                raise ImportError(
                    "zoopt not installed. Please install it first to use ZOOpt. \
                    Command to install: pip install zoopt"
                )

            # ZOOpt Search
            from ray.tune.suggest.zoopt import ZOOptSearch

            algo = ZOOptSearch
        elif self.search_algo == "Repeater":

            # Repeated Evaluations
            from ray.tune.suggest import Repeater

            algo = Repeater
        elif self.search_algo == "ConcurrencyLimiter":

            # ConcurrencyLimiter
            from ray.tune.suggest import ConcurrencyLimiter

            algo = ConcurrencyLimiter
        else:

            # if none above, assume is a callable custom algorithm
            if isinstance(self.search_algo, Callable):
                algo = self.search_algo
            # if not callable, raise error
            else:
                raise TypeError(
                    "Algorithm {} is not supported. Please use one of the supported algorithms.".format(
                        self.search_algo
                    )
                )

        return algo

    # get search scheduler
    def get_scheduler(self):

        if self.search_scheduler == "FIFOScheduler":

            from ray.tune.schedulers import FIFOScheduler

            scheduler = FIFOScheduler
        elif self.search_scheduler == "ASHAScheduler":

            from ray.tune.schedulers import ASHAScheduler

            scheduler = ASHAScheduler
        elif self.search_scheduler == "HyperBandScheduler":

            from ray.tune.schedulers import HyperBandScheduler

            scheduler = HyperBandScheduler
        elif self.search_scheduler == "MedianStoppingRule":

            from ray.tune.schedulers import MedianStoppingRule

            scheduler = MedianStoppingRule
        elif self.search_scheduler == "PopulationBasedTraining":

            from ray.tune.schedulers import PopulationBasedTraining

            scheduler = PopulationBasedTraining
        elif self.search_scheduler == "PopulationBasedTrainingReplay":

            from ray.tune.schedulers import PopulationBasedTrainingReplay

            scheduler = PopulationBasedTrainingReplay
        elif self.search_scheduler == "PB2":

            # check whether GPy2 is installed
            Gpy_spec = importlib.util.find_spec("GPy")
            if Gpy_spec is None:
                raise ImportError(
                    "GPy2 not installed. Please install it first to use PB2. \
                    Command to install: pip install GPy"
                )

            from ray.tune.schedulers.pb2 import PB2

            scheduler = PB2
        elif self.search_scheduler == "HyperBandForBOHB":

            from ray.tune.schedulers import HyperBandForBOHB

            scheduler = HyperBandForBOHB
        else:

            # if callable, use it as scheduler
            if isinstance(self.search_scheduler, Callable):
                scheduler = self.search_scheduler
            else:
                raise TypeError(
                    "Scheduler {} is not supported. Please use one of the supported schedulers.".format(
                        self.search_scheduler
                    )
                )

        return scheduler

    # get progress reporter
    def get_progress_reporter(self):

        if self.progress_reporter == "CLIReporter":

            from ray.tune.progress_reporter import CLIReporter

            progress_reporter = CLIReporter(
                # metric_columns=[
                #     "fitted_model",
                #     "training_status",
                #     "total time (s)",
                #     "iter",
                #     "loss",
                # ],
                parameter_columns=["task_type"],
                max_progress_rows=self.max_evals,
                max_error_rows=self.max_error,
                sort_by_metric=True,
            )
        elif self.progress_reporter == "JupyterNotebookReporter":

            from ray.tune.progress_reporter import JupyterNotebookReporter

            progress_reporter = JupyterNotebookReporter(
                overwrite=True,
                # metric_columns=[
                #     "fitted_model",
                #     "training_status",
                #     "total time (s)",
                #     "iter",
                #     "loss",
                # ],
                parameter_columns=["task_type"],
                max_progress_rows=self.max_evals,
                max_error_rows=self.max_error,
                sort_by_metric=True,
            )

        # add metrics for visualization
        progress_reporter.add_metric_column("fitted_model")
        progress_reporter.add_metric_column("training_status")
        progress_reporter.add_metric_column("loss")

        return progress_reporter

    # load hyperparameter settings and train on the data
    def load_model(self, _X, _y):

        # load hyperparameter settings
        with open(self.model_name) as f:
            optimal_setting = f.readlines()

        # remove change line signs
        optimal_setting = [item.replace("\n", "") for item in optimal_setting]
        # remove blank spaces
        while "" in optimal_setting:
            optimal_setting.remove("")

        # convert strings to readable dictionaries
        self.optimal_encoder = optimal_setting[0]
        self.optimal_encoder_hyperparameters = ast.literal_eval(optimal_setting[1])
        self.optimal_imputer = optimal_setting[2]
        self.optimal_imputer_hyperparameters = ast.literal_eval(optimal_setting[3])
        self.optimal_balancing = optimal_setting[4]
        self.optimal_balancing_hyperparameters = ast.literal_eval(optimal_setting[5])
        self.optimal_scaling = optimal_setting[6]
        self.optimal_scaling_hyperparameters = ast.literal_eval(optimal_setting[7])
        self.optimal_feature_selection = optimal_setting[8]
        self.optimal_feature_selection_hyperparameters = ast.literal_eval(
            optimal_setting[9]
        )
        self.optimal_model = optimal_setting[10]
        self.optimal_model_hyperparameters = ast.literal_eval(optimal_setting[11])

        # map the methods and hyperparameters
        # fit the methods
        # encoding
        self._fit_encoder = self._all_encoders[self.optimal_encoder](
            **self.optimal_encoder_hyperparameters
        )
        _X = self._fit_encoder.fit(_X)
        # imputer
        self._fit_imputer = self._all_imputers[self.optimal_imputer](
            **self.optimal_imputer_hyperparameters
        )
        _X = self._fit_imputer.fill(_X)
        # balancing
        self._fit_balancing = self._all_balancings[self.optimal_balancing](
            **self.optimal_balancing_hyperparameters
        )
        _X, _y = self._fit_balancing.fit_transform(_X, _y)

        # make sure the classes are integers (belongs to certain classes)
        if self.task_mode == "classification":
            _y = _y.astype(int)
        # scaling
        self._fit_scaling = self._all_scalings[self.optimal_scaling](
            **self.optimal_scaling_hyperparameters
        )
        self._fit_scaling.fit(_X, _y)
        _X = self._fit_scaling.transform(_X)
        # feature selection
        self._fit_feature_selection = self._all_feature_selection[
            self.optimal_feature_selection
        ](**self.optimal_feature_selection_hyperparameters)
        self._fit_feature_selection.fit(_X, _y)
        _X = self._fit_feature_selection.transform(_X)
        # model
        self._fit_model = self._all_models[self.optimal_model](
            **self.optimal_model_hyperparameters
        )
        self._fit_model.fit(_X, _y.values.ravel())

        return self

    # select optimal settings and fit on optimal hyperparameters
    def _fit_optimal(self, optimal_point, _X, _y):

        # optimal encoder
        self.optimal_encoder_hyperparameters = optimal_point["encoder"]
        # find optimal encoder key
        for _key in self.optimal_encoder_hyperparameters.keys():
            if "encoder_" in _key:
                _encoder_key = _key
                break
        self.optimal_encoder = self.optimal_encoder_hyperparameters[_encoder_key]
        del self.optimal_encoder_hyperparameters[_encoder_key]
        # remvoe indcations
        self.optimal_encoder_hyperparameters = {
            k.replace(
                self.optimal_encoder + "_", ""
            ): self.optimal_encoder_hyperparameters[k]
            for k in self.optimal_encoder_hyperparameters
        }

        # optimal imputer
        self.optimal_imputer_hyperparameters = optimal_point["imputer"]
        # find optimal imputer key
        for _key in self.optimal_imputer_hyperparameters.keys():
            if "imputer_" in _key:
                _imputer_key = _key
                break
        self.optimal_imputer = self.optimal_imputer_hyperparameters[_imputer_key]
        del self.optimal_imputer_hyperparameters[_imputer_key]
        # remvoe indcations
        self.optimal_imputer_hyperparameters = {
            k.replace(
                self.optimal_imputer + "_", ""
            ): self.optimal_imputer_hyperparameters[k]
            for k in self.optimal_imputer_hyperparameters
        }

        # optimal balancing
        self.optimal_balancing_hyperparameters = optimal_point["balancing"]
        # find optimal balancing key
        for _key in self.optimal_balancing_hyperparameters.keys():
            if "balancing_" in _key:
                _balancing_key = _key
                break
        self.optimal_balancing = self.optimal_balancing_hyperparameters[_balancing_key]
        del self.optimal_balancing_hyperparameters[_balancing_key]
        # remvoe indcations
        self.optimal_balancing_hyperparameters = {
            k.replace(
                self.optimal_balancing + "_", ""
            ): self.optimal_balancing_hyperparameters[k]
            for k in self.optimal_balancing_hyperparameters
        }

        # optimal scaling
        self.optimal_scaling_hyperparameters = optimal_point["scaling"]
        # find optimal scaling key
        for _key in self.optimal_scaling_hyperparameters.keys():
            if "scaling_" in _key:
                _scaling_key = _key
                break
        self.optimal_scaling = self.optimal_scaling_hyperparameters[_scaling_key]
        del self.optimal_scaling_hyperparameters[_scaling_key]
        # remvoe indcations
        self.optimal_scaling_hyperparameters = {
            k.replace(
                self.optimal_scaling + "_", ""
            ): self.optimal_scaling_hyperparameters[k]
            for k in self.optimal_scaling_hyperparameters
        }

        # optimal feature selection
        self.optimal_feature_selection_hyperparameters = optimal_point[
            "feature_selection"
        ]
        # find optimal feature_selection key
        for _key in self.optimal_feature_selection_hyperparameters.keys():
            if "feature_selection_" in _key:
                _feature_selection_key = _key
                break
        self.optimal_feature_selection = self.optimal_feature_selection_hyperparameters[
            _feature_selection_key
        ]
        del self.optimal_feature_selection_hyperparameters[_feature_selection_key]
        # remvoe indcations
        self.optimal_feature_selection_hyperparameters = {
            k.replace(
                self.optimal_feature_selection + "_", ""
            ): self.optimal_feature_selection_hyperparameters[k]
            for k in self.optimal_feature_selection_hyperparameters
        }

        # optimal classifier
        self.optimal_model_hyperparameters = optimal_point[
            "model"
        ]  # optimal model selected
        # find optimal model key
        for _key in self.optimal_model_hyperparameters.keys():
            if "model_" in _key:
                _model_key = _key
                break
        self.optimal_model = self.optimal_model_hyperparameters[
            _model_key
        ]  # optimal hyperparameter settings selected
        del self.optimal_model_hyperparameters[_model_key]
        # remvoe indcations
        self.optimal_model_hyperparameters = {
            k.replace(self.optimal_model + "_", ""): self.optimal_model_hyperparameters[
                k
            ]
            for k in self.optimal_model_hyperparameters
        }

        # record optimal settings
        with open(
            os.path.join(self.temp_directory, self.model_name, "optimal_setting.txt"),
            "w",
        ) as f:
            f.write("Optimal encoding method is: {}\n".format(self.optimal_encoder))
            f.write("Optimal encoding hyperparameters:")
            print(self.optimal_encoder_hyperparameters, file=f, end="\n\n")
            f.write("Optimal imputation method is: {}\n".format(self.optimal_imputer))
            f.write("Optimal imputation hyperparameters:")
            print(self.optimal_imputer_hyperparameters, file=f, end="\n\n")
            f.write("Optimal balancing method is: {}\n".format(self.optimal_balancing))
            f.write("Optimal balancing hyperparamters:")
            print(self.optimal_balancing_hyperparameters, file=f, end="\n\n")
            f.write("Optimal scaling method is: {}\n".format(self.optimal_scaling))
            f.write("Optimal scaling hyperparameters:")
            print(self.optimal_scaling_hyperparameters, file=f, end="\n\n")
            f.write(
                "Optimal feature selection method is: {}\n".format(
                    self.optimal_feature_selection
                )
            )
            f.write("Optimal feature selection hyperparameters:")
            print(self.optimal_feature_selection_hyperparameters, file=f, end="\n\n")
            f.write(
                "Optimal {} model is: {}\n".format(self.task_mode, self.optimal_model)
            )
            f.write("Optimal {} hyperparameters:".format(self.task_mode))
            print(self.optimal_model_hyperparameters, file=f, end="\n\n")

        # encoding
        self._fit_encoder = self._all_encoders[self.optimal_encoder](
            **self.optimal_encoder_hyperparameters
        )
        _X = self._fit_encoder.fit(_X)
        # imputer
        self._fit_imputer = self._all_imputers[self.optimal_imputer](
            **self.optimal_imputer_hyperparameters
        )
        _X = self._fit_imputer.fill(_X)
        # balancing
        self._fit_balancing = self._all_balancings[self.optimal_balancing](
            **self.optimal_balancing_hyperparameters
        )
        _X, _y = self._fit_balancing.fit_transform(_X, _y)

        # make sure the classes are integers (belongs to certain classes)
        _y = _y.astype(int)
        _y = _y.astype(int)
        # scaling
        self._fit_scaling = self._all_scalings[self.optimal_scaling](
            **self.optimal_scaling_hyperparameters
        )
        self._fit_scaling.fit(_X, _y)
        _X = self._fit_scaling.transform(_X)
        # feature selection
        self._fit_feature_selection = self._all_feature_selection[
            self.optimal_feature_selection
        ](**self.optimal_feature_selection_hyperparameters)
        self._fit_feature_selection.fit(_X, _y)
        _X = self._fit_feature_selection.transform(_X)
        # classification
        self._fit_model = self._all_models[self.optimal_model](
            **self.optimal_model_hyperparameters
        )
        self._fit_model.fit(_X, _y.values.ravel())

        # save the model
        if self.save:
            save_model(
                self.optimal_encoder,
                self.optimal_encoder_hyperparameters,
                self.optimal_imputer,
                self.optimal_imputer_hyperparameters,
                self.optimal_balancing,
                self.optimal_balancing_hyperparameters,
                self.optimal_scaling,
                self.optimal_scaling_hyperparameters,
                self.optimal_feature_selection,
                self.optimal_feature_selection_hyperparameters,
                self.optimal_model,
                self.optimal_model_hyperparameters,
                self.model_name,
            )

        return self

    def fit(self, X, y):

        if self.ignore_warning:  # ignore all warnings to generate clearer outputs
            warnings.filterwarnings("ignore")

        # get device info
        self.cpu_threads = (
            os.cpu_count() if self.cpu_threads is None else self.cpu_threads
        )
        self.gpu_count = device_count if self.use_gpu else 0

        _X = X.copy()
        _y = y.copy()

        (
            encoder,
            imputer,
            balancing,
            scaling,
            feature_selection,
            models,
        ) = self.get_hyperparameter_space(_X, _y)

        # if the model is already trained, read the setting
        if os.path.exists(self.model_name):

            print("Stored model found, load previous model.")
            self.load_model(_X, _y)

            return self

        # initialize temp directory
        # check if temp directory exists, if exists, empty it
        if os.path.isdir(self.temp_directory):
            shutil.rmtree(self.temp_directory)
        os.makedirs(self.temp_directory)
        os.makedirs(os.path.join(self.temp_directory, self.model_name))

        # write basic information to init.txt
        with open(
            os.path.join(self.temp_directory, self.model_name, "init.txt"), "w"
        ) as f:
            f.write("Features of the dataset: {}\n".format(list(_X.columns)))
            f.write(
                "Shape of the design matrix: {} * {}\n".format(_X.shape[0], _X.shape[1])
            )
            f.write("Response of the dataset: {}\n".format(list(_y.columns)))
            f.write(
                "Shape of the response vector: {} * {}\n".format(
                    _y.shape[0], _y.shape[1]
                )
            )
            f.write("Type of the task: {}.\n".format(self.task_mode))

        # set random seed
        np.random.seed(self.seed)

        # get maximum allowed errors
        self.max_error = int(self.max_evals * self.allow_error_prop)

        if self.validation:  # only perform train_test_split when validation
            # train test split so the performance of model selection and
            # hyperparameter optimization can be evaluated
            from sklearn.model_selection import train_test_split

            X_train, X_test, y_train, y_test = train_test_split(
                _X, _y, test_size=self.valid_size, random_state=self.seed
            )

        # the objective function of Bayesian Optimization tries to minimize
        # use accuracy score
        @ignore_warnings(category=ConvergenceWarning)
        def _objective(params):

            # different evaluation metrics for classification and regression
            if self.task_mode == "regression":
                # evaluation for predictions
                if self.objective == "MSE":
                    from sklearn.metrics import mean_squared_error

                    _obj = mean_squared_error
                elif self.objective == "MAE":
                    from sklearn.metrics import mean_absolute_error

                    _obj = mean_absolute_error
                elif self.objective == "MSLE":
                    from sklearn.metrics import mean_squared_log_error

                    _obj = mean_squared_log_error
                elif self.objective == "R2":
                    from sklearn.metrics import r2_score

                    _obj = r2_score
                elif self.objective == "MAX":
                    from sklearn.metrics import (
                        max_error,
                    )  # focus on reducing extreme losses

                    _obj = max_error
                else:
                    raise ValueError(
                        'Mode {} only support ["MSE", "MAE", "MSLE", "R2", "MAX"], get{}'.format(
                            self.task_mode, self.objective
                        )
                    )
            elif self.task_mode == "classification":
                # evaluation for predictions
                if self.objective == "accuracy":
                    from sklearn.metrics import accuracy_score

                    _obj = accuracy_score
                elif self.objective == "precision":
                    from sklearn.metrics import precision_score

                    _obj = precision_score
                elif self.objective == "auc":
                    from sklearn.metrics import roc_auc_score

                    _obj = roc_auc_score
                elif self.objective == "hinge":
                    from sklearn.metrics import hinge_loss

                    _obj = hinge_loss
                elif self.objective == "f1":
                    from sklearn.metrics import f1_score

                    _obj = f1_score
                else:
                    raise ValueError(
                        'Mode {} only support ["accuracy", "precision", "auc", "hinge", "f1"], get{}'.format(
                            self.task_mode, self.objective
                        )
                    )

            # pipeline of objective, [encoder, imputer, balancing, scaling, feature_selection, model]
            # select encoder and set hyperparameters

            # issue 1: https://github.com/PanyiDong/My_AutoML/issues/1
            # HyperOpt hyperparameter space conflicts with ray.tune

            # while setting hyperparameters space,
            # the method name is injected into the hyperparameter space
            # so, before fitting, these indications are removed

            # must have encoder
            _encoder_hyper = params["encoder"]
            # find corresponding encoder key
            for key in _encoder_hyper.keys():
                if "encoder_" in key:
                    _encoder_key = key
                    break
            _encoder = _encoder_hyper[_encoder_key]
            del _encoder_hyper[_encoder_key]
            # remvoe indcations
            _encoder_hyper = {
                k.replace(_encoder + "_", ""): _encoder_hyper[k] for k in _encoder_hyper
            }
            enc = encoder[_encoder](**_encoder_hyper)

            # select imputer and set hyperparameters
            _imputer_hyper = params["imputer"]
            # find corresponding imputer key
            for key in _imputer_hyper.keys():
                if "imputer_" in key:
                    _imputer_key = key
                    break
            _imputer = _imputer_hyper[_imputer_key]
            del _imputer_hyper[_imputer_key]
            # remvoe indcations
            _imputer_hyper = {
                k.replace(_imputer + "_", ""): _imputer_hyper[k] for k in _imputer_hyper
            }
            imp = imputer[_imputer](**_imputer_hyper)

            # select balancing and set hyperparameters
            # must have balancing, since no_preprocessing is included
            _balancing_hyper = params["balancing"]
            # find corresponding balancing key
            for key in _balancing_hyper.keys():
                if "balancing_" in key:
                    _balancing_key = key
                    break
            _balancing = _balancing_hyper[_balancing_key]
            del _balancing_hyper[_balancing_key]
            # remvoe indcations
            _balancing_hyper = {
                k.replace(_balancing + "_", ""): _balancing_hyper[k]
                for k in _balancing_hyper
            }
            blc = balancing[_balancing](**_balancing_hyper)

            # select scaling and set hyperparameters
            # must have scaling, since no_preprocessing is included
            _scaling_hyper = params["scaling"]
            # find corresponding scaling key
            for key in _scaling_hyper.keys():
                if "scaling_" in key:
                    _scaling_key = key
                    break
            _scaling = _scaling_hyper[_scaling_key]
            del _scaling_hyper[_scaling_key]
            # remvoe indcations
            _scaling_hyper = {
                k.replace(_scaling + "_", ""): _scaling_hyper[k] for k in _scaling_hyper
            }
            scl = scaling[_scaling](**_scaling_hyper)

            # select feature selection and set hyperparameters
            # must have feature selection, since no_preprocessing is included
            _feature_selection_hyper = params["feature_selection"]
            # find corresponding feature_selection key
            for key in _feature_selection_hyper.keys():
                if "feature_selection_" in key:
                    _feature_selection_key = key
                    break
            _feature_selection = _feature_selection_hyper[_feature_selection_key]
            del _feature_selection_hyper[_feature_selection_key]
            # remvoe indcations
            _feature_selection_hyper = {
                k.replace(_feature_selection + "_", ""): _feature_selection_hyper[k]
                for k in _feature_selection_hyper
            }
            fts = feature_selection[_feature_selection](**_feature_selection_hyper)

            # select model model and set hyperparameters
            # must have a model
            _model_hyper = params["model"]
            # find corresponding model key
            for key in _model_hyper.keys():
                if "model_" in key:
                    _model_key = key
                    break
            _model = _model_hyper[_model_key]
            del _model_hyper[_model_key]
            # remvoe indcations
            _model_hyper = {
                k.replace(_model + "_", ""): _model_hyper[k] for k in _model_hyper
            }
            mol = models[_model](
                **_model_hyper
            )  # call the model using passed parameters

            # obj_tmp_directory = self.temp_directory  # + "/iter_" + str(self._iter + 1)
            # if not os.path.isdir(obj_tmp_directory):
            #     os.makedirs(obj_tmp_directory)

            # with open(obj_tmp_directory + "/hyperparameter_settings.txt", "w") as f:
            with open("hyperparameter_settings.txt", "w") as f:
                f.write("Encoding method: {}\n".format(_encoder))
                f.write("Encoding Hyperparameters:")
                print(_encoder_hyper, file=f, end="\n\n")
                f.write("Imputation method: {}\n".format(_imputer))
                f.write("Imputation Hyperparameters:")
                print(_imputer_hyper, file=f, end="\n\n")
                f.write("Balancing method: {}\n".format(_balancing))
                f.write("Balancing Hyperparameters:")
                print(_balancing_hyper, file=f, end="\n\n")
                f.write("Scaling method: {}\n".format(_scaling))
                f.write("Scaling Hyperparameters:")
                print(_scaling_hyper, file=f, end="\n\n")
                f.write("Feature Selection method: {}\n".format(_feature_selection))
                f.write("Feature Selection Hyperparameters:")
                print(_feature_selection_hyper, file=f, end="\n\n")
                f.write("Model: {}\n".format(_model))
                f.write("Model Hyperparameters:")
                print(_model_hyper, file=f, end="\n\n")

            if self.validation:
                _X_train_obj, _X_test_obj = X_train.copy(), X_test.copy()
                _y_train_obj, _y_test_obj = y_train.copy(), y_test.copy()

                # encoding
                _X_train_obj = enc.fit(_X_train_obj)
                _X_test_obj = enc.refit(_X_test_obj)
                # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                with open("objective_process.txt", "w") as f:
                    f.write("Encoding finished, in imputation process.")
                # imputer
                _X_train_obj = imp.fill(_X_train_obj)
                _X_test_obj = imp.fill(_X_test_obj)
                # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                with open("objective_process.txt", "w") as f:
                    f.write("Imputation finished, in scaling process.")
                # balancing
                _X_train_obj, _y_train_obj = blc.fit_transform(
                    _X_train_obj, _y_train_obj
                )
                # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                with open("objective_process.txt", "w") as f:
                    f.write("Balancing finished, in scaling process.")

                # make sure the classes are integers (belongs to certain classes)
                _y_train_obj = _y_train_obj.astype(int)
                _y_test_obj = _y_test_obj.astype(int)
                # scaling
                scl.fit(_X_train_obj, _y_train_obj)
                _X_train_obj = scl.transform(_X_train_obj)
                _X_test_obj = scl.transform(_X_test_obj)
                # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                with open("objective_process.txt", "w") as f:
                    f.write("Scaling finished, in feature selection process.")
                # feature selection
                fts.fit(_X_train_obj, _y_train_obj)
                _X_train_obj = fts.transform(_X_train_obj)
                _X_test_obj = fts.transform(_X_test_obj)
                # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                with open("objective_process.txt", "w") as f:
                    f.write(
                        "Feature selection finished, in {} model.".format(
                            self.task_mode
                        )
                    )

                # fit model
                if scipy.sparse.issparse(
                    _X_train_obj
                ):  # check if returns sparse matrix
                    _X_train_obj = _X_train_obj.toarray()
                if scipy.sparse.issparse(_X_test_obj):
                    _X_test_obj = _X_test_obj.toarray()

                # store the preprocessed train/test datasets
                if isinstance(
                    _X_train_obj, np.ndarray
                ):  # in case numpy array is returned
                    pd.concat(
                        [pd.DataFrame(_X_train_obj), _y_train_obj],
                        axis=1,
                        ignore_index=True,
                    ).to_csv("train_preprocessed.csv", index=False)
                elif isinstance(_X_train_obj, pd.DataFrame):
                    pd.concat([_X_train_obj, _y_train_obj], axis=1).to_csv(
                        "train_preprocessed.csv", index=False
                    )
                else:
                    raise TypeError("Only accept numpy array or pandas dataframe!")

                if isinstance(_X_test_obj, np.ndarray):
                    pd.concat(
                        [pd.DataFrame(_X_test_obj), _y_test_obj],
                        axis=1,
                        ignore_index=True,
                    ).to_csv("test_preprocessed.csv", index=False)
                elif isinstance(_X_test_obj, pd.DataFrame):
                    pd.concat([_X_test_obj, _y_test_obj], axis=1).to_csv(
                        "test_preprocessed.csv", index=False
                    )
                else:
                    raise TypeError("Only accept numpy array or pandas dataframe!")

                mol.fit(_X_train_obj, _y_train_obj.values.ravel())
                os.remove("objective_process.txt")

                y_pred = mol.predict(_X_test_obj)
                if self.objective in [
                    "R2",
                    "accuracy",
                    "precision",
                    "auc",
                    "hinge",
                    "f1",
                ]:
                    # special treatment for ["R2", "accuracy", "precision", "auc", "hinge", "f1"]
                    # larger the better, since to minimize, add negative sign
                    _loss = -_obj(y_pred, _y_test_obj.values)
                else:
                    _loss = _obj(y_pred, _y_test_obj.values)

                with open("testing_objective.txt", "w") as f:
                    f.write("Loss from objective function is: {:.6f}\n".format(_loss))
                    f.write("Loss is calculate using {}.".format(self.objective))
                self._iter += 1

                # since we tries to minimize the objective function, take negative accuracy here
                if self.full_status:
                    tune.report(
                        encoder=_encoder,
                        encoder_hyperparameter=_encoder_hyper,
                        imputer=_imputer,
                        imputer_hyperparameter=_imputer_hyper,
                        balancing=_balancing,
                        balancing_hyperparameter=_balancing_hyper,
                        scaling=_scaling,
                        scaling_hyperparameter=_scaling_hyper,
                        feature_selection=_feature_selection,
                        feature_selection_hyperparameter=_feature_selection_hyper,
                        model=_model,
                        model_hyperparameter=_model_hyper,
                        fitted_model=_model,
                        training_status="fitted",
                        loss=_loss,
                    )
                else:
                    tune.report(
                        fitted_model=_model,
                        training_status="fitted",
                        loss=_loss,
                    )
            else:
                _X_obj = _X.copy()
                _y_obj = _y.copy()

                # encoding
                _X_obj = enc.fit(_X_obj)
                # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                with open("objective_process.txt", "w") as f:
                    f.write("Encoding finished, in imputation process.")
                # imputer
                _X_obj = imp.fill(_X_obj)
                # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                with open("objective_process.txt", "w") as f:
                    f.write("Imputation finished, in scaling process.")
                # balancing
                _X_obj = blc.fit_transform(_X_obj)
                # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                with open("objective_process.txt", "w") as f:
                    f.write("Balancing finished, in feature selection process.")
                # scaling
                scl.fit(_X_obj, _y_obj)
                _X_obj = scl.transform(_X_obj)
                # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                with open("objective_process.txt", "w") as f:
                    f.write("Scaling finished, in balancing process.")
                # feature selection
                fts.fit(_X_obj, _y_obj)
                _X_obj = fts.transform(_X_obj)
                # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                with open("objective_process.txt", "w") as f:
                    f.write(
                        "Feature selection finished, in {} model.".format(
                            self.task_mode
                        )
                    )

                # fit model
                mol.fit(_X_obj.values, _y_obj.values.ravel())
                pd.concat([_X_obj, _y_obj], axis=1).to_csv(
                    "data_preprocessed.csv", index=False
                )
                os.remove("objective_process.txt")

                y_pred = mol.predict(_X_obj.values)

                if self.objective == "R2":  # special treatment for r2_score
                    _loss = -_obj(y_pred, _y_obj.values)
                else:
                    _loss = _obj(y_pred, _y_obj.values)

                # with open(obj_tmp_directory + "/testing_objective.txt", "w") as f:
                with open("testing_objective.txt", "w") as f:
                    f.write("Loss from objective function is: {.6f}\n".format(_loss))
                    f.write("Loss is calculate using {}.".format(self.objective))
                self._iter += 1

                if self.full_status:
                    tune.report(
                        encoder=_encoder,
                        encoder_hyperparameter=_encoder_hyper,
                        imputer=_imputer,
                        imputer_hyperparameter=_imputer_hyper,
                        balancing=_balancing,
                        balancing_hyperparameter=_balancing_hyper,
                        scaling=_scaling,
                        scaling_hyperparameter=_scaling_hyper,
                        feature_selection=_feature_selection,
                        feature_selection_hyperparameter=_feature_selection_hyper,
                        model=_model,
                        model_hyperparameter=_model_hyper,
                        fitted_model=_model,
                        training_status="fitted",
                        loss=_loss,
                    )
                else:
                    tune.report(
                        fitted_model=_model,
                        training_status="fitted",
                        loss=_loss,
                    )

        # use ray for Model Selection and Hyperparameter Selection
        # get search algorithm
        algo = self.get_algo()

        # get search scheduler
        scheduler = self.get_scheduler()

        # get progress reporter
        progress_reporter = self.get_progress_reporter()

        # initialize ray
        ray.init(
            num_cpus=self.cpu_threads,
            num_gpus=self.gpu_count,
        )

        # trial directory name
        def trial_str_creator(trial):
            trialname = "iter_{}_id_{}".format(self._iter + 1, trial.trial_id)
            self._iter += 1
            return trialname

        # optimization process
        fit_analysis = tune.run(
            _objective,
            config=self.hyperparameter_space,
            name=self.model_name,  # name of the tuning process, use model_name
            mode="min",  # always call a minimization process
            search_alg=algo(**self.search_algo_setttings),
            scheduler=scheduler(**self.search_scheduler_settings),
            metric="loss",
            num_samples=self.max_evals,
            max_failures=self.max_error,
            time_budget_s=self.timeout,
            progress_reporter=progress_reporter,
            verbose=self.verbose,
            trial_dirname_creator=trial_str_creator,
            local_dir=self.temp_directory,
            log_to_file=True,
        )

        # shut down ray
        ray.shutdown()

        # select optimal settings and fit optimal pipeline
        self._fit_optimal(fit_analysis.best_config, _X, _y)

        # whether to retain temp files
        if self.delete_temp_after_terminate:
            shutil.rmtree(self.temp_directory)

        return self

    def predict(self, X):

        _X = X.copy()

        # may need preprocessing for test data, the preprocessing should be the same as in fit part
        # Encoding
        # convert string types to numerical type
        _X = self._fit_encoder.refit(_X)

        # Imputer
        # fill missing values
        _X = self._fit_imputer.fill(_X)

        # Balancing
        # deal with imbalanced dataset, using over-/under-sampling methods
        # No need to balance on test data

        # Scaling
        _X = self._fit_scaling.transform(_X)

        # Feature selection
        # Remove redundant features, reduce dimensionality
        _X = self._fit_feature_selection.transform(_X)

        # use model to predict
        return self._fit_model.predict(_X)
