"""
Created on August 3, 2020
model: Attentional Factorization Machines: Learning the Weight of Feature Interactions via Attention Networks
@author: Ziyao Geng
"""
import itertools
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.regularizers import l2
from tensorflow.keras.layers import Embedding, Dense, Dropout, Input


class AFM(keras.Model):
    def __init__(self, feature_columns, mode, att_vector=8, activation='relu', dropout=0.5, embed_reg=1e-4):
        """
        AFM
        :param feature_columns: A list. dense_feature_columns and sparse_feature_columns
        :param mode: A string. 'max'(MAX Pooling) or 'avg'(Average Pooling) or 'att'(Attention)
        :param att_vector: A scalar. attention vector.
        :param activation: A string. Activation function of attention.
        :param dropout: A scalar. Dropout.
        :param embed_reg: A scalar. the regularizer of embedding
        """
        super(AFM, self).__init__()
        self.dense_feature_columns, self.sparse_feature_columns = feature_columns
        self.mode = mode
        self.embed_layers = {
            'embed_' + str(i): Embedding(input_dim=feat['feat_num'],
                                         input_length=1,
                                         output_dim=feat['embed_dim'],
                                         embeddings_initializer='random_uniform',
                                         embeddings_regularizer=l2(embed_reg))
            for i, feat in enumerate(self.sparse_feature_columns)
        }
        if self.mode == 'att':
            self.attention_W = Dense(units=att_vector, activation=activation, use_bias=True)
            self.attention_dense = Dense(units=1, activation=None)
        self.dropout = Dropout(dropout)
        self.dense = Dense(units=1, activation=None)

    def call(self, inputs):
        # Input Layer
        dense_inputs, sparse_inputs = inputs
        # Embedding Layer
        embed = [self.embed_layers['embed_{}'.format(i)](sparse_inputs[:, i]) for i in range(sparse_inputs.shape[1])]
        embed = tf.transpose(tf.convert_to_tensor(embed), perm=[1, 0, 2])  # (None, len(sparse_inputs), embed_dim)
        # Pair-wise Interaction Layer
        row = []
        col = []
        for r, c in itertools.combinations(range(len(self.sparse_feature_columns)), 2):
            row.append(r)
            col.append(c)
        p = tf.gather(embed, row, axis=1)  # (None, (len(sparse) * len(sparse) - 1) / 2, k)
        q = tf.gather(embed, col, axis=1)  # (None, (len(sparse) * len(sparse) - 1) / 2, k)
        bi_interaction = p * q  # (None, (len(sparse) * len(sparse) - 1) / 2, k)
        # mode
        if self.mode == 'max':
            # MaxPooling Layer
            x = tf.reduce_sum(bi_interaction, axis=1)   # (None, k)
        elif self.mode == 'avg':
            # AvgPooling Layer
            x = tf.reduce_mean(bi_interaction, axis=1)  # (None, k)
        else:
            # Attention Layer
            x = self.attention(bi_interaction)  # (None, k)
        # Output Layer
        outputs = tf.nn.sigmoid(self.dense(x))

        return outputs

    def summary(self):
        dense_inputs = Input(shape=(len(self.dense_feature_columns),), dtype=tf.float32)
        sparse_inputs = Input(shape=(len(self.sparse_feature_columns),), dtype=tf.int32)
        keras.Model(inputs=[dense_inputs, sparse_inputs], outputs=self.call([dense_inputs, sparse_inputs])).summary()

    def attention(self, bi_interaction):
        a = self.attention_W(bi_interaction)  # (None, (len(sparse) * len(sparse) - 1) / 2, t)
        a = self.attention_dense(a)  # (None, (len(sparse) * len(sparse) - 1) / 2, 1)
        a_score = tf.nn.softmax(a, axis=1)  # (None, (len(sparse) * len(sparse) - 1) / 2, 1)
        outputs = tf.reduce_sum(bi_interaction * a_score, axis=1)  # (None, embed_dim)
        return outputs