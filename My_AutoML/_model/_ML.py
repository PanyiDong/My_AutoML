"""
File: _ML.py
Author: Panyi Dong
GitHub: https://github.com/PanyiDong/
Mathematics Department, University of Illinois at Urbana-Champaign (UIUC)

Project: My_AutoML
Latest Version: 0.2.0
Relative Path: /My_AutoML/_model/_ML.py
File Created: Wednesday, 13th April 2022 12:08:45 am
Author: Panyi Dong (panyid2@illinois.edu)

-----
Last Modified: Wednesday, 13th April 2022 9:52:27 am
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

import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor

from My_AutoML._constant import (
    LIGHTGBM_BINARY_CLASSIFICATION,
    LIGHTGBM_MULTICLASS_CLASSIFICATION,
    LIGHTGBM_REGRESSION,
    LIGHTGBM_BOOSTING,
    LIGHTGBM_TREE_LEARNER,
)

# https://lightgbm.readthedocs.io/en/latest/Parameters-Tuning.html

class LightGBM_Base :
    
    """
    LightGBM Classification/Regression Wrapper
    """
    
    def __init__(
        self,
        task_type = "classification",
        objective = "regression",
        boosting = "gbdt",
        n_estimators = 100,
        max_depth = -1,
        num_leaves = 31,
        min_data_in_leaf = 20,
        learning_rate = 0.1,
        tree_learner = "serial",
        num_iterations = 100,
        seed = 1,
    ) :
        self.task_type = task_type
        self.objective = objective
        self.boosting = boosting
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.num_leaves = num_leaves
        self.min_data_in_leaf = min_data_in_leaf
        self.learning_rate = learning_rate
        self.tree_learner = tree_learner
        self.num_iterations = num_iterations
        self.seed = seed
    
    def fit(self, X, y) :
        
        # get binary classification and multiclass classification
        if self.task_type == "classification" :
            if len(pd.unique(y)) == 2 :
                self.task_type = "binary"
            else :
                self.task_type = "multiclass"
                
        # check categorical hyperparameters in range
        # objective
        if self.task_type == "binary" and self.objective not in LIGHTGBM_BINARY_CLASSIFICATION :
            raise AttributeError(
                "For {} tasks, only accept objects: {}, get {}.".format(
                    self.task_type, ", ".join(LIGHTGBM_BINARY_CLASSIFICATION), self.objective
                )
            )
        elif self.task_type == "multiclass" and self.objective not in LIGHTGBM_MULTICLASS_CLASSIFICATION :
            raise AttributeError(
                "For {} tasks, only accept objects: {}, get {}.".format(
                    self.task_type, ", ".join(LIGHTGBM_MULTICLASS_CLASSIFICATION), self.objective
                )
            )
        elif self.task_type == "regression" and self.objective not in LIGHTGBM_REGRESSION :
            raise AttributeError(
                "For {} tasks, only accept objects: {}, get {}.".format(
                    self.task_type, ", ".join(LIGHTGBM_REGRESSION), self.objective
                )
            )
            
        # boosting
        if self.boosting not in LIGHTGBM_BOOSTING :
            raise AttributeError(
                "Expect one of {} boosting method, get {}.".format(
                    ", ".join(LIGHTGBM_BOOSTING), self.boosting
                )
            )
            
        # tree learner
        if self.tree_learner not in LIGHTGBM_TREE_LEARNER :
            raise AttributeError(
                "Expect one of {} tree learner, get {}.".format(
                    ", ".join(LIGHTGBM_TREE_LEARNER), self.tree_learner
                )
            )
        
        # model
        if self.task_type in ["binary", "multiclass"] :
            self.model = LGBMClassifier(
                objective=self.objective,
                boosting_type=self.boosting,
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                num_leaves=self.num_leaves,
                min_data_in_leaf=self.min_data_in_leaf,
                learning_rate=self.learning_rate,
                tree_learner = self.tree_learner,
                num_iterations = self.num_iterations,
            )
        elif self.task_type == "regression" :
            self.model = LGBMRegressor(
                objective=self.objective,
                boosting_type=self.boosting,
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                num_leaves=self.num_leaves,
                min_data_in_leaf=self.min_data_in_leaf,
                learning_rate=self.learning_rate,
                tree_learner = self.tree_learner,
                num_iterations = self.num_iterations,
            )
            
        self.model.fit(X, y)
        
        return self
    
    def predict(self, X) :
        
        return self.model.predict(X)
    
class LightGBM_Classifier(LightGBM_Base) :
    
    """
    LightGBM Classification Wrapper
    """
    
    def __init__(
        self,
        objective = "multiclass",
        boosting = "gbdt",
        n_estimators = 100,
        max_depth = -1,
        num_leaves = 31,
        min_data_in_leaf = 20,
        learning_rate = 0.1,
        tree_learner = "serial",
        num_iterations = 100,
        seed = 1,
    ) :
        self.objective = objective
        self.boosting = boosting
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.num_leaves = num_leaves
        self.min_data_in_leaf = min_data_in_leaf
        self.learning_rate = learning_rate
        self.tree_learner = tree_learner
        self.num_iterations = num_iterations
        self.seed = seed
        
        super().__init__(
            task_type = "classification",
            objective = self.objective,
            boosting = self.boosting,
            n_estimators = self.n_estimators,
            max_depth = self.max_depth,
            num_leaves = self.num_leaves,
            min_data_in_leaf = self.min_data_in_leaf,
            learning_rate = self.learning_rate,
            tree_learner = self.tree_learner,
            num_iterations = self.num_iterations,
            seed = self.seed,
        )
        
    def fit(self, X, y) :
        
        return super().fit(X, y)
    
    def predict(self, X):
        
        return super().predict(X)
    
class LightGBM_Regressor(LightGBM_Base) :
    
    """
    LightGBM Regression Wrapper
    """
    
    def __init__(
        self,
        objective = "multiclass",
        boosting = "gbdt",
        n_estimators = 100,
        max_depth = -1,
        num_leaves = 31,
        min_data_in_leaf = 20,
        learning_rate = 0.1,
        tree_learner = "serial",
        num_iterations = 100,
        seed = 1,
    ) :
        self.objective = objective
        self.boosting = boosting
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.num_leaves = num_leaves
        self.min_data_in_leaf = min_data_in_leaf
        self.learning_rate = learning_rate
        self.tree_learner = tree_learner
        self.num_iterations = num_iterations
        self.seed = seed
        
        super().__init__(
            task_type = "regression",
            objective = self.objective,
            boosting = self.boosting,
            n_estimators = self.n_estimators,
            max_depth = self.max_depth,
            num_leaves = self.num_leaves,
            min_data_in_leaf = self.min_data_in_leaf,
            learning_rate = self.learning_rate,
            tree_learner = self.tree_learner,
            num_iterations = self.num_iterations,
            seed = self.seed,
        )
        
    def fit(self, X, y) :
        
        return super().fit(X, y)
    
    def predict(self, X):
        
        return super().predict(X)