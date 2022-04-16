"""
File: test_regression.py
Author: Panyi Dong
GitHub: https://github.com/PanyiDong/
Mathematics Department, University of Illinois at Urbana-Champaign (UIUC)

Project: My_AutoML
Latest Version: 0.2.0
Relative Path: /tests/test_hpo/test_regression.py
File Created: Sunday, 10th April 2022 12:00:04 pm
Author: Panyi Dong (panyid2@illinois.edu)

-----
Last Modified: Friday, 15th April 2022 7:25:09 pm
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

import os
import pandas as pd

import My_AutoML
from My_AutoML import load_data

# use command line interaction to run the model
# apparently, same class object called in one test case will not be able
# to run the model correctly after the first time
# detect whether optimal setting exists as method of determining whether
# the model is fitted correctly


def test_stroke():

    os.system(
        "python main.py --data_folder Appendix --train_data healthcare-dataset-stroke-data --response stroke"
    )

    assert (
        os.path.exists("tmp/healthcare-dataset-stroke-data_model/init.txt") == True
    ), "Classification for Stroke data failed to initiated."
    # assert (
    #     mol_heart._fitted == True
    # ), "Classification for Heart data failed to fit."
    assert (
        os.path.exists("tmp/healthcare-dataset-stroke-data_model/optimal_setting.txt")
        == True
    ), "Classification for Stroke data failed to find optimal setting."


def test_heart():

    os.system(
        "python main.py --data_folder example/example_data --train_data heart --response HeartDisease \
            --search_algo GridSearch"
    )

    assert (
        os.path.exists("tmp/heart_model/init.txt") == True
    ), "Classification for Heart data failed to initiated."
    # assert (
    #     mol_heart._fitted == True
    # ), "Classification for Heart data failed to fit."
    assert (
        os.path.exists("tmp/heart_model/optimal_setting.txt") == True
    ), "Classification for Heart data failed to find optimal setting."


def test_insurance():

    os.system(
        "python main.py --data_folder example/example_data --train_data insurance --response expenses"
    )

    assert (
        os.path.exists("tmp/insurance_model/init.txt") == True
    ), "Regression for Insurance data failed to initiated."
    # assert (
    #     mol_insurance._fitted == True
    # ), "Regression for Insurance data failed to fit."
    assert (
        os.path.exists("tmp/insurance_model/optimal_setting.txt") == True
    ), "Regression for Insurance data failed to find optimal setting."


def test_stroke_import_version():

    # test load_data here
    data = load_data().load("Appendix", "healthcare-dataset-stroke-data")
    data = data["healthcare-dataset-stroke-data"]

    features = list(data.columns)
    features.remove("stroke")
    response = ["stroke"]

    mol = My_AutoML.AutoTabular(
        model_name="stroke",
    )
    mol.fit(data[features], data[response])

    assert (
        os.path.exists("tmp/stroke/init.txt") == True
    ), "Classification for Stroke data (import_version) failed to initiated."
    assert (
        mol._fitted == True
    ), "Classification for Stroke data (import_version) failed to fit."
    assert (
        os.path.exists("tmp/stroke/optimal_setting.txt") == True
    ), "Classification for Stroke data (import_version) failed to find optimal setting."
