"""
Created on August 26, 2020

train FFM model

@author: Ziyao Geng
"""

import numpy as np
import tensorflow as tf
from tensorflow.keras.losses import binary_crossentropy
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.metrics import AUC
from model import FFM

from utils import create_criteo_dataset

import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


if __name__ == '__main__':
    # ========================= Hyper Parameters =======================
    # you can modify your file path
    file = '../dataset/Criteo/train.txt'
    read_part = True
    sample_num = 100000
    test_size = 0.2

    k = 8

    learning_rate = 0.001
    batch_size = 512
    epochs = 5

    # ========================== Create dataset =======================
    feature_columns, train, test = create_criteo_dataset(file=file,
                                           read_part=read_part,
                                           sample_num=sample_num,
                                           test_size=test_size)
    train_X, train_y = train
    test_X, test_y = test
    # ============================Build Model==========================
    model = FFM(feature_columns=feature_columns, k=k)
    model.summary()
    # ============================model checkpoint======================
    # check_path = '../save/fm_weights.epoch_{epoch:04d}.val_loss_{val_loss:.4f}.ckpt'
    # checkpoint = tf.keras.callbacks.ModelCheckpoint(check_path, save_weights_only=True,
    #                                                 verbose=1, period=5)
    # ============================Compile============================
    model.compile(loss=binary_crossentropy, optimizer=Adam(learning_rate=learning_rate),
                  metrics=[AUC()])
    # ==============================Fit==============================
    model.fit(
        train_X,
        train_y,
        epochs=epochs,
        # callbacks=[checkpoint],
        batch_size=batch_size,
        validation_split=0.1
    )
    # ===========================Test==============================
    print('test AUC: %f' % model.evaluate(test_X, test_y)[1])
