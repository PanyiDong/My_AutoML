import sys
from pandas.core.algorithms import isin
from pandas.core.frame import DataFrame

sys.setrecursionlimit(10000)  # add recursive depth
import os
import shutil
import warnings
import numpy as np
import pandas as pd
import scipy
import scipy.stats
import sklearn
import mlflow
import hyperopt
from hyperopt import (
    fmin,
    hp,
    rand,
    tpe,
    atpe,
    Trials,
    SparkTrials,
    space_eval,
    STATUS_OK,
    pyll,
)
from sklearn.utils._testing import ignore_warnings
from sklearn.exceptions import ConvergenceWarning

import My_AutoML
from ._base import no_processing
from ._utils import type_of_task
from ._hyperparameters import (
    encoder_hyperparameter,
    imputer_hyperparameter,
    scaling_hyperparameter,
    balancing_hyperparameter,
    feature_selection_hyperparameter,
    classifiers,
    classifier_hyperparameter,
    regressors,
    regressor_hyperparameter,
)

# filter certain warnings
warnings.filterwarnings("ignore", message="The dataset is balanced, no change.")
warnings.filterwarnings("ignore", message="Variables are collinear")
warnings.filterwarnings("ignore", category=UserWarning)

"""
Classifiers/Hyperparameters from autosklearn:
1. AdaBoost: n_estimators, learning_rate, algorithm, max_depth
2. Bernoulli naive Bayes: alpha, fit_prior
3. Decision Tree: criterion, max_features, max_depth_factor, min_samples_split, 
            min_samples_leaf, min_weight_fraction_leaf, max_leaf_nodes, min_impurity_decrease
4. Extra Trees: criterion, min_samples_leaf, min_samples_split,  max_features, 
            bootstrap, max_leaf_nodes, max_depth, min_weight_fraction_leaf, min_impurity_decrease
5. Gaussian naive Bayes
6. Gradient boosting: loss, learning_rate, min_samples_leaf, max_depth,
            max_leaf_nodes, max_bins, l2_regularization, early_stop, tol, scoring
7. KNN: n_neighbors, weights, p
8. LDA: shrinkage, tol
9. Linear SVC (LibLinear): penalty, loss, dual, tol, C, multi_class, 
            fit_intercept, intercept_scaling
10. kernel SVC (LibSVM): C, kernel, gamma, shrinking, tol, max_iter
11. MLP (Multilayer Perceptron): hidden_layer_depth, num_nodes_per_layer, activation, alpha,
            learning_rate_init, early_stopping, solver, batch_size, n_iter_no_change, tol,
            shuffle, beta_1, beta_2, epsilon
12. Multinomial naive Bayes: alpha, fit_prior
13. Passive aggressive: C, fit_intercept, tol, loss, average
14. QDA: reg_param
15. Random forest: criterion, max_features, max_depth, min_samples_split, 
            min_samples_leaf, min_weight_fraction_leaf, bootstrap, max_leaf_nodes
16. SGD (Stochastic Gradient Descent): loss, penalty, alpha, fit_intercept, tol,
            learning_rate
"""

# Auto binary classifier
class AutoClassifier:

    """
    Perform model selection and hyperparameter optimization for classification tasks
    using sklearn models, predefine hyperparameters

    Parameters
    ----------
    timeout: Total time limit for the job in seconds, default = 360
    
    max_evals: Maximum number of function evaluations allowed, default = 32

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
    support ('AdaboostClassifier', 'BernoulliNB', 'DecisionTree', 'ExtraTreesClassifier',
            'GaussianNB', 'GradientBoostingClassifier', 'KNearestNeighborsClassifier',
            'LDA', 'LibLinear_SVC', 'LibSVM_SVC', 'MLPClassifier', 'MultinomialNB',
            'PassiveAggressive', 'QDA', 'RandomForest',  'SGD')
    'auto' will select all default models, or use a list to select

    validation: Whether to use train_test_split to test performance on test set, default = True
    
    test_size: Test percentage used to evaluate the performance, default = 0.15
    only effective when validation = True

    objective: Objective function to test performance, default = 'accuracy'
    support ("accuracy", "precision", "auc", "hinge", "f1")
    
    method: Model selection/hyperparameter optimization methods, default = 'Bayesian'
    
    algo: Search algorithm, default = 'tpe'
    support (rand, tpe, atpe)
    
    spark_trials: Whether to use SparkTrials, default = False

    progressbar: Whether to show progress bar, default = False
    
    seed: Random seed, default = 1
    """

    def __init__(
        self,
        timeout=360,
        max_evals=64,
        temp_directory="tmp",
        delete_temp_after_terminate=False,
        encoder="auto",
        imputer="auto",
        balancing="auto",
        scaling="auto",
        feature_selection="auto",
        models="auto",
        validation=True,
        test_size=0.15,
        objective="accuracy",
        method="Bayesian",
        algo="tpe",
        spark_trials=False,
        progressbar=False,
        seed=1,
    ):
        self.timeout = timeout
        self.max_evals = max_evals
        self.temp_directory = temp_directory
        self.delete_temp_after_terminate = delete_temp_after_terminate
        self.encoder = encoder
        self.imputer = imputer
        self.balancing = balancing
        self.scaling = scaling
        self.feature_selection = feature_selection
        self.models = models
        self.validation = validation
        self.test_size = test_size
        self.objective = objective
        self.method = method
        self.algo = algo
        self.spark_trials = spark_trials
        self.progressbar = progressbar
        self.seed = seed

        self._iter = 0  # record iteration number

    # create hyperparameter space using Hyperopt.hp.choice
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
                if item["encoder"] == _encoder:
                    _encoding_hyperparameter.append(item)

        _encoding_hyperparameter = hp.choice(
            "classification_encoders", _encoding_hyperparameter
        )

        # imputation space
        _imputer_hyperparameter = []
        if not X.isnull().values.any():  # if no missing, no need for imputation
            _imputer_hyperparameter = hp.choice(
                "classification_imputers", [{"imputer": "no_processing"}]
            )
        else:
            for _imputer in [*imputer]:
                for (
                    item
                ) in imputers_hyperparameters:  # search the imputer' hyperparameters
                    if item["imputer"] == _imputer:
                        _imputer_hyperparameter.append(item)

            _imputer_hyperparameter = hp.choice(
                "classification_imputers", _imputer_hyperparameter
            )

        # balancing space
        _balancing_hyperparameter = []
        for _balancing in [*balancing]:
            for (
                item
            ) in balancings_hyperparameters:  # search the balancings' hyperparameters
                if item["balancing"] == _balancing:
                    _balancing_hyperparameter.append(item)

        _balancing_hyperparameter = hp.choice(
            "classification_balancing", _balancing_hyperparameter
        )
        
        # scaling space
        _scaling_hyperparameter = []
        for _scaling in [*scaling]:
            for (
                item
            ) in scalings_hyperparameters:  # search the scalings' hyperparameters
                if item["scaling"] == _scaling:
                    _scaling_hyperparameter.append(item)

        _scaling_hyperparameter = hp.choice(
            "classification_scaling", _scaling_hyperparameter
        )

        # feature selection space
        _feature_selection_hyperparameter = []
        for _feature_selection in [*feature_selection]:
            for (
                item
            ) in (
                feature_selection_hyperparameters
            ):  # search the feature selections' hyperparameters
                if item["feature_selection"] == _feature_selection:
                    _feature_selection_hyperparameter.append(item)

        _feature_selection_hyperparameter = hp.choice(
            "classification_feature_selection", _feature_selection_hyperparameter
        )

        # model selection and hyperparameter optimization space
        _model_hyperparameter = []
        for _model in [*models]:
            # checked before at models that all models are in default space
            for item in models_hyperparameters:  # search the models' hyperparameters
                if item["model"] == _model:
                    _model_hyperparameter.append(item)

        _model_hyperparameter = hp.choice(
            "classification_models", _model_hyperparameter
        )

        # the pipeline search space
        return pyll.as_apply(
            {
                "encoder": _encoding_hyperparameter,
                "imputer": _imputer_hyperparameter,
                "balancing": _balancing_hyperparameter,
                "scaling": _scaling_hyperparameter,
                "feature_selection": _feature_selection_hyperparameter,
                "classification": _model_hyperparameter,
            }
        )

    # initialize and get hyperparameter search space
    def get_hyperparameter_space(self, X, y):

        # initialize default search options
        # all encoders available
        self._all_encoders = My_AutoML.encoders

        # all hyperparameters for encoders
        self._all_encoders_hyperparameters = encoder_hyperparameter

        # all imputers available
        self._all_imputers = My_AutoML.imputers

        # all hyperparemeters for imputers
        self._all_imputers_hyperparameters = imputer_hyperparameter

        # all scalings available
        self._all_scalings = My_AutoML.scalings

        # all balancings available
        self._all_balancings = My_AutoML.balancing

        # all hyperparameters for balancing methods
        self._all_balancings_hyperparameters = balancing_hyperparameter
        
        # all hyperparameters for scalings
        self._all_scalings_hyperparameters = scaling_hyperparameter
        
        # all feature selections available
        self._all_feature_selection = My_AutoML.feature_selection
        # special treatment, remove some feature selection for regression
        del self._all_feature_selection["extra_trees_preproc_for_regression"]
        del self._all_feature_selection["select_percentile_regression"]
        del self._all_feature_selection["select_rates_regression"]
        if X.shape[0] * X.shape[1] > 10000 :
            del self._all_feature_selection["liblinear_svc_preprocessor"]

        # all hyperparameters for feature selections
        self._all_feature_selection_hyperparameters = feature_selection_hyperparameter

        # all classification models available
        self._all_models = classifiers
        # special treatment, remove SVM methods when observations are large
        # SVM suffers from the complexity o(n_samples^2 * n_features), 
        # which is time-consuming for large datasets
        if X.shape[0] * X.shape[1] > 10000 :
            del self._all_models["LibLinear_SVC"]
            del self._all_models["LibSVM_SVC"]

        # all hyperparameters for the classification models
        self._all_models_hyperparameters = classifier_hyperparameter

        self.hyperparameter_space = None

        # Encoding
        # convert string types to numerical type
        # get encoder space
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

        # Imputer
        # fill missing values
        # get imputer space
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

        # Balancing
        # deal with imbalanced dataset, using over-/under-sampling methods
        # get balancing space
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
        
        # Scaling
        # get scaling space
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

        # Feature selection
        # Remove redundant features, reduce dimensionality
        # get feature selection space
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

        # Model selection/Hyperparameter optimization
        # using Bayesian Optimization
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

        # initialize the hyperparameter space
        _all_encoders_hyperparameters = self._all_encoders_hyperparameters.copy()
        _all_imputers_hyperparameters = self._all_imputers_hyperparameters.copy()
        _all_balancings_hyperparameters = self._all_balancings_hyperparameters.copy()
        _all_scalings_hyperparameters = self._all_scalings_hyperparameters.copy()
        _all_feature_selection_hyperparameters = (
            self._all_feature_selection_hyperparameters.copy()
        )
        _all_models_hyperparameters = self._all_models_hyperparameters.copy()

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

    # select optimal settings and fit on optimal hyperparameters
    def _fit_optimal(self, best_results, _X, _y):

        # mapping the optimal model and hyperparameters selected
        # fit the optimal setting
        optimal_point = space_eval(self.hyperparameter_space, best_results)
        # optimal encoder
        self.optimal_encoder_hyperparameters = optimal_point["encoder"]
        self.optimal_encoder = self.optimal_encoder_hyperparameters["encoder"]
        del self.optimal_encoder_hyperparameters["encoder"]
        # optimal imputer
        self.optimal_imputer_hyperparameters = optimal_point["imputer"]
        self.optimal_imputer = self.optimal_imputer_hyperparameters["imputer"]
        del self.optimal_imputer_hyperparameters["imputer"]
        # optimal balancing
        self.optimal_balancing_hyperparameters = optimal_point["balancing"]
        self.optimal_balancing = self.optimal_balancing_hyperparameters["balancing"]
        del self.optimal_balancing_hyperparameters["balancing"]
        # optimal scaling
        self.optimal_scaling_hyperparameters = optimal_point["scaling"]
        self.optimal_scaling = self.optimal_scaling_hyperparameters["scaling"]
        del self.optimal_scaling_hyperparameters["scaling"]
        # optimal feature selection
        self.optimal_feature_selection_hyperparameters = optimal_point[
            "feature_selection"
        ]
        self.optimal_feature_selection = self.optimal_feature_selection_hyperparameters[
            "feature_selection"
        ]
        del self.optimal_feature_selection_hyperparameters["feature_selection"]
        # optimal classifier
        self.optimal_classifier_hyperparameters = optimal_point[
            "classification"
        ]  # optimal model selected
        self.optimal_classifier = self.optimal_classifier_hyperparameters[
            "model"
        ]  # optimal hyperparameter settings selected
        del self.optimal_classifier_hyperparameters["model"]
        
        # record optimal settings
        with open(self.temp_directory + "/optimal_setting.txt", "w") as f:
            f.write("Optimal encoding method is: {}.\n".format(self.optimal_encoder))
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
                "Optimal classification model is: {}\n".format(self.optimal_classifier)
            )
            f.write("Optimal classification hyperparameters:")
            print(self.optimal_classifier_hyperparameters, file=f, end="\n\n")

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
        self._fit_scaling.fit(_X)
        _X = self._fit_scaling.transform(_X)
        # feature selection
        self._fit_feature_selection = self._all_feature_selection[
            self.optimal_feature_selection
        ](**self.optimal_feature_selection_hyperparameters)
        self._fit_feature_selection.fit(_X, _y)
        _X = self._fit_feature_selection.transform(_X)
        # classification
        self._fit_classifier = self._all_models[self.optimal_classifier](
            **self.optimal_classifier_hyperparameters
        )
        self._fit_classifier.fit(_X, _y.values.ravel())

        return self

    def fit(self, X, y):

        # initialize temp directory
        # check if temp directory exists, if exists, empty it
        if os.path.isdir(self.temp_directory):
            shutil.rmtree(self.temp_directory)
        os.makedirs(self.temp_directory)

        # write basic information to init.txt
        with open(self.temp_directory + "/init.txt", "w") as f:
            f.write("Features of the dataset: {}\n".format(list(X.columns)))
            f.write(
                "Shape of the design matrix: {} * {}".format(X.shape[0], X.shape[1])
            )
            f.write("Response of the dataset: {}\n".format(list(y.columns)))
            f.write(
                "Shape of the response vector: {} * {}".format(y.shape[0], y.shape[1])
            )
            f.write("Type of the task: Classification.\n")

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

        if self.validation:  # only perform train_test_split when validation
            # train test split so the performance of model selection and
            # hyperparameter optimization can be evaluated
            from sklearn.model_selection import train_test_split

            X_train, X_test, y_train, y_test = train_test_split(
                _X, _y, test_size=self.test_size, random_state=self.seed
            )

        # the objective function of Bayesian Optimization tries to minimize
        # use accuracy score
        @ignore_warnings(category=ConvergenceWarning)
        def _objective(params):
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
                    'Only support ["accuracy", "precision", "auc", "hinge", "f1"], get{}'.format(
                        self.objective
                    )
                )

            # pipeline of objective, [encoder, imputer, balancing, scaling, feature_selection, model]
            # select encoder and set hyperparameters
            # must have encoder
            _encoder_hyper = params["encoder"]
            _encoder = _encoder_hyper["encoder"]
            del _encoder_hyper["encoder"]
            enc = encoder[_encoder](**_encoder_hyper)

            # select imputer and set hyperparameters
            _imputer_hyper = params["imputer"]
            _imputer = _imputer_hyper["imputer"]
            del _imputer_hyper["imputer"]
            imp = imputer[_imputer](**_imputer_hyper)

            # select balancing and set hyperparameters
            # must have balancing, since no_preprocessing is included
            _balancing_hyper = params["balancing"]
            _balancing = _balancing_hyper["balancing"]
            del _balancing_hyper["balancing"]
            blc = balancing[_balancing](**_balancing_hyper)
            
            # select scaling and set hyperparameters
            # must have scaling, since no_preprocessing is included
            _scaling_hyper = params["scaling"]
            _scaling = _scaling_hyper["scaling"]
            del _scaling_hyper["scaling"]
            scl = scaling[_scaling](**_scaling_hyper)

            # select feature selection and set hyperparameters
            # must have feature selection, since no_preprocessing is included
            _feature_selection_hyper = params["feature_selection"]
            _feature_selection = _feature_selection_hyper["feature_selection"]
            del _feature_selection_hyper["feature_selection"]
            fts = feature_selection[_feature_selection](**_feature_selection_hyper)

            # select classifier model and set hyperparameters
            # must have a classifier
            _classifier_hyper = params["classification"]
            _classifier = _classifier_hyper["model"]
            del _classifier_hyper["model"]
            clf = models[_classifier](
                **_classifier_hyper
            )  # call the model using passed parameters

            obj_tmp_directory = self.temp_directory + "/iter_" + str(self._iter + 1)
            if not os.path.isdir(obj_tmp_directory):
                os.makedirs(obj_tmp_directory)

            with open(obj_tmp_directory + "/hyperparameter_settings.txt", "w") as f:
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
                f.write("Classification model: {}\n".format(_classifier))
                f.write("Classifier Hyperparameters:")
                print(_classifier_hyper, file=f, end="\n\n")

            if self.validation:
                _X_train_obj, _X_test_obj = X_train.copy(), X_test.copy()
                _y_train_obj, _y_test_obj = y_train.copy(), y_test.copy()

                # encoding
                _X_train_obj = enc.fit(_X_train_obj)
                _X_test_obj = enc.refit(_X_test_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Encoding finished, in imputation process.")
                # imputer
                _X_train_obj = imp.fill(_X_train_obj)
                _X_test_obj = imp.fill(_X_test_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Imputation finished, in scaling process.")
                # balancing
                _X_train_obj, _y_train_obj = blc.fit_transform(
                    _X_train_obj, _y_train_obj
                )
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Balancing finished, in scaling process.")

                # make sure the classes are integers (belongs to certain classes)
                _y_train_obj = _y_train_obj.astype(int)
                _y_test_obj = _y_test_obj.astype(int)
                # scaling
                scl.fit(_X_train_obj, _y_train_obj)
                _X_train_obj = scl.transform(_X_train_obj)
                _X_test_obj = scl.transform(_X_test_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Scaling finished, in feature selection process.")
                # feature selection
                fts.fit(_X_train_obj, _y_train_obj)
                _X_train_obj = fts.transform(_X_train_obj)
                _X_test_obj = fts.transform(_X_test_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Feature selection finished, in classification model.")
                if scipy.sparse.issparse(_X_train_obj) : # check if returns sparse matrix
                    _X_train_obj = _X_train_obj.toarray()
                if scipy.sparse.issparse(_X_test_obj) :
                    _X_test_obj = _X_test_obj.toarray()
                # classification

                # store preprocessed train/test datasets
                if isinstance(_X_train_obj, np.ndarray) : # in case numpy array is returned
                    pd.concat([pd.DataFrame(_X_train_obj), _y_train_obj], axis=1, ignore_index=True).to_csv(
                        obj_tmp_directory + "/train_preprocessed.csv", index=False
                    )
                elif isinstance(_X_train_obj, pd.DataFrame) :
                    pd.concat([_X_train_obj, _y_train_obj], axis=1).to_csv(
                        obj_tmp_directory + "/train_preprocessed.csv", index=False
                    )
                else :
                    raise TypeError(
                        "Only accept numpy array or pandas dataframe!"
                    )
                
                if isinstance(_X_test_obj, np.ndarray) :
                    pd.concat([pd.DataFrame(_X_test_obj), _y_test_obj], axis=1, ignore_index=True).to_csv(
                        obj_tmp_directory + "/test_preprocessed.csv", index=False
                    )
                elif isinstance(_X_test_obj, pd.DataFrame) :
                    pd.concat([_X_test_obj, _y_test_obj], axis=1).to_csv(
                        obj_tmp_directory + "/test_preprocessed.csv", index=False
                    )
                else :
                    raise TypeError(
                        "Only accept numpy array or pandas dataframe!"
                    )

                clf.fit(_X_train_obj, _y_train_obj.values.ravel())
                os.remove(obj_tmp_directory + "/objective_process.txt")

                y_pred = clf.predict(_X_test_obj)
                _loss = -_obj(y_pred, _y_test_obj.values)

                with open(obj_tmp_directory + "/testing_objective.txt", "w") as f:
                    f.write("Loss from objective function is: {:.6f}\n".format(_loss))
                    f.write("Loss is calculate using {}.".format(self.objective))
                self._iter += 1

                # since fmin of Hyperopt tries to minimize the objective function, take negative accuracy here
                return {"loss": _loss, "status": STATUS_OK}
            else:
                _X_obj = _X.copy()
                _y_obj = _y.copy()

                # encoding
                _X_obj = enc.fit(_X_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Encoding finished, in imputation process.")
                # imputer
                _X_obj = imp.fill(_X_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Imputation finished, in scaling process.")
                # balancing
                _X_obj = blc.fit_transform(_X_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Balancing finished, in feature selection process.")
                # scaling
                scl.fit(_X_obj, _y_obj)
                _X_obj = scl.transform(_X_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Scaling finished, in balancing process.")
                # feature selection
                fts.fit(_X_obj, _y_obj)
                _X_obj = fts.transform(_X_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Feature selection finished, in classification model.")
                # classification
                clf.fit(_X_obj.values, _y_obj.values.ravel())
                pd.concat([_X_obj, _y_obj], axis=1).to_csv(
                    obj_tmp_directory + "/data_preprocessed.csv", index=False
                )
                os.remove(obj_tmp_directory + "/objective_process.txt")

                y_pred = clf.predict(_X_obj.values)
                _loss = -_obj(y_pred, _y_obj.values)

                with open(obj_tmp_directory + "/testing_objective.txt", "w") as f:
                    f.write("Loss from objective function is: {.6f}\n".format(_loss))
                    f.write("Loss is calculate using {}.".format(self.objective))
                self._iter += 1

                return {"loss": _loss, "status": STATUS_OK}

        # call hyperopt to use Bayesian Optimization for Model Selection and Hyperparameter Selection

        # search algorithm
        if self.algo == "rand":
            algo = rand.suggest
        elif self.algo == "tpe":
            algo = tpe.suggest
        elif self.algo == "atpe":
            algo = atpe.suggest

        # Storage for evaluation points
        if self.spark_trials:
            trials = SparkTrials()
        else:
            trials = Trials()

        # run fmin to search for optimal hyperparameter settings
        with mlflow.start_run():
            best_results = fmin(
                fn=_objective,
                space=self.hyperparameter_space,
                algo=algo,
                max_evals=self.max_evals,
                timeout=self.timeout,
                trials=trials,
                show_progressbar=self.progressbar,
                rstate=np.random.RandomState(seed=self.seed),
            )

        # select optimal settings and fit optimal pipeline
        self._fit_optimal(best_results, _X, _y)

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

        return self._fit_classifier.predict(_X)


"""
Regressors/Hyperparameters from sklearn:
1. AdaBoost: n_estimators, learning_rate, loss, max_depth
2. Ard regression: n_iter, tol, alpha_1, alpha_2, lambda_1, lambda_2,
            threshold_lambda, fit_intercept
3. Decision tree: criterion, max_features, max_depth_factor,
            min_samples_split, min_samples_leaf, min_weight_fraction_leaf,
            max_leaf_nodes, min_impurity_decrease
4. extra trees: criterion, min_samples_leaf, min_samples_split, 
            max_features, bootstrap, max_leaf_nodes, max_depth, 
            min_weight_fraction_leaf, min_impurity_decrease
5. Gaussian Process: alpha, thetaL, thetaU
6. Gradient boosting: loss, learning_rate, min_samples_leaf, max_depth,
            max_leaf_nodes, max_bins, l2_regularization, early_stop, tol, scoring
7. KNN: n_neighbors, weights, p
8. Linear SVR (LibLinear): loss, epsilon, dual, tol, C, fit_intercept,
            intercept_scaling
9. Kernel SVR (LibSVM): kernel, C, epsilon, tol, shrinking
10. Random forest: criterion, max_features, max_depth, min_samples_split, 
            min_samples_leaf, min_weight_fraction_leaf, bootstrap, 
            max_leaf_nodes, min_impurity_decrease
11. SGD (Stochastic Gradient Descent): loss, penalty, alpha, fit_intercept, tol,
            learning_rate
12. MLP (Multilayer Perceptron): hidden_layer_depth, num_nodes_per_layer, 
            activation, alpha, learning_rate_init, early_stopping, solver, 
            batch_size, n_iter_no_change, tol, shuffle, beta_1, beta_2, epsilon
"""


class AutoRegressor:

    """
    Perform model selection and hyperparameter optimization for regression tasks
    using sklearn models, predefine hyperparameters

    Parameters
    ----------
    timeout: Total time limit for the job in seconds, default = 360
    
    max_evals: Maximum number of function evaluations allowed, default = 32

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
    'FeatureFilter', 'ASFFS', 'GeneticAlgorithm', 'extra_trees_preproc_for_regression',
    'fast_ica', 'feature_agglomeration', 'kernel_pca', 'kitchen_sinks', 
    'liblinear_svc_preprocessor', 'nystroem_sampler', 'pca', 'polynomial', 
    'random_trees_embedding', 'select_percentile_regression','select_rates_regression', 
    'truncatedSVD')
    'auto' will select all default feature selections, or use a list to select
    
    models: Models selected for the job, default = 'auto'
    support ("AdaboostRegressor", "ARDRegression", "DecisionTree", "ExtraTreesRegressor",
    "GaussianProcess", "GradientBoosting", "KNearestNeighborsRegressor", "LibLinear_SVR",
    "LibSVM_SVR", "MLPRegressor", "RandomForest", "SGD")
    'auto' will select all default models, or use a list to select

    validation: Whether to use train_test_split to test performance on test set, default = True
    
    test_size: Test percentage used to evaluate the performance, default = 0.15
    only effective when validation = True

    objective: Objective function to test performance, default = 'MSE'
    support ("MSE", "MAE", "MSLE", "R2", "MAX")
    
    method: Model selection/hyperparameter optimization methods, default = 'Bayesian'
    
    algo: Search algorithm, default = 'tpe'
    support (rand, tpe, atpe)
    
    spark_trials: Whether to use SparkTrials, default = False

    progressbar: Whether to show progress bar, default = False
    
    seed: Random seed, default = 1
    """

    def __init__(
        self,
        timeout=360,
        max_evals=64,
        temp_directory="tmp",
        delete_temp_after_terminate=False,
        encoder="auto",
        imputer="auto",
        balancing="auto",
        scaling="auto",
        feature_selection="auto",
        models="auto",
        validation=True,
        test_size=0.15,
        objective="MSE",
        method="Bayesian",
        algo="tpe",
        spark_trials=False,
        progressbar=False,
        seed=1,
    ):
        self.timeout = timeout
        self.max_evals = max_evals
        self.temp_directory = temp_directory
        self.delete_temp_after_terminate = delete_temp_after_terminate
        self.encoder = encoder
        self.imputer = imputer
        self.balancing = balancing
        self.scaling = scaling
        self.feature_selection = feature_selection
        self.models = models
        self.validation = validation
        self.test_size = test_size
        self.objective = objective
        self.method = method
        self.algo = algo
        self.spark_trials = spark_trials
        self.progressbar = progressbar
        self.seed = seed

        self._iter = 0  # record iteration number

    # create hyperparameter space using Hyperopt.hp.choice
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
                if item["encoder"] == _encoder:
                    _encoding_hyperparameter.append(item)

        _encoding_hyperparameter = hp.choice(
            "regression_encoders", _encoding_hyperparameter
        )

        # imputation space
        _imputer_hyperparameter = []
        if not X.isnull().values.any():  # if no missing, no need for imputation
            _imputer_hyperparameter = hp.choice(
                "regression_imputers", [{"imputer": "no_processing"}]
            )
        else:
            for _imputer in [*imputer]:
                for (
                    item
                ) in imputers_hyperparameters:  # search the imputer' hyperparameters
                    if item["imputer"] == _imputer:
                        _imputer_hyperparameter.append(item)

            _imputer_hyperparameter = hp.choice(
                "regression_imputers", _imputer_hyperparameter
            )

        # balancing space
        _balancing_hyperparameter = []
        for _balancing in [*balancing]:
            for (
                item
            ) in balancings_hyperparameters:  # search the balancings' hyperparameters
                if item["balancing"] == _balancing:
                    _balancing_hyperparameter.append(item)

        _balancing_hyperparameter = hp.choice(
            "regression_balancing", _balancing_hyperparameter
        )
        
        # scaling space
        _scaling_hyperparameter = []
        for _scaling in [*scaling]:
            for (
                item
            ) in scalings_hyperparameters:  # search the scalings' hyperparameters
                if item["scaling"] == _scaling:
                    _scaling_hyperparameter.append(item)

        _scaling_hyperparameter = hp.choice(
            "regression_scaling", _scaling_hyperparameter
        )

        # feature selection space
        _feature_selection_hyperparameter = []
        for _feature_selection in [*feature_selection]:
            for (
                item
            ) in (
                feature_selection_hyperparameters
            ):  # search the feature selections' hyperparameters
                if item["feature_selection"] == _feature_selection:
                    _feature_selection_hyperparameter.append(item)

        _feature_selection_hyperparameter = hp.choice(
            "regression_feature_selection", _feature_selection_hyperparameter
        )

        # model selection and hyperparameter optimization space
        _model_hyperparameter = []
        for _model in [*models]:
            # checked before at models that all models are in default space
            for item in models_hyperparameters:  # search the models' hyperparameters
                if item["model"] == _model:
                    _model_hyperparameter.append(item)

        _model_hyperparameter = hp.choice(
            "regression_models", _model_hyperparameter
        )

        # the pipeline search space
        return pyll.as_apply(
            {
                "encoder": _encoding_hyperparameter,
                "imputer": _imputer_hyperparameter,
                "balancing": _balancing_hyperparameter,
                "scaling": _scaling_hyperparameter,
                "feature_selection": _feature_selection_hyperparameter,
                "regression": _model_hyperparameter,
            }
        )

    # initialize and get hyperparameter search space
    def get_hyperparameter_space(self, X, y):

        # initialize default search options
        # all encoders available
        self._all_encoders = My_AutoML.encoders

        # all hyperparameters for encoders
        self._all_encoders_hyperparameters = encoder_hyperparameter

        # all imputers available
        self._all_imputers = My_AutoML.imputers

        # all hyperparemeters for imputers
        self._all_imputers_hyperparameters = imputer_hyperparameter

        # all scalings available
        self._all_scalings = My_AutoML.scalings

        # all balancings available
        self._all_balancings = My_AutoML.balancing

        # all hyperparameters for balancing methods
        self._all_balancings_hyperparameters = balancing_hyperparameter
        
        # all hyperparameters for scalings
        self._all_scalings_hyperparameters = scaling_hyperparameter
        
        # all feature selections available
        self._all_feature_selection = My_AutoML.feature_selection
        # special treatment, remove some feature selection for classification
        del self._all_feature_selection["extra_trees_preproc_for_classification"]
        del self._all_feature_selection["select_percentile_classification"]
        del self._all_feature_selection["select_rates_classification"]
        # remove SVM feature selection since it's time-consuming for large datasets
        if X.shape[0] * X.shape[1] > 10000 :
            del self._all_feature_selection["liblinear_svc_preprocessor"]

        # all hyperparameters for feature selections
        self._all_feature_selection_hyperparameters = feature_selection_hyperparameter

        # all regression models available
        self._all_models = regressors
        # special treatment, remove SVM methods when observations are large
        # SVM suffers from the complexity o(n_samples^2 * n_features), 
        # which is time-consuming for large datasets
        if X.shape[0] * X.shape[1] > 10000 :
            del self._all_models["LibLinear_SVR"]
            del self._all_models["LibSVM_SVR"]

        # all hyperparameters for the regression models
        self._all_models_hyperparameters = regressor_hyperparameter

        self.hyperparameter_space = None

        # Encoding
        # convert string types to numerical type
        # get encoder space
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

        # Imputer
        # fill missing values
        # get imputer space
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

        # Balancing
        # deal with imbalanced dataset, using over-/under-sampling methods
        # get balancing space
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
        
        # Scaling
        # get scaling space
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

        # Feature selection
        # Remove redundant features, reduce dimensionality
        # get feature selection space
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

        # Model selection/Hyperparameter optimization
        # using Bayesian Optimization
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

        # initialize the hyperparameter space
        _all_encoders_hyperparameters = self._all_encoders_hyperparameters.copy()
        _all_imputers_hyperparameters = self._all_imputers_hyperparameters.copy()
        _all_balancings_hyperparameters = self._all_balancings_hyperparameters.copy()
        _all_scalings_hyperparameters = self._all_scalings_hyperparameters.copy()
        _all_feature_selection_hyperparameters = (
            self._all_feature_selection_hyperparameters.copy()
        )
        _all_models_hyperparameters = self._all_models_hyperparameters.copy()

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

    # select optimal settings and fit on optimal hyperparameters
    def _fit_optimal(self, best_results, _X, _y):

        # mapping the optimal model and hyperparameters selected
        # fit the optimal setting
        optimal_point = space_eval(self.hyperparameter_space, best_results)
        # optimal encoder
        self.optimal_encoder_hyperparameters = optimal_point["encoder"]
        self.optimal_encoder = self.optimal_encoder_hyperparameters["encoder"]
        del self.optimal_encoder_hyperparameters["encoder"]
        # optimal imputer
        self.optimal_imputer_hyperparameters = optimal_point["imputer"]
        self.optimal_imputer = self.optimal_imputer_hyperparameters["imputer"]
        del self.optimal_imputer_hyperparameters["imputer"]
        # optimal balancing
        self.optimal_balancing_hyperparameters = optimal_point["balancing"]
        self.optimal_balancing = self.optimal_balancing_hyperparameters["balancing"]
        del self.optimal_balancing_hyperparameters["balancing"]
        # optimal scaling
        self.optimal_scaling_hyperparameters = optimal_point["scaling"]
        self.optimal_scaling = self.optimal_scaling_hyperparameters["scaling"]
        del self.optimal_scaling_hyperparameters["scaling"]
        # optimal feature selection
        self.optimal_feature_selection_hyperparameters = optimal_point[
            "feature_selection"
        ]
        self.optimal_feature_selection = self.optimal_feature_selection_hyperparameters[
            "feature_selection"
        ]
        del self.optimal_feature_selection_hyperparameters["feature_selection"]
        # optimal regressor
        self.optimal_regressor_hyperparameters = optimal_point[
            "regression"
        ]  # optimal model selected
        self.optimal_regressor = self.optimal_regressor_hyperparameters[
            "model"
        ]  # optimal hyperparameter settings selected
        del self.optimal_regressor_hyperparameters["model"]
        
        # record optimal settings
        with open(self.temp_directory + "/optimal_setting.txt", "w") as f:
            f.write("Optimal encoding method is: {}.\n".format(self.optimal_encoder))
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
                "Optimal regression model is: {}\n".format(self.optimal_regressor)
            )
            f.write("Optimal regression hyperparameters:")
            print(self.optimal_regressor_hyperparameters, file=f, end="\n\n")

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
        self._fit_scaling.fit(_X)
        _X = self._fit_scaling.transform(_X)
        # feature selection
        self._fit_feature_selection = self._all_feature_selection[
            self.optimal_feature_selection
        ](**self.optimal_feature_selection_hyperparameters)
        self._fit_feature_selection.fit(_X, _y)
        _X = self._fit_feature_selection.transform(_X)
        # regression
        self._fit_regressor = self._all_models[self.optimal_regressor](
            **self.optimal_regressor_hyperparameters
        )
        self._fit_regressor.fit(_X, _y.values.ravel())

        return self

    def fit(self, X, y):
    
        # initialize temp directory
        # check if temp directory exists, if exists, empty it
        if os.path.isdir(self.temp_directory):
            shutil.rmtree(self.temp_directory)
        os.makedirs(self.temp_directory)

        # write basic information to init.txt
        with open(self.temp_directory + "/init.txt", "w") as f:
            f.write("Features of the dataset: {}\n".format(list(X.columns)))
            f.write(
                "Shape of the design matrix: {} * {}".format(X.shape[0], X.shape[1])
            )
            f.write("Response of the dataset: {}\n".format(list(y.columns)))
            f.write(
                "Shape of the response vector: {} * {}\n".format(y.shape[0], y.shape[1])
            )
            f.write("Type of the task: Regression.\n")

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

        if self.validation:  # only perform train_test_split when validation
            # train test split so the performance of model selection and
            # hyperparameter optimization can be evaluated
            from sklearn.model_selection import train_test_split

            X_train, X_test, y_train, y_test = train_test_split(
                _X, _y, test_size=self.test_size, random_state=self.seed
            )

        # the objective function of Bayesian Optimization tries to minimize
        # use accuracy score
        @ignore_warnings(category=ConvergenceWarning)
        def _objective(params):
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
                from sklearn.metrics import max_error # focus on reducing extreme losses

                _obj = max_error
            else:
                raise ValueError(
                    'Only support ["MSE", "MAE", "MSLE", "R2", "MAX"], get{}'.format(
                        self.objective
                    )
                )

            # pipeline of objective, [encoder, imputer, balancing, scaling, feature_selection, model]
            # select encoder and set hyperparameters
            # must have encoder
            _encoder_hyper = params["encoder"]
            _encoder = _encoder_hyper["encoder"]
            del _encoder_hyper["encoder"]
            enc = encoder[_encoder](**_encoder_hyper)

            # select imputer and set hyperparameters
            _imputer_hyper = params["imputer"]
            _imputer = _imputer_hyper["imputer"]
            del _imputer_hyper["imputer"]
            imp = imputer[_imputer](**_imputer_hyper)

            # select balancing and set hyperparameters
            # must have balancing, since no_preprocessing is included
            _balancing_hyper = params["balancing"]
            _balancing = _balancing_hyper["balancing"]
            del _balancing_hyper["balancing"]
            blc = balancing[_balancing](**_balancing_hyper)
            
            # select scaling and set hyperparameters
            # must have scaling, since no_preprocessing is included
            _scaling_hyper = params["scaling"]
            _scaling = _scaling_hyper["scaling"]
            del _scaling_hyper["scaling"]
            scl = scaling[_scaling](**_scaling_hyper)

            # select feature selection and set hyperparameters
            # must have feature selection, since no_preprocessing is included
            _feature_selection_hyper = params["feature_selection"]
            _feature_selection = _feature_selection_hyper["feature_selection"]
            del _feature_selection_hyper["feature_selection"]
            fts = feature_selection[_feature_selection](**_feature_selection_hyper)

            # select regressor model and set hyperparameters
            # must have a regressor
            _regressor_hyper = params["regression"]
            _regressor = _regressor_hyper["model"]
            del _regressor_hyper["model"]
            reg = models[_regressor](
                **_regressor_hyper
            )  # call the model using passed parameters

            obj_tmp_directory = self.temp_directory + "/iter_" + str(self._iter + 1)
            if not os.path.isdir(obj_tmp_directory):
                os.makedirs(obj_tmp_directory)

            with open(obj_tmp_directory + "/hyperparameter_settings.txt", "w") as f:
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
                f.write("Regression model: {}\n".format(_regressor))
                f.write("Regression Hyperparameters:")
                print(_regressor_hyper, file=f, end="\n\n")

            if self.validation:
                _X_train_obj, _X_test_obj = X_train.copy(), X_test.copy()
                _y_train_obj, _y_test_obj = y_train.copy(), y_test.copy()

                # encoding
                _X_train_obj = enc.fit(_X_train_obj)
                _X_test_obj = enc.refit(_X_test_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Encoding finished, in imputation process.")
                # imputer
                _X_train_obj = imp.fill(_X_train_obj)
                _X_test_obj = imp.fill(_X_test_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Imputation finished, in scaling process.")
                # balancing
                _X_train_obj, _y_train_obj = blc.fit_transform(
                    _X_train_obj, _y_train_obj
                )
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Balancing finished, in scaling process.")

                # make sure the classes are integers (belongs to certain classes)
                _y_train_obj = _y_train_obj.astype(int)
                _y_test_obj = _y_test_obj.astype(int)
                # scaling
                scl.fit(_X_train_obj, _y_train_obj)
                _X_train_obj = scl.transform(_X_train_obj)
                _X_test_obj = scl.transform(_X_test_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Scaling finished, in feature selection process.")
                # feature selection
                fts.fit(_X_train_obj, _y_train_obj)
                _X_train_obj = fts.transform(_X_train_obj)
                _X_test_obj = fts.transform(_X_test_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Feature selection finished, in regression model.")
                if scipy.sparse.issparse(_X_train_obj) : # check if returns sparse matrix
                    _X_train_obj = _X_train_obj.toarray()
                if scipy.sparse.issparse(_X_test_obj) :
                    _X_test_obj = _X_test_obj.toarray()
                # regression

                # store the preprocessed train/test datasets
                if isinstance(_X_train_obj, np.ndarray) : # in case numpy array is returned
                    pd.concat([pd.DataFrame(_X_train_obj), _y_train_obj], axis=1, ignore_index=True).to_csv(
                        obj_tmp_directory + "/train_preprocessed.csv", index=False
                    )
                elif isinstance(_X_train_obj, pd.DataFrame) :
                    pd.concat([_X_train_obj, _y_train_obj], axis=1).to_csv(
                        obj_tmp_directory + "/train_preprocessed.csv", index=False
                    )
                else :
                    raise TypeError(
                        "Only accept numpy array or pandas dataframe!"
                    )
                
                if isinstance(_X_test_obj, np.ndarray) :
                    pd.concat([pd.DataFrame(_X_test_obj), _y_test_obj], axis=1, ignore_index=True).to_csv(
                        obj_tmp_directory + "/test_preprocessed.csv", index=False
                    )
                elif isinstance(_X_test_obj, pd.DataFrame) :
                    pd.concat([_X_test_obj, _y_test_obj], axis=1).to_csv(
                        obj_tmp_directory + "/test_preprocessed.csv", index=False
                    )
                else :
                    raise TypeError(
                        "Only accept numpy array or pandas dataframe!"
                    )

                reg.fit(_X_train_obj, _y_train_obj.values.ravel())
                os.remove(obj_tmp_directory + "/objective_process.txt")

                y_pred = reg.predict(_X_test_obj)
                _loss = -_obj(y_pred, _y_test_obj.values)

                with open(obj_tmp_directory + "/testing_objective.txt", "w") as f:
                    f.write("Loss from objective function is: {:.6f}\n".format(_loss))
                    f.write("Loss is calculate using {}.".format(self.objective))
                self._iter += 1

                # since fmin of Hyperopt tries to minimize the objective function, take negative accuracy here
                return {"loss": _loss, "status": STATUS_OK}
            else:
                _X_obj = _X.copy()
                _y_obj = _y.copy()

                # encoding
                _X_obj = enc.fit(_X_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Encoding finished, in imputation process.")
                # imputer
                _X_obj = imp.fill(_X_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Imputation finished, in scaling process.")
                # balancing
                _X_obj = blc.fit_transform(_X_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Balancing finished, in feature selection process.")
                # scaling
                scl.fit(_X_obj, _y_obj)
                _X_obj = scl.transform(_X_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Scaling finished, in balancing process.")
                # feature selection
                fts.fit(_X_obj, _y_obj)
                _X_obj = fts.transform(_X_obj)
                with open(obj_tmp_directory + "/objective_process.txt", "w") as f:
                    f.write("Feature selection finished, in regression model.")
                # regression
                reg.fit(_X_obj.values, _y_obj.values.ravel())
                pd.concat([_X_obj, _y_obj], axis=1).to_csv(
                    obj_tmp_directory + "/data_preprocessed.csv", index=False
                )
                os.remove(obj_tmp_directory + "/objective_process.txt")

                y_pred = reg.predict(_X_obj.values)
                _loss = -_obj(y_pred, _y_obj.values)

                with open(obj_tmp_directory + "/testing_objective.txt", "w") as f:
                    f.write("Loss from objective function is: {.6f}\n".format(_loss))
                    f.write("Loss is calculate using {}.".format(self.objective))
                self._iter += 1

                return {"loss": _loss, "status": STATUS_OK}

        # call hyperopt to use Bayesian Optimization for Model Selection and Hyperparameter Selection

        # search algorithm
        if self.algo == "rand":
            algo = rand.suggest
        elif self.algo == "tpe":
            algo = tpe.suggest
        elif self.algo == "atpe":
            algo = atpe.suggest

        # Storage for evaluation points
        if self.spark_trials:
            trials = SparkTrials()
        else:
            trials = Trials()

        # run fmin to search for optimal hyperparameter settings
        with mlflow.start_run():
            best_results = fmin(
                fn=_objective,
                space=self.hyperparameter_space,
                algo=algo,
                max_evals=self.max_evals,
                timeout=self.timeout,
                trials=trials,
                show_progressbar=self.progressbar,
                rstate=np.random.RandomState(seed=self.seed),
            )

        # select optimal settings and fit optimal pipeline
        self._fit_optimal(best_results, _X, _y)

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

        return self._fit_regressor.predict(_X)

class AutoML(AutoClassifier, AutoRegressor) :
    
    """
    Automatically assign to AutoClassifier or AutoRegressor
    """

    def __init__(
        self,
        timeout=360,
        max_evals=64,
        temp_directory="tmp",
        delete_temp_after_terminate=False,
        encoder="auto",
        imputer="auto",
        balancing="auto",
        scaling="auto",
        feature_selection="auto",
        models="auto",
        validation=True,
        test_size=0.15,
        objective=None,
        method="Bayesian",
        algo="tpe",
        spark_trials=False,
        progressbar=False,
        seed=1,
    ):
        self.timeout = timeout
        self.max_evals = max_evals
        self.temp_directory = temp_directory
        self.delete_temp_after_terminate = delete_temp_after_terminate
        self.encoder = encoder
        self.imputer = imputer
        self.balancing = balancing
        self.scaling = scaling
        self.feature_selection = feature_selection
        self.models = models
        self.validation = validation
        self.test_size = test_size
        self.objective = objective
        self.method = method
        self.algo = algo
        self.spark_trials = spark_trials
        self.progressbar = progressbar
        self.seed = seed

    def fit(self, X, y = None) :
        
        if isinstance(y, pd.DataFrame) or isinstance(y, np.ndarray) :
            self._type = type_of_task(y)
        elif y == None :
            self._type = 'Unsupervised'

        if self._type in ['binary', 'multiclass'] : # assign classification tasks
            self.model = AutoClassifier(
                timeout=self.timeout,
                max_evals=self.max_evals,
                temp_directory=self.temp_directory,
                delete_temp_after_terminate=self.delete_temp_after_terminate,
                encoder=self.encoder,
                imputer=self.imputer,
                balancing=self.balancing,
                scaling=self.scaling,
                feature_selection=self.feature_selection,
                models=self.models,
                validation=self.validation,
                test_size=self.test_size,
                objective="accuracy" if not self.objective else self.objective,
                method=self.method,
                algo=self.algo,
                spark_trials=self.spark_trials,
                progressbar=self.progressbar,
                seed=self.seed
            )
        elif self._type == 'continuous' : # assign regression tasks
            self.model = AutoRegressor(
                timeout=self.timeout,
                max_evals=self.max_evals,
                temp_directory=self.temp_directory,
                delete_temp_after_terminate=self.delete_temp_after_terminate,
                encoder=self.encoder,
                imputer=self.imputer,
                balancing=self.balancing,
                scaling=self.scaling,
                feature_selection=self.feature_selection,
                models=self.models,
                validation=self.validation,
                test_size=self.test_size,
                objective="MSE" if not self.objective else self.objective,
                method=self.method,
                algo=self.algo,
                spark_trials=self.spark_trials,
                progressbar=self.progressbar,
                seed=self.seed
            )
        else :
            raise ValueError(
                'Not recognizing type, only ["binary", "multiclass", "continuous"] accepted, get {}!'.format(
                    self._type
                )
            )

        self.model.fit(X, y)

    def predict(self, X) :

        if self.model :
            self.model.predict(X)
        else :
            raise ValueError('No tasks found! Need to fit first.')
