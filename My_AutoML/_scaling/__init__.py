"""
File: __init__.py
Author: Panyi Dong
GitHub: https://github.com/PanyiDong/
Mathematics Department, University of Illinois at Urbana-Champaign (UIUC)

Project: My_AutoML
Latest Version: 0.2.0
Relative Path: /My_AutoML/_scaling/__init__.py
File Created: Wednesday, 6th April 2022 10:40:25 am
Author: Panyi Dong (panyid2@illinois.edu)

-----
Last Modified: Friday, 29th April 2022 1:40:01 pm
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

from ._scaling import (
    MinMaxScale,
    Standardize,
    Normalize,
    RobustScale,
    PowerTransformer,
    QuantileTransformer,
    Winsorization,
    Feature_Manipulation,
    Feature_Truncation,
)
from My_AutoML._base import no_processing

scalings = {
    "no_processing": no_processing,
    "MinMaxScale": MinMaxScale,
    "Standardize": Standardize,
    "Normalize": Normalize,
    "RobustScale": RobustScale,
    "PowerTransformer": PowerTransformer,
    "QuantileTransformer": QuantileTransformer,
    "Winsorization": Winsorization,
    # "Feature_Manipulation": Feature_Manipulation,
    # "Feature_Truncation": Feature_Truncation,
}
