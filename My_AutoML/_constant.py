"""
File: _constant.py
Author: Panyi Dong
GitHub: https://github.com/PanyiDong/
Mathematics Department, University of Illinois at Urbana-Champaign (UIUC)

Project: My_AutoML
Latest Version: 0.2.0
Relative Path: /My_AutoML/_constant.py
File Created: Sunday, 10th April 2022 4:50:47 pm
Author: Panyi Dong (panyid2@illinois.edu)

-----
Last Modified: Tuesday, 12th April 2022 11:37:59 pm
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


# maximum unique classes determined as categorical variable
# 31 is capped by days in a month
UNI_CLASS = 31

# LightGBM default object (metric/loss)
# binary classification
LIGHTGBM_BINARY_CLASSIFICATION = ["binary", "cross-entropy"]
# multiclass classification
LIGHTGBM_MULTICLASS_CLASSIFICATION = ["multiclass", "multiclassova", "num_class"]
# regression
LIGHTGBM_REGRESSION = ["regression", "regression_l1", "huber", "fair", "poisson", \
    "quantile", "mape", "gamma", "tweedie"]

# LightGBM boosting methods
LIGHTGBM_BOOSTING = ["gbdt", "rf", "dart", "goss"]

# LightGBM tree learner
LIGHTGBM_TREE_LEARNER = ["serial", "feature", "data", "voting"]