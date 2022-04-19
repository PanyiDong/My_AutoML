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
Last Modified: Tuesday, 19th April 2022 11:36:52 am
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
import copy
import shutil
import importlib
import warnings
import random
import numpy as np
import pandas as pd
import scipy
from sklearn.utils._testing import ignore_warnings
from sklearn.exceptions import ConvergenceWarning
from typing import Callable

from My_AutoML._constant import UNI_CLASS
from My_AutoML._base import no_processing
from My_AutoML._utils._base import type_of_script
from My_AutoML._utils._file import (
    save_methods,
    load_methods,
    find_exact_path,
)
from My_AutoML._utils._data import (
    str2list,
    str2dict,
    train_test_split,
)
from My_AutoML._utils._optimize import (
    get_algo,
    get_scheduler,
    get_logger,
    get_progress_reporter,
    TimePlateauStopper,
)

# filter certain warnings
warnings.filterwarnings("ignore", message="The dataset is balanced, no change.")
warnings.filterwarnings("ignore", message="Variables are collinear")
# warnings.filterwarnings("ignore", message="Function checkpointing is disabled")
# warnings.filterwarnings(
#     "ignore", message="The TensorboardX logger cannot be instantiated"
# )
# I wish to use sklearn v1.0 for new features
# but there's conflicts between autosklearn models and sklearn models
# mae <-> absolute_error, mse <-> squared_error inconsistency
warnings.filterwarnings("ignore", message="Criterion 'mse' was deprecated in v1.0")
warnings.filterwarnings("ignore", message="Criterion 'mae' was deprecated in v1.0")
warnings.filterwarnings("ignore", message="'normalize' was deprecated in version 1.0")
warnings.filterwarnings("ignore", category=UserWarning)

# check whether gpu device available
import importlib

torch_spec = importlib.util.find_spec("torch")
if torch_spec is not None:
    import torch

    device_count = torch.cuda.device_count()
else:
    device_count = 0


class ObjectiveTrainer(tune.Trainable):
    def setup(
        self,
        params,
        _X,
        _y,
        encoder,
        imputer,
        balancing,
        scaling,
        feature_selection,
        models,
        model_name,
        task_mode,
        objective,
        validation,
        valid_size,
        full_status,
        reset_index,
        _iter,
        seed,
    ):
        # assign parameters
        self._X = _X
        self._y = _y
        self.model_name = model_name
        self.task_mode = task_mode
        self.objective = objective
        self.validation = validation
        self.valid_size = valid_size
        self.full_status = full_status
        self.reset_index = reset_index
        self._iter = _iter
        self.seed = seed

        # pipeline of objective, [encoder, imputer, balancing, scaling, feature_selection, model]
        # select encoder and set hyperparameters

        # issue 1: https://github.com/PanyiDong/My_AutoML/issues/1
        # HyperOpt hyperparameter space conflicts with ray.tune

        # while setting hyperparameters space,
        # the method name is injected into the hyperparameter space
        # so, before fitting, these indications are removed

        # must have encoder
        self._encoder_hyper = params["encoder"].copy()
        # find corresponding encoder key
        for key in self._encoder_hyper.keys():
            if "encoder_" in key:
                _encoder_key = key
                break
        self._encoder = self._encoder_hyper[_encoder_key]
        del self._encoder_hyper[_encoder_key]
        # remvoe indcations
        self._encoder_hyper = {
            k.replace(self._encoder + "_", ""): self._encoder_hyper[k]
            for k in self._encoder_hyper
        }
        self.enc = encoder[self._encoder](**self._encoder_hyper)

        # select imputer and set hyperparameters
        self._imputer_hyper = params["imputer"].copy()
        # find corresponding imputer key
        for key in self._imputer_hyper.keys():
            if "imputer_" in key:
                _imputer_key = key
                break
        self._imputer = self._imputer_hyper[_imputer_key]
        del self._imputer_hyper[_imputer_key]
        # remvoe indcations
        self._imputer_hyper = {
            k.replace(self._imputer + "_", ""): self._imputer_hyper[k]
            for k in self._imputer_hyper
        }
        self.imp = imputer[self._imputer](**self._imputer_hyper)

        # select balancing and set hyperparameters
        # must have balancing, since no_preprocessing is included
        self._balancing_hyper = params["balancing"]
        # find corresponding balancing key
        for key in self._balancing_hyper.keys():
            if "balancing_" in key:
                _balancing_key = key
                break
        self._balancing = self._balancing_hyper[_balancing_key]
        del self._balancing_hyper[_balancing_key]
        # remvoe indcations
        self._balancing_hyper = {
            k.replace(self._balancing + "_", ""): self._balancing_hyper[k]
            for k in self._balancing_hyper
        }
        self.blc = balancing[self._balancing](**self._balancing_hyper)

        # select scaling and set hyperparameters
        # must have scaling, since no_preprocessing is included
        self._scaling_hyper = params["scaling"]
        # find corresponding scaling key
        for key in self._scaling_hyper.keys():
            if "scaling_" in key:
                _scaling_key = key
                break
        self._scaling = self._scaling_hyper[_scaling_key]
        del self._scaling_hyper[_scaling_key]
        # remvoe indcations
        self._scaling_hyper = {
            k.replace(self._scaling + "_", ""): self._scaling_hyper[k]
            for k in self._scaling_hyper
        }
        self.scl = scaling[self._scaling](**self._scaling_hyper)

        # select feature selection and set hyperparameters
        # must have feature selection, since no_preprocessing is included
        self._feature_selection_hyper = params["feature_selection"]
        # find corresponding feature_selection key
        for key in self._feature_selection_hyper.keys():
            if "feature_selection_" in key:
                _feature_selection_key = key
                break
        self._feature_selection = self._feature_selection_hyper[_feature_selection_key]
        del self._feature_selection_hyper[_feature_selection_key]
        # remvoe indcations
        self._feature_selection_hyper = {
            k.replace(self._feature_selection + "_", ""): self._feature_selection_hyper[
                k
            ]
            for k in self._feature_selection_hyper
        }
        self.fts = feature_selection[self._feature_selection](
            **self._feature_selection_hyper
        )

        # select model model and set hyperparameters
        # must have a model
        self._model_hyper = params["model"]
        # find corresponding model key
        for key in self._model_hyper.keys():
            if "model_" in key:
                _model_key = key
                break
        self._model = self._model_hyper[_model_key]
        del self._model_hyper[_model_key]
        # remvoe indcations
        self._model_hyper = {
            k.replace(self._model + "_", ""): self._model_hyper[k]
            for k in self._model_hyper
        }
        self.mol = models[self._model](
            **self._model_hyper
        )  # call the model using passed parameters

        # obj_tmp_directory = self.temp_directory  # + "/iter_" + str(self._iter + 1)
        # if not os.path.isdir(obj_tmp_directory):
        #     os.makedirs(obj_tmp_directory)

        # with open(obj_tmp_directory + "/hyperparameter_settings.txt", "w") as f:
        with open("hyperparameter_settings.txt", "w") as f:
            f.write("Encoding method: {}\n".format(self._encoder))
            f.write("Encoding Hyperparameters:")
            print(self._encoder_hyper, file=f, end="\n\n")
            f.write("Imputation method: {}\n".format(self._imputer))
            f.write("Imputation Hyperparameters:")
            print(self._imputer_hyper, file=f, end="\n\n")
            f.write("Balancing method: {}\n".format(self._balancing))
            f.write("Balancing Hyperparameters:")
            print(self._balancing_hyper, file=f, end="\n\n")
            f.write("Scaling method: {}\n".format(self._scaling))
            f.write("Scaling Hyperparameters:")
            print(self._scaling_hyper, file=f, end="\n\n")
            f.write("Feature Selection method: {}\n".format(self._feature_selection))
            f.write("Feature Selection Hyperparameters:")
            print(self._feature_selection_hyper, file=f, end="\n\n")
            f.write("Model: {}\n".format(self._model))
            f.write("Model Hyperparameters:")
            print(self._model_hyper, file=f, end="\n\n")

    def step(self):

        return self._objective()

    @ignore_warnings(category=ConvergenceWarning)
    def _objective(
        self,
    ):

        # different evaluation metrics for classification and regression
        # notice: if add metrics that is larger the better, need to add - sign
        # at actual fitting process below (since try to minimize the loss)
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
            elif isinstance(self.objective, Callable):

                # if callable, use the callable
                _obj = self.objective
            else:
                raise ValueError(
                    'Mode {} only support ["MSE", "MAE", "MSLE", "R2", "MAX", callable], get{}'.format(
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
            elif isinstance(self.objective, Callable):

                # if callable, use the callable
                _obj = self.objective
            else:
                raise ValueError(
                    'Mode {} only support ["accuracy", "precision", "auc", "hinge", "f1", callable], get{}'.format(
                        self.task_mode, self.objective
                    )
                )

        if self.validation:
            # only perform train_test_split when validation
            # train test split so the performance of model selection and
            # hyperparameter optimization can be evaluated
            X_train, X_test, y_train, y_test = train_test_split(
                self._X, self._y, test_perc=self.valid_size, seed=self.seed
            )

            if self.reset_index:
                # reset index to avoid indexing order error
                X_train.reset_index(drop=True, inplace=True)
                X_test.reset_index(drop=True, inplace=True)
                y_train.reset_index(drop=True, inplace=True)
                y_test.reset_index(drop=True, inplace=True)

            _X_train_obj, _X_test_obj = X_train.copy(), X_test.copy()
            _y_train_obj, _y_test_obj = y_train.copy(), y_test.copy()

            # encoding
            _X_train_obj = self.enc.fit(_X_train_obj)
            _X_test_obj = self.enc.refit(_X_test_obj)
            # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
            with open("objective_process.txt", "w") as f:
                f.write("Encoding finished, in imputation process.")

            # imputer
            _X_train_obj = self.imp.fill(_X_train_obj)
            _X_test_obj = self.imp.fill(_X_test_obj)
            # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
            with open("objective_process.txt", "w") as f:
                f.write("Imputation finished, in scaling process.")

            # balancing
            _X_train_obj, _y_train_obj = self.blc.fit_transform(
                _X_train_obj, _y_train_obj
            )
            # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
            with open("objective_process.txt", "w") as f:
                f.write("Balancing finished, in scaling process.")
            # make sure the classes are integers (belongs to certain classes)
            _y_train_obj = _y_train_obj.astype(int)
            _y_test_obj = _y_test_obj.astype(int)

            # scaling
            self.scl.fit(_X_train_obj, _y_train_obj)
            _X_train_obj = self.scl.transform(_X_train_obj)
            _X_test_obj = self.scl.transform(_X_test_obj)
            # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
            with open("objective_process.txt", "w") as f:
                f.write("Scaling finished, in feature selection process.")

            # feature selection
            self.fts.fit(_X_train_obj, _y_train_obj)
            _X_train_obj = self.fts.transform(_X_train_obj)
            _X_test_obj = self.fts.transform(_X_test_obj)
            # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
            with open("objective_process.txt", "w") as f:
                f.write(
                    "Feature selection finished, in {} model.".format(self.task_mode)
                )

            # fit model
            if scipy.sparse.issparse(_X_train_obj):  # check if returns sparse matrix
                _X_train_obj = _X_train_obj.toarray()
            if scipy.sparse.issparse(_X_test_obj):
                _X_test_obj = _X_test_obj.toarray()

            # store the preprocessed train/test datasets
            if isinstance(_X_train_obj, np.ndarray):  # in case numpy array is returned
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

            self.mol.fit(_X_train_obj, _y_train_obj.values.ravel())
            os.remove("objective_process.txt")

            y_pred = self.mol.predict(_X_test_obj)
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
                _loss = -_obj(_y_test_obj.values, y_pred)
            else:
                _loss = _obj(_y_test_obj.values, y_pred)

            # save the fitted model objects
            save_methods(
                self.model_name,
                [self.enc, self.imp, self.blc, self.scl, self.fts, self.mol],
            )

            with open("testing_objective.txt", "w") as f:
                f.write("Loss from objective function is: {:.6f}\n".format(_loss))
                f.write("Loss is calculate using {}.".format(self.objective))
            self._iter += 1

            # since we tries to minimize the objective function, take negative accuracy here
            if self.full_status:
                # tune.report(
                #     encoder=_encoder,
                #     encoder_hyperparameter=_encoder_hyper,
                #     imputer=_imputer,
                #     imputer_hyperparameter=_imputer_hyper,
                #     balancing=_balancing,
                #     balancing_hyperparameter=_balancing_hyper,
                #     scaling=_scaling,
                #     scaling_hyperparameter=_scaling_hyper,
                #     feature_selection=_feature_selection,
                #     feature_selection_hyperparameter=_feature_selection_hyper,
                #     model=_model,
                #     model_hyperparameter=_model_hyper,
                #     fitted_model=_model,
                #     training_status="fitted",
                #     loss=_loss,
                # )
                # only for possible checks
                return {
                    "encoder": self._encoder,
                    "encoder_hyperparameter": self._encoder_hyper,
                    "imputer": self._imputer,
                    "imputer_hyperparameter": self._imputer_hyper,
                    "balancing": self._balancing,
                    "balancing_hyperparameter": self._balancing_hyper,
                    "scaling": self._scaling,
                    "scaling_hyperparameter": self._scaling_hyper,
                    "feature_selection": self._feature_selection,
                    "feature_selection_hyperparameter": self._feature_selection_hyper,
                    "model": self._model,
                    "model_hyperparameter": self._model_hyper,
                    "fitted_model": self._model,
                    "training_status": "fitted",
                    "loss": _loss,
                }
            else:
                # tune.report(
                #     fitted_model=_model,
                #     training_status="fitted",
                #     loss=_loss,
                # )
                # only for possible checks
                return {
                    "fitted_model": self._model,
                    "training_status": "fitted",
                    "loss": _loss,
                }
        else:
            _X_obj = self._X.copy()
            _y_obj = self._y.copy()

            # encoding
            _X_obj = self.enc.fit(_X_obj)
            # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
            with open("objective_process.txt", "w") as f:
                f.write("Encoding finished, in imputation process.")

            # imputer
            _X_obj = self.imp.fill(_X_obj)
            # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
            with open("objective_process.txt", "w") as f:
                f.write("Imputation finished, in scaling process.")

            # balancing
            _X_obj = self.blc.fit_transform(_X_obj)
            # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
            with open("objective_process.txt", "w") as f:
                f.write("Balancing finished, in feature selection process.")

            # scaling
            self.scl.fit(_X_obj, _y_obj)
            _X_obj = self.scl.transform(_X_obj)
            # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
            with open("objective_process.txt", "w") as f:
                f.write("Scaling finished, in balancing process.")

            # feature selection
            self.fts.fit(_X_obj, _y_obj)
            _X_obj = self.fts.transform(_X_obj)
            # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
            with open("objective_process.txt", "w") as f:
                f.write(
                    "Feature selection finished, in {} model.".format(self.task_mode)
                )

            # fit model
            if scipy.sparse.issparse(_X_obj):  # check if returns sparse matrix
                _X_obj = _X_obj.toarray()

            # store the preprocessed train/test datasets
            if isinstance(_X_obj, np.ndarray):  # in case numpy array is returned
                pd.concat(
                    [pd.DataFrame(_X_obj), _y_obj],
                    axis=1,
                    ignore_index=True,
                ).to_csv("train_preprocessed.csv", index=False)
            elif isinstance(_X_obj, pd.DataFrame):
                pd.concat([_X_obj, _y_obj], axis=1).to_csv(
                    "train_preprocessed.csv", index=False
                )
            else:
                raise TypeError("Only accept numpy array or pandas dataframe!")

            self.mol.fit(_X_obj, _y_obj.values.ravel())
            os.remove("objective_process.txt")

            y_pred = self.mol.predict(_X_obj)

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
                _loss = -_obj(_y_obj.values, y_pred)
            else:
                _loss = _obj(_y_obj.values, y_pred)

            # save the fitted model objects
            save_methods(
                self.model_name,
                [self.enc, self.imp, self.blc, self.scl, self.fts, self.mol],
            )

            # with open(obj_tmp_directory + "/testing_objective.txt", "w") as f:
            with open("testing_objective.txt", "w") as f:
                f.write("Loss from objective function is: {:.6f}\n".format(_loss))
                f.write("Loss is calculate using {}.".format(self.objective))
            self._iter += 1

            if self.full_status:
                # tune.report(
                #     encoder=_encoder,
                #     encoder_hyperparameter=_encoder_hyper,
                #     imputer=_imputer,
                #     imputer_hyperparameter=_imputer_hyper,
                #     balancing=_balancing,
                #     balancing_hyperparameter=_balancing_hyper,
                #     scaling=_scaling,
                #     scaling_hyperparameter=_scaling_hyper,
                #     feature_selection=_feature_selection,
                #     feature_selection_hyperparameter=_feature_selection_hyper,
                #     model=_model,
                #     model_hyperparameter=_model_hyper,
                #     fitted_model=_model,
                #     training_status="fitted",
                #     loss=_loss,
                # )
                # only for possible checks
                return {
                    "encoder": self._encoder,
                    "encoder_hyperparameter": self._encoder_hyper,
                    "imputer": self._imputer,
                    "imputer_hyperparameter": self._imputer_hyper,
                    "balancing": self._balancing,
                    "balancing_hyperparameter": self._balancing_hyper,
                    "scaling": self._scaling,
                    "scaling_hyperparameter": self._scaling_hyper,
                    "feature_selection": self._feature_selection,
                    "feature_selection_hyperparameter": self._feature_selection_hyper,
                    "model": self._model,
                    "model_hyperparameter": self._model_hyper,
                    "fitted_model": self._model,
                    "training_status": "fitted",
                    "loss": _loss,
                }
            else:
                # tune.report(
                #     fitted_model=_model,
                #     training_status="fitted",
                #     loss=_loss,
                # )
                # only for possible checks
                return {
                    "fitted_model": self._model,
                    "training_status": "fitted",
                    "loss": _loss,
                }


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

    search_algo_settings: search algorithm settings, default = {}
    need manual configuration for each search algorithm

    search_scheduler: search scheduler used, default = "FIFOScheduler"
    support ("FIFOScheduler", "ASHAScheduler", "HyperBandScheduler", "MedianStoppingRule"
            "PopulationBasedTraining", "PopulationBasedTrainingReplay", "PB2",
            "HyperBandForBOHB", callable)

    search_scheduler_settings: search scheduler settings, default = {}
    need manual configuration for each search scheduler

    logger: callback logger, default = ["Logger"]
    list of supported callbacks, support ("Logger", "TBX", "JSON", "CSV", "MLflow", "Wandb")

    progress_reporter: progress reporter, default = None
    automatically decide what progressbar to use
    support ("CLIReporter", "JupyterNotebookReporter")

    full_status: whether to print full status, default = False

    verbose: display for output, default = 1
    support (0, 1, 2, 3)

    cpu_threads: number of cpu threads to use, default = None
    if None, get all available cpu threads

    use_gpu: whether to use gpu, default = None
    if None, will use gpu if available, otherwise False (not to use gpu)

    reset_index: whether to reset index during traning, default = True
    there are methods that are index independent (ignore index, resetted, e.g. GAIN)
    if you wish to use these methods and set reset_index = False, please make sure
    all input index are ordered and starting from 0

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
        search_algo_settings={},
        search_scheduler="FIFOScheduler",
        search_scheduler_settings={},
        logger=["Logger"],
        progress_reporter=None,
        full_status=False,
        verbose=1,
        cpu_threads=None,
        use_gpu=None,
        reset_index=True,
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
        self.search_algo_settings = search_algo_settings
        self.search_scheduler = search_scheduler
        self.search_scheduler_settings = search_scheduler_settings
        self.logger = logger
        self.progress_reporter = progress_reporter
        self.full_status = full_status
        self.verbose = verbose
        self.cpu_threads = cpu_threads
        self.use_gpu = use_gpu
        self.reset_index = reset_index
        self.seed = seed

        self._iter = 0  # record iteration number
        self._fitted = False  # record whether the model has been fitted

    def get_hyperparameter_space(self, X, y):

        # initialize default search options
        # and select the search options based on the input restrictions
        # use copy to allows multiple manipulation

        # Encoding: convert string types to numerical type
        # all encoders available
        from My_AutoML._encoding import encoders

        self._all_encoders = copy.deepcopy(encoders)

        # get default encoder methods space
        if self.encoder == "auto":
            encoder = copy.deepcopy(self._all_encoders)
        else:
            self.encoder = str2list(self.encoder)  # string list to list
            encoder = {}  # if specified, check if encoders in default encoders
            for _encoder in self.encoder:
                if _encoder not in [*self._all_encoders]:
                    raise ValueError(
                        "Only supported encoders are {}, get {}.".format(
                            [*self._all_encoders], _encoder
                        )
                    )
                encoder[_encoder] = self._all_encoders[_encoder]

        # Imputer: fill missing values
        # all imputers available
        from My_AutoML._imputation import imputers

        self._all_imputers = copy.deepcopy(imputers)

        # special case: kNN imputer can not handle categorical data
        # remove kNN imputer from all imputers
        for _column in list(X.columns):
            if len(X[_column].unique()) <= min(0.1 * len(X), UNI_CLASS):
                del self._all_imputers["KNNImputer"]
                break

        # get default imputer methods space
        if self.imputer == "auto":
            if not X.isnull().values.any():  # if no missing values
                imputer = {"no_processing": no_processing}
                self._all_imputers = imputer  # limit default imputer space
            else:
                imputer = copy.deepcopy(self._all_imputers)
        else:
            self.imputer = str2list(self.imputer)  # string list to list
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

        # Balancing: deal with imbalanced dataset, using over-/under-sampling methods
        # all balancings available
        from My_AutoML._balancing import balancings

        self._all_balancings = copy.deepcopy(balancings)

        # get default balancing methods space
        if self.balancing == "auto":
            balancing = copy.deepcopy(self._all_balancings)
        else:
            self.balancing = str2list(self.balancing)  # string list to list
            balancing = {}  # if specified, check if balancings in default balancings
            for _balancing in self.balancing:
                if _balancing not in [*self._all_balancings]:
                    raise ValueError(
                        "Only supported balancings are {}, get {}.".format(
                            [*self._all_balancings], _balancing
                        )
                    )
                balancing[_balancing] = self._all_balancings[_balancing]

        # Scaling
        # all scalings available
        from My_AutoML._scaling import scalings

        self._all_scalings = copy.deepcopy(scalings)

        # get default scaling methods space
        if self.scaling == "auto":
            scaling = copy.deepcopy(self._all_scalings)
        else:
            self.scaling = str2list(self.scaling)  # string list to list
            scaling = {}  # if specified, check if scalings in default scalings
            for _scaling in self.scaling:
                if _scaling not in [*self._all_scalings]:
                    raise ValueError(
                        "Only supported scalings are {}, get {}.".format(
                            [*self._all_scalings], _scaling
                        )
                    )
                scaling[_scaling] = self._all_scalings[_scaling]

        # Feature selection: Remove redundant features, reduce dimensionality
        # all feature selections available
        from My_AutoML._feature_selection import feature_selections

        self._all_feature_selection = copy.deepcopy(feature_selections)
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
            feature_selection = copy.deepcopy(self._all_feature_selection)
        else:
            self.feature_selection = str2list(
                self.feature_selection
            )  # string list to list
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

        # Model selection/Hyperparameter optimization
        # using Bayesian Optimization
        # all models available
        # if mode is classification, use classification models
        # if mode is regression, use regression models
        if self.task_mode == "classification":
            from My_AutoML._model import classifiers

            self._all_models = copy.deepcopy(classifiers)
        elif self.task_mode == "regression":
            from My_AutoML._model import regressors

            self._all_models = copy.deepcopy(regressors)

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
            models = copy.deepcopy(self._all_models)
        else:
            self.models = str2list(self.models)  # string list to list
            models = {}  # if specified, check if models in default models
            for _model in self.models:
                if _model not in [*self._all_models]:
                    raise ValueError(
                        "Only supported models are {}, get {}.".format(
                            [*self._all_models], _model
                        )
                    )
                models[_model] = self._all_models[_model]

        # # initialize model hyperparameter space
        # _all_models_hyperparameters = copy.deepcopy(self._all_models_hyperparameters)

        # initialize default search space
        from My_AutoML._utils._optimize import _get_hyperparameter_space

        from My_AutoML._hyperparameters import (
            encoder_hyperparameter,
            imputer_hyperparameter,
            scaling_hyperparameter,
            balancing_hyperparameter,
            feature_selection_hyperparameter,
            classifier_hyperparameter,
            regressor_hyperparameter,
        )

        # if needed, modify default hyperparameter space
        # like model hyperparameter space below
        # all hyperparameters for encoders
        # _all_encoders_hyperparameters = copy.deepcopy(encoder_hyperparameter)

        # # initialize encoders hyperparameter space
        # _all_encoders_hyperparameters = copy.deepcopy(self._all_encoders_hyperparameters)

        # all hyperparemeters for imputers
        # _all_imputers_hyperparameters = copy.deepcopy(imputer_hyperparameter)

        # # initialize imputers hyperparameter space
        # _all_imputers_hyperparameters = copy.deepcopy(self._all_imputers_hyperparameters)

        # all hyperparameters for balancing methods
        # _all_balancings_hyperparameters = copy.deepcopy(balancing_hyperparameter)

        # # initialize balancing hyperparameter space
        # _all_balancings_hyperparameters = copy.deepcopy(self._all_balancings_hyperparameters)

        # all hyperparameters for scalings
        # _all_scalings_hyperparameters = copy.deepcopy(scaling_hyperparameter)

        # # initialize scaling hyperparameter space
        # _all_scalings_hyperparameters = copy.deepcopy(self._all_scalings_hyperparameters)

        # all hyperparameters for feature selections
        # _all_feature_selection_hyperparameters = copy.deepcopy(
        #     feature_selection_hyperparameter
        # )

        # # initialize feature selection hyperparameter space
        # _all_feature_selection_hyperparameters = copy.deepcopy(
        #     self._all_feature_selection_hyperparameters
        # )

        # all hyperparameters for the models by mode
        if self.task_mode == "classification":
            _all_models_hyperparameters = copy.deepcopy(classifier_hyperparameter)
        elif self.task_mode == "regression":
            _all_models_hyperparameters = copy.deepcopy(regressor_hyperparameter)

        # special treatment, for LightGBM_Classifier
        # if binary classification, use LIGHTGBM_BINARY_CLASSIFICATION
        # if multiclass, use LIGHTGBM_MULTICLASS_CLASSIFICATION
        if self.task_mode == "classification":
            # get LightGBM_Regressor key
            for item in _all_models_hyperparameters:
                for key in item.keys():
                    if key == "LightGBM_Classifier_objective":
                        # flatten to 1d
                        if len(pd.unique(y.to_numpy().flatten())) == 2:
                            from My_AutoML._constant import (
                                LIGHTGBM_BINARY_CLASSIFICATION,
                            )

                            item[key] = tune.choice(LIGHTGBM_BINARY_CLASSIFICATION)
                        else:
                            from My_AutoML._constant import (
                                LIGHTGBM_MULTICLASS_CLASSIFICATION,
                            )

                            item[key] = tune.choice(LIGHTGBM_MULTICLASS_CLASSIFICATION)

        # generate the hyperparameter space
        hyperparameter_space = _get_hyperparameter_space(
            X,
            encoder_hyperparameter,
            encoder,
            imputer_hyperparameter,
            imputer,
            balancing_hyperparameter,
            balancing,
            scaling_hyperparameter,
            scaling,
            feature_selection_hyperparameter,
            feature_selection,
            _all_models_hyperparameters,
            models,
            self.task_mode,
        )  # _X to choose whether include imputer
        # others are the combinations of default hyperparameter space & methods selected

        return (
            encoder,
            imputer,
            balancing,
            scaling,
            feature_selection,
            models,
            hyperparameter_space,
        )

    # method is deprecated as pickle save/load methods are now supported
    # load hyperparameter settings and train on the data
    # def load_model(self, _X, _y):

    #     # load hyperparameter settings
    #     with open(self.model_name) as f:
    #         optimal_setting = f.readlines()

    #     # remove change line signs
    #     optimal_setting = [item.replace("\n", "") for item in optimal_setting]
    #     # remove blank spaces
    #     while "" in optimal_setting:
    #         optimal_setting.remove("")

    #     # convert strings to readable dictionaries
    #     self.optimal_encoder = optimal_setting[0]
    #     self.optimal_encoder_hyperparameters = ast.literal_eval(optimal_setting[1])
    #     self.optimal_imputer = optimal_setting[2]
    #     self.optimal_imputer_hyperparameters = ast.literal_eval(optimal_setting[3])
    #     self.optimal_balancing = optimal_setting[4]
    #     self.optimal_balancing_hyperparameters = ast.literal_eval(optimal_setting[5])
    #     self.optimal_scaling = optimal_setting[6]
    #     self.optimal_scaling_hyperparameters = ast.literal_eval(optimal_setting[7])
    #     self.optimal_feature_selection = optimal_setting[8]
    #     self.optimal_feature_selection_hyperparameters = ast.literal_eval(
    #         optimal_setting[9]
    #     )
    #     self.optimal_model = optimal_setting[10]
    #     self.optimal_model_hyperparameters = ast.literal_eval(optimal_setting[11])

    #     # map the methods and hyperparameters
    #     # fit the methods
    #     # encoding
    #     self._fit_encoder = self._all_encoders[self.optimal_encoder](
    #         **self.optimal_encoder_hyperparameters
    #     )
    #     _X = self._fit_encoder.fit(_X)
    #     # imputer
    #     self._fit_imputer = self._all_imputers[self.optimal_imputer](
    #         **self.optimal_imputer_hyperparameters
    #     )
    #     _X = self._fit_imputer.fill(_X)
    #     # balancing
    #     self._fit_balancing = self._all_balancings[self.optimal_balancing](
    #         **self.optimal_balancing_hyperparameters
    #     )
    #     _X, _y = self._fit_balancing.fit_transform(_X, _y)

    #     # make sure the classes are integers (belongs to certain classes)
    #     if self.task_mode == "classification":
    #         _y = _y.astype(int)
    #     # scaling
    #     self._fit_scaling = self._all_scalings[self.optimal_scaling](
    #         **self.optimal_scaling_hyperparameters
    #     )
    #     self._fit_scaling.fit(_X, _y)
    #     _X = self._fit_scaling.transform(_X)
    #     # feature selection
    #     self._fit_feature_selection = self._all_feature_selection[
    #         self.optimal_feature_selection
    #     ](**self.optimal_feature_selection_hyperparameters)
    #     self._fit_feature_selection.fit(_X, _y)
    #     _X = self._fit_feature_selection.transform(_X)
    #     # model
    #     self._fit_model = self._all_models[self.optimal_model](
    #         **self.optimal_model_hyperparameters
    #     )
    #     self._fit_model.fit(_X, _y.values.ravel())

    #     return self

    # select optimal settings and fit on optimal hyperparameters
    def _fit_optimal(self, optimal_point, best_path):

        # optimal encoder
        optimal_encoder_hyperparameters = optimal_point["encoder"]
        # find optimal encoder key
        for _key in optimal_encoder_hyperparameters.keys():
            if "encoder_" in _key:
                _encoder_key = _key
                break
        optimal_encoder = optimal_encoder_hyperparameters[_encoder_key]
        del optimal_encoder_hyperparameters[_encoder_key]
        # remvoe indcations
        optimal_encoder_hyperparameters = {
            k.replace(optimal_encoder + "_", ""): optimal_encoder_hyperparameters[k]
            for k in optimal_encoder_hyperparameters
        }

        # optimal imputer
        optimal_imputer_hyperparameters = optimal_point["imputer"]
        # find optimal imputer key
        for _key in optimal_imputer_hyperparameters.keys():
            if "imputer_" in _key:
                _imputer_key = _key
                break
        optimal_imputer = optimal_imputer_hyperparameters[_imputer_key]
        del optimal_imputer_hyperparameters[_imputer_key]
        # remvoe indcations
        optimal_imputer_hyperparameters = {
            k.replace(optimal_imputer + "_", ""): optimal_imputer_hyperparameters[k]
            for k in optimal_imputer_hyperparameters
        }

        # optimal balancing
        optimal_balancing_hyperparameters = optimal_point["balancing"]
        # find optimal balancing key
        for _key in optimal_balancing_hyperparameters.keys():
            if "balancing_" in _key:
                _balancing_key = _key
                break
        optimal_balancing = optimal_balancing_hyperparameters[_balancing_key]
        del optimal_balancing_hyperparameters[_balancing_key]
        # remvoe indcations
        optimal_balancing_hyperparameters = {
            k.replace(optimal_balancing + "_", ""): optimal_balancing_hyperparameters[k]
            for k in optimal_balancing_hyperparameters
        }

        # optimal scaling
        optimal_scaling_hyperparameters = optimal_point["scaling"]
        # find optimal scaling key
        for _key in optimal_scaling_hyperparameters.keys():
            if "scaling_" in _key:
                _scaling_key = _key
                break
        optimal_scaling = optimal_scaling_hyperparameters[_scaling_key]
        del optimal_scaling_hyperparameters[_scaling_key]
        # remvoe indcations
        optimal_scaling_hyperparameters = {
            k.replace(optimal_scaling + "_", ""): optimal_scaling_hyperparameters[k]
            for k in optimal_scaling_hyperparameters
        }

        # optimal feature selection
        optimal_feature_selection_hyperparameters = optimal_point["feature_selection"]
        # find optimal feature_selection key
        for _key in optimal_feature_selection_hyperparameters.keys():
            if "feature_selection_" in _key:
                _feature_selection_key = _key
                break
        optimal_feature_selection = optimal_feature_selection_hyperparameters[
            _feature_selection_key
        ]
        del optimal_feature_selection_hyperparameters[_feature_selection_key]
        # remvoe indcations
        optimal_feature_selection_hyperparameters = {
            k.replace(
                optimal_feature_selection + "_", ""
            ): optimal_feature_selection_hyperparameters[k]
            for k in optimal_feature_selection_hyperparameters
        }

        # optimal classifier
        optimal_model_hyperparameters = optimal_point["model"]  # optimal model selected
        # find optimal model key
        for _key in optimal_model_hyperparameters.keys():
            if "model_" in _key:
                _model_key = _key
                break
        optimal_model = optimal_model_hyperparameters[
            _model_key
        ]  # optimal hyperparameter settings selected
        del optimal_model_hyperparameters[_model_key]
        # remvoe indcations
        optimal_model_hyperparameters = {
            k.replace(optimal_model + "_", ""): optimal_model_hyperparameters[k]
            for k in optimal_model_hyperparameters
        }

        # record optimal settings
        with open(
            os.path.join(self.temp_directory, self.model_name, "optimal_setting.txt"),
            "w",
        ) as f:
            f.write("Optimal encoding method is: {}\n".format(optimal_encoder))
            f.write("Optimal encoding hyperparameters:")
            print(optimal_encoder_hyperparameters, file=f, end="\n\n")
            f.write("Optimal imputation method is: {}\n".format(optimal_imputer))
            f.write("Optimal imputation hyperparameters:")
            print(optimal_imputer_hyperparameters, file=f, end="\n\n")
            f.write("Optimal balancing method is: {}\n".format(optimal_balancing))
            f.write("Optimal balancing hyperparamters:")
            print(optimal_balancing_hyperparameters, file=f, end="\n\n")
            f.write("Optimal scaling method is: {}\n".format(optimal_scaling))
            f.write("Optimal scaling hyperparameters:")
            print(optimal_scaling_hyperparameters, file=f, end="\n\n")
            f.write(
                "Optimal feature selection method is: {}\n".format(
                    optimal_feature_selection
                )
            )
            f.write("Optimal feature selection hyperparameters:")
            print(optimal_feature_selection_hyperparameters, file=f, end="\n\n")
            f.write("Optimal {} model is: {}\n".format(self.task_mode, optimal_model))
            f.write("Optimal {} hyperparameters:".format(self.task_mode))
            print(optimal_model_hyperparameters, file=f, end="\n\n")

        # method is deprecated as pickle save/load methods are now supported
        # # encoding
        # self._fit_encoder = self._all_encoders[self.optimal_encoder](
        #     **self.optimal_encoder_hyperparameters
        # )
        # _X = self._fit_encoder.fit(_X)

        # # imputer
        # self._fit_imputer = self._all_imputers[self.optimal_imputer](
        #     **self.optimal_imputer_hyperparameters
        # )
        # _X = self._fit_imputer.fill(_X)

        # # balancing
        # self._fit_balancing = self._all_balancings[self.optimal_balancing](
        #     **self.optimal_balancing_hyperparameters
        # )
        # _X, _y = self._fit_balancing.fit_transform(_X, _y)
        # # make sure the classes are integers (belongs to certain classes)
        # _y = _y.astype(int)
        # _y = _y.astype(int)

        # # scaling
        # self._fit_scaling = self._all_scalings[self.optimal_scaling](
        #     **self.optimal_scaling_hyperparameters
        # )
        # self._fit_scaling.fit(_X, _y)
        # _X = self._fit_scaling.transform(_X)

        # # feature selection
        # self._fit_feature_selection = self._all_feature_selection[
        #     self.optimal_feature_selection
        # ](**self.optimal_feature_selection_hyperparameters)
        # self._fit_feature_selection.fit(_X, _y)
        # _X = self._fit_feature_selection.transform(_X)

        # # model fitting
        # self._fit_model = self._all_models[self.optimal_model](
        #     **self.optimal_model_hyperparameters
        # )
        # self._fit_model.fit(_X, _y.values.ravel())

        (
            self._fit_encoder,
            self._fit_imputer,
            self._fit_balancing,
            self._fit_scaling,
            self._fit_feature_selection,
            self._fit_model,
        ) = load_methods(best_path)

        # save the model
        if self.save:
            # save_model(
            #     self.optimal_encoder,
            #     self.optimal_encoder_hyperparameters,
            #     self.optimal_imputer,
            #     self.optimal_imputer_hyperparameters,
            #     self.optimal_balancing,
            #     self.optimal_balancing_hyperparameters,
            #     self.optimal_scaling,
            #     self.optimal_scaling_hyperparameters,
            #     self.optimal_feature_selection,
            #     self.optimal_feature_selection_hyperparameters,
            #     self.optimal_model,
            #     self.optimal_model_hyperparameters,
            #     self.model_name,
            # )
            save_methods(
                self.model_name,
                [
                    self._fit_encoder,
                    self._fit_imputer,
                    self._fit_balancing,
                    self._fit_scaling,
                    self._fit_feature_selection,
                    self._fit_model,
                ],
            )

        return self

    # the objective function of HPO tries to minimize the loss
    # default use accuracy score
    # @ignore_warnings(category=ConvergenceWarning)
    # def _objective(
    #     self,
    #     params,
    #     _X,
    #     _y,
    #     encoder,
    #     imputer,
    #     balancing,
    #     scaling,
    #     feature_selection,
    #     models,
    # ):

    #     # different evaluation metrics for classification and regression
    #     # notice: if add metrics that is larger the better, need to add - sign
    #     # at actual fitting process below (since try to minimize the loss)
    #     if self.task_mode == "regression":
    #         # evaluation for predictions
    #         if self.objective == "MSE":
    #             from sklearn.metrics import mean_squared_error

    #             _obj = mean_squared_error
    #         elif self.objective == "MAE":
    #             from sklearn.metrics import mean_absolute_error

    #             _obj = mean_absolute_error
    #         elif self.objective == "MSLE":
    #             from sklearn.metrics import mean_squared_log_error

    #             _obj = mean_squared_log_error
    #         elif self.objective == "R2":
    #             from sklearn.metrics import r2_score

    #             _obj = r2_score
    #         elif self.objective == "MAX":
    #             from sklearn.metrics import (
    #                 max_error,
    #             )  # focus on reducing extreme losses

    #             _obj = max_error
    #         elif isinstance(self.objective, Callable):

    #             # if callable, use the callable
    #             _obj = self.objective
    #         else:
    #             raise ValueError(
    #                 'Mode {} only support ["MSE", "MAE", "MSLE", "R2", "MAX", callable], get{}'.format(
    #                     self.task_mode, self.objective
    #                 )
    #             )
    #     elif self.task_mode == "classification":
    #         # evaluation for predictions
    #         if self.objective == "accuracy":
    #             from sklearn.metrics import accuracy_score

    #             _obj = accuracy_score
    #         elif self.objective == "precision":
    #             from sklearn.metrics import precision_score

    #             _obj = precision_score
    #         elif self.objective == "auc":
    #             from sklearn.metrics import roc_auc_score

    #             _obj = roc_auc_score
    #         elif self.objective == "hinge":
    #             from sklearn.metrics import hinge_loss

    #             _obj = hinge_loss
    #         elif self.objective == "f1":
    #             from sklearn.metrics import f1_score

    #             _obj = f1_score
    #         elif isinstance(self.objective, Callable):

    #             # if callable, use the callable
    #             _obj = self.objective
    #         else:
    #             raise ValueError(
    #                 'Mode {} only support ["accuracy", "precision", "auc", "hinge", "f1", callable], get{}'.format(
    #                     self.task_mode, self.objective
    #                 )
    #             )

    #     # pipeline of objective, [encoder, imputer, balancing, scaling, feature_selection, model]
    #     # select encoder and set hyperparameters

    #     # issue 1: https://github.com/PanyiDong/My_AutoML/issues/1
    #     # HyperOpt hyperparameter space conflicts with ray.tune

    #     # while setting hyperparameters space,
    #     # the method name is injected into the hyperparameter space
    #     # so, before fitting, these indications are removed

    #     # must have encoder
    #     _encoder_hyper = params["encoder"]
    #     # find corresponding encoder key
    #     for key in _encoder_hyper.keys():
    #         if "encoder_" in key:
    #             _encoder_key = key
    #             break
    #     _encoder = _encoder_hyper[_encoder_key]
    #     del _encoder_hyper[_encoder_key]
    #     # remvoe indcations
    #     _encoder_hyper = {
    #         k.replace(_encoder + "_", ""): _encoder_hyper[k] for k in _encoder_hyper
    #     }
    #     enc = encoder[_encoder](**_encoder_hyper)

    #     # select imputer and set hyperparameters
    #     _imputer_hyper = params["imputer"]
    #     # find corresponding imputer key
    #     for key in _imputer_hyper.keys():
    #         if "imputer_" in key:
    #             _imputer_key = key
    #             break
    #     _imputer = _imputer_hyper[_imputer_key]
    #     del _imputer_hyper[_imputer_key]
    #     # remvoe indcations
    #     _imputer_hyper = {
    #         k.replace(_imputer + "_", ""): _imputer_hyper[k] for k in _imputer_hyper
    #     }
    #     imp = imputer[_imputer](**_imputer_hyper)

    #     # select balancing and set hyperparameters
    #     # must have balancing, since no_preprocessing is included
    #     _balancing_hyper = params["balancing"]
    #     # find corresponding balancing key
    #     for key in _balancing_hyper.keys():
    #         if "balancing_" in key:
    #             _balancing_key = key
    #             break
    #     _balancing = _balancing_hyper[_balancing_key]
    #     del _balancing_hyper[_balancing_key]
    #     # remvoe indcations
    #     _balancing_hyper = {
    #         k.replace(_balancing + "_", ""): _balancing_hyper[k]
    #         for k in _balancing_hyper
    #     }
    #     blc = balancing[_balancing](**_balancing_hyper)

    #     # select scaling and set hyperparameters
    #     # must have scaling, since no_preprocessing is included
    #     _scaling_hyper = params["scaling"]
    #     # find corresponding scaling key
    #     for key in _scaling_hyper.keys():
    #         if "scaling_" in key:
    #             _scaling_key = key
    #             break
    #     _scaling = _scaling_hyper[_scaling_key]
    #     del _scaling_hyper[_scaling_key]
    #     # remvoe indcations
    #     _scaling_hyper = {
    #         k.replace(_scaling + "_", ""): _scaling_hyper[k] for k in _scaling_hyper
    #     }
    #     scl = scaling[_scaling](**_scaling_hyper)

    #     # select feature selection and set hyperparameters
    #     # must have feature selection, since no_preprocessing is included
    #     _feature_selection_hyper = params["feature_selection"]
    #     # find corresponding feature_selection key
    #     for key in _feature_selection_hyper.keys():
    #         if "feature_selection_" in key:
    #             _feature_selection_key = key
    #             break
    #     _feature_selection = _feature_selection_hyper[_feature_selection_key]
    #     del _feature_selection_hyper[_feature_selection_key]
    #     # remvoe indcations
    #     _feature_selection_hyper = {
    #         k.replace(_feature_selection + "_", ""): _feature_selection_hyper[k]
    #         for k in _feature_selection_hyper
    #     }
    #     fts = feature_selection[_feature_selection](**_feature_selection_hyper)

    #     # select model model and set hyperparameters
    #     # must have a model
    #     _model_hyper = params["model"]
    #     # find corresponding model key
    #     for key in _model_hyper.keys():
    #         if "model_" in key:
    #             _model_key = key
    #             break
    #     _model = _model_hyper[_model_key]
    #     del _model_hyper[_model_key]
    #     # remvoe indcations
    #     _model_hyper = {
    #         k.replace(_model + "_", ""): _model_hyper[k] for k in _model_hyper
    #     }
    #     mol = models[_model](**_model_hyper)  # call the model using passed parameters

    #     # obj_tmp_directory = self.temp_directory  # + "/iter_" + str(self._iter + 1)
    #     # if not os.path.isdir(obj_tmp_directory):
    #     #     os.makedirs(obj_tmp_directory)

    #     # with open(obj_tmp_directory + "/hyperparameter_settings.txt", "w") as f:
    #     with open("hyperparameter_settings.txt", "w") as f:
    #         f.write("Encoding method: {}\n".format(_encoder))
    #         f.write("Encoding Hyperparameters:")
    #         print(_encoder_hyper, file=f, end="\n\n")
    #         f.write("Imputation method: {}\n".format(_imputer))
    #         f.write("Imputation Hyperparameters:")
    #         print(_imputer_hyper, file=f, end="\n\n")
    #         f.write("Balancing method: {}\n".format(_balancing))
    #         f.write("Balancing Hyperparameters:")
    #         print(_balancing_hyper, file=f, end="\n\n")
    #         f.write("Scaling method: {}\n".format(_scaling))
    #         f.write("Scaling Hyperparameters:")
    #         print(_scaling_hyper, file=f, end="\n\n")
    #         f.write("Feature Selection method: {}\n".format(_feature_selection))
    #         f.write("Feature Selection Hyperparameters:")
    #         print(_feature_selection_hyper, file=f, end="\n\n")
    #         f.write("Model: {}\n".format(_model))
    #         f.write("Model Hyperparameters:")
    #         print(_model_hyper, file=f, end="\n\n")

    #     if self.validation:
    #         # only perform train_test_split when validation
    #         # train test split so the performance of model selection and
    #         # hyperparameter optimization can be evaluated
    #         X_train, X_test, y_train, y_test = train_test_split(
    #             _X, _y, test_perc=self.valid_size, seed=self.seed
    #         )

    #         if self.reset_index:
    #             # reset index to avoid indexing order error
    #             X_train.reset_index(drop=True, inplace=True)
    #             X_test.reset_index(drop=True, inplace=True)
    #             y_train.reset_index(drop=True, inplace=True)
    #             y_test.reset_index(drop=True, inplace=True)

    #         _X_train_obj, _X_test_obj = X_train.copy(), X_test.copy()
    #         _y_train_obj, _y_test_obj = y_train.copy(), y_test.copy()

    #         # encoding
    #         _X_train_obj = enc.fit(_X_train_obj)
    #         _X_test_obj = enc.refit(_X_test_obj)
    #         # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
    #         with open("objective_process.txt", "w") as f:
    #             f.write("Encoding finished, in imputation process.")

    #         # imputer
    #         _X_train_obj = imp.fill(_X_train_obj)
    #         _X_test_obj = imp.fill(_X_test_obj)
    #         # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
    #         with open("objective_process.txt", "w") as f:
    #             f.write("Imputation finished, in scaling process.")

    #         # balancing
    #         _X_train_obj, _y_train_obj = blc.fit_transform(_X_train_obj, _y_train_obj)
    #         # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
    #         with open("objective_process.txt", "w") as f:
    #             f.write("Balancing finished, in scaling process.")
    #         # make sure the classes are integers (belongs to certain classes)
    #         _y_train_obj = _y_train_obj.astype(int)
    #         _y_test_obj = _y_test_obj.astype(int)

    #         # scaling
    #         scl.fit(_X_train_obj, _y_train_obj)
    #         _X_train_obj = scl.transform(_X_train_obj)
    #         _X_test_obj = scl.transform(_X_test_obj)
    #         # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
    #         with open("objective_process.txt", "w") as f:
    #             f.write("Scaling finished, in feature selection process.")

    #         # feature selection
    #         fts.fit(_X_train_obj, _y_train_obj)
    #         _X_train_obj = fts.transform(_X_train_obj)
    #         _X_test_obj = fts.transform(_X_test_obj)
    #         # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
    #         with open("objective_process.txt", "w") as f:
    #             f.write(
    #                 "Feature selection finished, in {} model.".format(self.task_mode)
    #             )

    #         # fit model
    #         if scipy.sparse.issparse(_X_train_obj):  # check if returns sparse matrix
    #             _X_train_obj = _X_train_obj.toarray()
    #         if scipy.sparse.issparse(_X_test_obj):
    #             _X_test_obj = _X_test_obj.toarray()

    #         # store the preprocessed train/test datasets
    #         if isinstance(_X_train_obj, np.ndarray):  # in case numpy array is returned
    #             pd.concat(
    #                 [pd.DataFrame(_X_train_obj), _y_train_obj],
    #                 axis=1,
    #                 ignore_index=True,
    #             ).to_csv("train_preprocessed.csv", index=False)
    #         elif isinstance(_X_train_obj, pd.DataFrame):
    #             pd.concat([_X_train_obj, _y_train_obj], axis=1).to_csv(
    #                 "train_preprocessed.csv", index=False
    #             )
    #         else:
    #             raise TypeError("Only accept numpy array or pandas dataframe!")

    #         if isinstance(_X_test_obj, np.ndarray):
    #             pd.concat(
    #                 [pd.DataFrame(_X_test_obj), _y_test_obj],
    #                 axis=1,
    #                 ignore_index=True,
    #             ).to_csv("test_preprocessed.csv", index=False)
    #         elif isinstance(_X_test_obj, pd.DataFrame):
    #             pd.concat([_X_test_obj, _y_test_obj], axis=1).to_csv(
    #                 "test_preprocessed.csv", index=False
    #             )
    #         else:
    #             raise TypeError("Only accept numpy array or pandas dataframe!")

    #         mol.fit(_X_train_obj, _y_train_obj.values.ravel())
    #         os.remove("objective_process.txt")

    #         y_pred = mol.predict(_X_test_obj)
    #         if self.objective in [
    #             "R2",
    #             "accuracy",
    #             "precision",
    #             "auc",
    #             "hinge",
    #             "f1",
    #         ]:
    #             # special treatment for ["R2", "accuracy", "precision", "auc", "hinge", "f1"]
    #             # larger the better, since to minimize, add negative sign
    #             _loss = -_obj(_y_test_obj.values, y_pred)
    #         else:
    #             _loss = _obj(_y_test_obj.values, y_pred)

    #         # save the fitted model objects
    #         save_methods(
    #             self.model_name,
    #             [enc, imp, blc, scl, fts, mol],
    #         )

    #         with open("testing_objective.txt", "w") as f:
    #             f.write("Loss from objective function is: {:.6f}\n".format(_loss))
    #             f.write("Loss is calculate using {}.".format(self.objective))
    #         self._iter += 1

    #         # since we tries to minimize the objective function, take negative accuracy here
    #         if self.full_status:
    #             tune.report(
    #                 encoder=_encoder,
    #                 encoder_hyperparameter=_encoder_hyper,
    #                 imputer=_imputer,
    #                 imputer_hyperparameter=_imputer_hyper,
    #                 balancing=_balancing,
    #                 balancing_hyperparameter=_balancing_hyper,
    #                 scaling=_scaling,
    #                 scaling_hyperparameter=_scaling_hyper,
    #                 feature_selection=_feature_selection,
    #                 feature_selection_hyperparameter=_feature_selection_hyper,
    #                 model=_model,
    #                 model_hyperparameter=_model_hyper,
    #                 fitted_model=_model,
    #                 training_status="fitted",
    #                 loss=_loss,
    #             )
    #             # only for possible checks
    #             return {
    #                 "fitted_model": _model,
    #                 "training_status": "fitted",
    #                 "loss": _loss,
    #             }
    #         else:
    #             tune.report(
    #                 fitted_model=_model,
    #                 training_status="fitted",
    #                 loss=_loss,
    #             )
    #             # only for possible checks
    #             return {
    #                 "fitted_model": _model,
    #                 "training_status": "fitted",
    #                 "loss": _loss,
    #             }
    #     else:
    #         _X_obj = _X.copy()
    #         _y_obj = _y.copy()

    #         # encoding
    #         _X_obj = enc.fit(_X_obj)
    #         # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
    #         with open("objective_process.txt", "w") as f:
    #             f.write("Encoding finished, in imputation process.")

    #         # imputer
    #         _X_obj = imp.fill(_X_obj)
    #         # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
    #         with open("objective_process.txt", "w") as f:
    #             f.write("Imputation finished, in scaling process.")

    #         # balancing
    #         _X_obj = blc.fit_transform(_X_obj)
    #         # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
    #         with open("objective_process.txt", "w") as f:
    #             f.write("Balancing finished, in feature selection process.")

    #         # scaling
    #         scl.fit(_X_obj, _y_obj)
    #         _X_obj = scl.transform(_X_obj)
    #         # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
    #         with open("objective_process.txt", "w") as f:
    #             f.write("Scaling finished, in balancing process.")

    #         # feature selection
    #         fts.fit(_X_obj, _y_obj)
    #         _X_obj = fts.transform(_X_obj)
    #         # with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
    #         with open("objective_process.txt", "w") as f:
    #             f.write(
    #                 "Feature selection finished, in {} model.".format(self.task_mode)
    #             )

    #         # fit model
    #         if scipy.sparse.issparse(_X_obj):  # check if returns sparse matrix
    #             _X_obj = _X_obj.toarray()

    #         # store the preprocessed train/test datasets
    #         if isinstance(_X_obj, np.ndarray):  # in case numpy array is returned
    #             pd.concat(
    #                 [pd.DataFrame(_X_obj), _y_obj],
    #                 axis=1,
    #                 ignore_index=True,
    #             ).to_csv("train_preprocessed.csv", index=False)
    #         elif isinstance(_X_obj, pd.DataFrame):
    #             pd.concat([_X_obj, _y_obj], axis=1).to_csv(
    #                 "train_preprocessed.csv", index=False
    #             )
    #         else:
    #             raise TypeError("Only accept numpy array or pandas dataframe!")

    #         mol.fit(_X_obj, _y_obj.values.ravel())
    #         os.remove("objective_process.txt")

    #         y_pred = mol.predict(_X_obj)

    #         if self.objective in [
    #             "R2",
    #             "accuracy",
    #             "precision",
    #             "auc",
    #             "hinge",
    #             "f1",
    #         ]:
    #             # special treatment for ["R2", "accuracy", "precision", "auc", "hinge", "f1"]
    #             # larger the better, since to minimize, add negative sign
    #             _loss = -_obj(_y_obj.values, y_pred)
    #         else:
    #             _loss = _obj(_y_obj.values, y_pred)

    #         # save the fitted model objects
    #         save_methods(
    #             self.model_name,
    #             [enc, imp, blc, scl, fts, mol],
    #         )

    #         # with open(obj_tmp_directory + "/testing_objective.txt", "w") as f:
    #         with open("testing_objective.txt", "w") as f:
    #             f.write("Loss from objective function is: {:.6f}\n".format(_loss))
    #             f.write("Loss is calculate using {}.".format(self.objective))
    #         self._iter += 1

    #         if self.full_status:
    #             tune.report(
    #                 encoder=_encoder,
    #                 encoder_hyperparameter=_encoder_hyper,
    #                 imputer=_imputer,
    #                 imputer_hyperparameter=_imputer_hyper,
    #                 balancing=_balancing,
    #                 balancing_hyperparameter=_balancing_hyper,
    #                 scaling=_scaling,
    #                 scaling_hyperparameter=_scaling_hyper,
    #                 feature_selection=_feature_selection,
    #                 feature_selection_hyperparameter=_feature_selection_hyper,
    #                 model=_model,
    #                 model_hyperparameter=_model_hyper,
    #                 fitted_model=_model,
    #                 training_status="fitted",
    #                 loss=_loss,
    #             )
    #             # only for possible checks
    #             return {
    #                 "fitted_model": _model,
    #                 "training_status": "fitted",
    #                 "loss": _loss,
    #             }
    #         else:
    #             tune.report(
    #                 fitted_model=_model,
    #                 training_status="fitted",
    #                 loss=_loss,
    #             )
    #             # only for possible checks
    #             return {
    #                 "fitted_model": _model,
    #                 "training_status": "fitted",
    #                 "loss": _loss,
    #             }

    def fit(self, X, y):

        if self.ignore_warning:  # ignore all warnings to generate clearer outputs
            warnings.filterwarnings("ignore")

        # get device info
        self.cpu_threads = (
            os.cpu_count() if self.cpu_threads is None else self.cpu_threads
        )
        # auto use_gpu selection if gpu is available
        self.use_gpu = (device_count > 0) if self.use_gpu is None else self.use_gpu
        # count gpu available
        self.gpu_count = device_count if self.use_gpu else 0

        # print warning if gpu available but not used
        if device_count > 0 and not self.use_gpu:
            warnings.warn(
                "You have {} GPU(s) available, but you have not set use_gpu to True, \
                which may drastically increase time to train neural networks.".format(
                    device_count
                )
            )
        # raise error if gpu not available but used
        if device_count == 0 and self.use_gpu:
            raise SystemError(
                "You have no GPU available, but you have set use_gpu to True. \
                Please check your GPU availability."
            )

        # get progress report from environment
        # if specified, use specified progress report
        self.progress_reporter = (
            (
                "CLIReporter"
                if type_of_script() == "terminal"
                else "JupyterNotebookReporter"
            )
            if self.progress_reporter is None
            else self.progress_reporter
        )

        if self.progress_reporter not in ["CLIReporter", "JupyterNotebookReporter"]:
            raise TypeError(
                "Progress reporter must be either CLIReporter or JupyterNotebookReporter, get {}.".format(
                    self.progress_reporter
                )
            )

        _X = X.copy()
        _y = y.copy()

        if self.reset_index:
            # reset index to avoid indexing error
            _X.reset_index(drop=True, inplace=True)
            _y.reset_index(drop=True, inplace=True)

        (
            encoder,
            imputer,
            balancing,
            scaling,
            feature_selection,
            models,
            hyperparameter_space,
        ) = self.get_hyperparameter_space(_X, _y)

        # print([item.sample() for key, item in hyperparameter_space.items() if key != "task_type"])

        # if the model is already trained, read the setting
        if os.path.exists(self.model_name):

            print("Stored model found, load previous model.")
            # self.load_model(_X, _y)
            (
                self._fit_encoder,
                self._fit_imputer,
                self._fit_balancing,
                self._fit_scaling,
                self._fit_feature_selection,
                self._fit_model,
            ) = load_methods(self.model_name)

            self._fitted = True  # successfully fitted the model

            return self

        # initialize temp directory
        # check if temp directory exists, if exists, empty it
        if os.path.isdir(os.path.join(self.temp_directory, self.model_name)):
            shutil.rmtree(os.path.join(self.temp_directory, self.model_name))
        if not os.path.isdir(self.temp_directory):
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
        random.seed(self.seed)

        # get maximum allowed errors
        self.max_error = int(self.max_evals * self.allow_error_prop)

        # load dict settings for search_algo and search_scheduler
        self.search_algo_settings = str2dict(self.search_algo_settings)
        self.search_scheduler_settings = str2dict(self.search_scheduler_settings)

        # use ray for Model Selection and Hyperparameter Selection
        # get search algorithm
        algo = get_algo(self.search_algo)

        # special requirement for Nevergrad, need a algorithm setting
        if self.search_algo == "Nevergrad" and len(self.search_algo_settings) == 0:
            warnings.warn("No algorithm setting for Nevergrad find, use NGOpt.")
            import nevergrad as ng

            self.search_algo_settings = {"optimizer": ng.optimizers.NGOpt}
            # raise AttributeError(
            #     "Search algorithm Nevergrad requires Nevergrad optimizer. \
            #     Example: self.search_algo_settings = {'optimizer': nevergrad.optimizers.NGOpt}."
            # )

        # set trainable
        trainer = tune.with_parameters(
            ObjectiveTrainer,
            _X=_X,
            _y=_y,
            encoder=encoder,
            imputer=imputer,
            balancing=balancing,
            scaling=scaling,
            feature_selection=feature_selection,
            models=models,
            model_name=self.model_name,
            task_mode=self.task_mode,
            objective=self.objective,
            validation=self.validation,
            valid_size=self.valid_size,
            full_status=self.full_status,
            reset_index=self.reset_index,
            _iter=self._iter,
            seed=self.seed,
        )

        # get search scheduler
        scheduler = get_scheduler(self.search_scheduler)

        # get callback logger
        logger = get_logger(self.logger)

        # get progress reporter
        progress_reporter = get_progress_reporter(
            self.progress_reporter,
            self.max_evals,
            self.max_error,
        )

        # initialize stopper
        stopper = TimePlateauStopper(
            timeout=self.timeout,
            metric="loss",
            std=0.1,
            num_results=2,
            grace_period=2,
            mode="min",
        )

        # initialize ray
        # if already initialized, do nothing
        if not ray.is_initialized():
            ray.init(
                # local_mode=True,
                num_cpus=self.cpu_threads,
                num_gpus=self.gpu_count,
            )
        # check if ray is initialized
        assert ray.is_initialized() == True, "Ray is not initialized."

        # trial directory name
        def trial_str_creator(trial):
            trialname = "iter_{}_id_{}".format(self._iter + 1, trial.trial_id)
            self._iter += 1
            return trialname

        # optimization process
        # partially activated objective function
        fit_analysis = tune.run(
            # tune.with_parameters(
            #     self._objective,
            #     _X=_X,
            #     _y=_y,
            #     encoder=encoder,
            #     imputer=imputer,
            #     balancing=balancing,
            #     scaling=scaling,
            #     feature_selection=feature_selection,
            #     models=models,
            # ),
            trainer,
            config=hyperparameter_space,
            name=self.model_name,  # name of the tuning process, use model_name
            # resume="AUTO",
            checkpoint_freq=8,  # disable checkpoint
            checkpoint_at_end=True,
            keep_checkpoints_num=4,
            checkpoint_score_attr="loss",
            mode="min",  # always call a minimization process
            search_alg=algo(**self.search_algo_settings),
            scheduler=scheduler(**self.search_scheduler_settings),
            metric="loss",
            num_samples=self.max_evals,
            max_failures=self.max_error,
            stop=stopper,  # use stopper
            callbacks=logger,
            # time_budget_s=self.timeout,  # included in stopper
            progress_reporter=progress_reporter,
            verbose=self.verbose,
            trial_dirname_creator=trial_str_creator,
            local_dir=self.temp_directory,
            log_to_file=True,
        )

        # shut down ray
        ray.shutdown()
        # check if ray is shutdown
        assert ray.is_initialized() == False, "Ray is not shutdown."

        # get the best config settings
        best_trial_id = str(
            fit_analysis.get_best_trial(metric="loss", mode="min", scope="all").trial_id
        )
        # find the exact path
        best_path = find_exact_path(
            os.path.join(self.temp_directory, self.model_name), "id_" + best_trial_id
        )
        best_path = os.path.join(best_path, self.model_name)

        # select optimal settings and fit optimal pipeline
        self._fit_optimal(fit_analysis.best_config, best_path)

        # whether to retain temp files
        if self.delete_temp_after_terminate:
            shutil.rmtree(self.temp_directory)

        self._fitted = True

        return self

    def predict(self, X):

        if self.reset_index:
            # reset index to avoid indexing error
            X.reset_index(drop=True, inplace=True)

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
