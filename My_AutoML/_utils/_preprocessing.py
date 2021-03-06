"""
File: _preprocessing.py
Author: Panyi Dong
GitHub: https://github.com/PanyiDong/
Mathematics Department, University of Illinois at Urbana-Champaign (UIUC)

Project: My_AutoML
Latest Version: 0.2.0
Relative Path: /My_AutoML/_utils/_preprocessing.py
File Created: Wednesday, 6th April 2022 12:04:44 am
Author: Panyi Dong (panyid2@illinois.edu)

-----
Last Modified: Friday, 8th April 2022 10:27:33 pm
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

import importlib

pytorch_spec = importlib.util.find_spec("torch")
if pytorch_spec is not None:
    import torch
    from torch.utils.data import TensorDataset, DataLoader

torchtext_spec = importlib.util.find_spec("torchtext")
if torchtext_spec is not None:
    from torchtext.data.utils import get_tokenizer
    from torchtext.vocab import build_vocab_from_iterator

transformers_spec = importlib.util.find_spec("transformers")
if transformers_spec is not None:
    import transformers
    from transformers import AutoTokenizer

# text preprocessing
# build a vocabulary from text using torchtext methods
# fixed length sequence needed
def text_preprocessing_torchtext(
    data,
    batch_size=32,
    shuffle=True,
    drop_first=True,
    return_offset=False,
):
    tokenizer = get_tokenizer("basic_english")

    # yield tokens from a string
    def yield_tokens(data_iter):
        for item in data_iter:
            # if item is dict, get text/label
            # assume from datasets packages
            if isinstance(item, dict):
                yield tokenizer(item["text"])
            # else, assume in (text, label) format
            else:
                text, label = item
                yield tokenizer(text)

    # define vocabulary
    vocab = build_vocab_from_iterator(yield_tokens(data), specials=["<unk>"])
    vocab.set_default_index(vocab["<unk>"])

    # tokenize data and build vocab
    text_pipeline = lambda x: vocab(tokenizer(x))
    # label_pipeline = lambda x: int(x) - 1

    # return tensordataset text, label, and offset (optional)
    text_list, label_list, offsets = [], [], [0]

    for idx, item in enumerate(data):
        # if item is dict, get text/label
        # assume from datasets packages
        if isinstance(item, dict):
            _text, _label = item["text"], item["label"]
        # else, assume in (text, label) format
        else:
            _text, _label = item

        processed_text = torch.tensor(text_pipeline(_text), dtype=torch.int64)
        text_list.append(processed_text)
        label_list.append(_label)
        if return_offset:
            offsets.append(processed_text.size(0))

    text_list = torch.stack(text_list)
    label_list = torch.tensor(label_list, dtype=torch.int64)
    if return_offset:
        offsets = torch.tensor(offsets[:-1]).cumsum(dim=0)

    if return_offset:
        data_tensor = TensorDataset(text_list, label_list, offsets)
    else:
        data_tensor = TensorDataset(text_list, label_list)

    # load data to DataLoader
    data_loader = DataLoader(
        data_tensor, batch_size=batch_size, shuffle=shuffle, drop_first=drop_first
    )

    return data_loader, vocab


# text preprocessing using transformers package
def text_preprocessing_transformers(
    data,
    batch_size=32,
    tokenizer_model="bert-base-uncased",
    max_len=512,
    return_attention_mask=False,
    return_token_type_ids=False,
    return_tensors="pt",
):

    # load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_model)

    # define a mapping tokenization method
    def mapping_tokenizer(example):

        # tokenizer the text to tensor inputs
        # max_length, padding, truncation combination can pad/truncate text tokens to max_length
        # 1. add space after meaningful tokens if sentence length < max_length
        # 2. delete text tokens to max_length if sentence length > max_length
        # decide whether to return attention masks and token type ids
        return tokenizer(
            example["text"],
            max_length=max_len,
            padding="max_length",
            truncation=True,
            return_attention_mask=return_attention_mask,
            return_token_type_ids=return_token_type_ids,
            return_tensors=return_tensors,
        )

    # apply mapping tokenization method to data examples
    tokenized_data = data.map(mapping_tokenizer)

    # limit data parts to use
    selected_data = tokenized_data.set_format(type="torch", columns=["inputs", "label"])

    # load data to DataLoader
    train_tensor = TensorDataset(
        torch.as_tensor(selected_data["input_ids"]),
        torch.as_tensor(selected_data["label"]),
    )
    train_loader = DataLoader(
        train_tensor, batch_size=batch_size, shuffle=True, drop_last=True
    )

    return train_loader
