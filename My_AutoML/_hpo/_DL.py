"""
File: _DL.py
Author: Panyi Dong
GitHub: https://github.com/PanyiDong/
Mathematics Department, University of Illinois at Urbana-Champaign (UIUC)

Project: My_AutoML
Latest Version: 0.2.0
Relative Path: /My_AutoML/_hpo/_DL.py
File Created: Tuesday, 5th April 2022 10:50:34 pm
Author: Panyi Dong (panyid2@illinois.edu)

-----
Last Modified: Friday, 8th April 2022 10:21:48 pm
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

class AutoTextClassifier:

    """
    Automated sentence classification: sentiment analysis, topic detection, etc.
    """

    def __init__(
        self,
        seed=1,
    ):
        self.seed = seed

    def fit(self, X, y):

        raise NotImplementedError("AutoTextClassifier is not implemented yet!")

        return self

    def predict(self, X):

        raise NotImplementedError("AutoTextClassifier is not implemented yet!")

        return self


class AutoNextWordPrediction:

    """
    Automated Next Word Prediction: sequence modeling, etc.
    """

    def __init__(
        self,
        seed=1,
    ):
        self.seed = seed

    def fit(self, X, y):

        raise NotImplementedError("AutoNextWordPrediction is not implemented yet!")

        return self

    def predict(self, X):

        raise NotImplementedError("AutoNextWordPrediction is not implemented yet!")

        return self
