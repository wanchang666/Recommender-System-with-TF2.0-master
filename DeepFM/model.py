"""
Created on July 31, 2020

model: DeepFM: A Factorization-Machine based Neural Network for CTR Prediction

@author: Ziyao Geng
"""

import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.regularizers import l2
from tensorflow.keras.layers import Embedding, Dropout, Dense, Input, Layer


class FM(Layer):
	"""
	Wide part
	"""
	def __init__(self, k=10, w_reg=1e-4, v_reg=1e-4):
		"""
		Factorization Machine
		:param k: A scalar. The dimension of the latent vector.
		:param w_reg: A scalar. The regularization coefficient of parameter w.
		:param v_reg: A scalar. The regularization coefficient of parameter v.
		"""
		super(FM, self).__init__()
		self.k = k
		self.w_reg = w_reg
		self.v_reg = v_reg

	def build(self, input_shape):
		self.w0 = self.add_weight(name='w0', shape=(1,),
								  initializer=tf.zeros_initializer(),
								  trainable=True)
		self.w = self.add_weight(name='w', shape=(input_shape[-1], 1),
								 initializer='random_uniform',
								 regularizer=l2(self.w_reg),
								 trainable=True)
		self.V = self.add_weight(name='V', shape=(self.k, input_shape[-1]),
								 initializer='random_uniform',
								 regularizer=l2(self.v_reg),
								 trainable=True)

	def call(self, inputs, **kwargs):
		# first order
		first_order = self.w0 + tf.matmul(inputs, self.w)
		# second order
		second_order = 0.5 * tf.reduce_sum(
			tf.pow(tf.matmul(inputs, tf.transpose(self.V)), 2) -
			tf.matmul(tf.pow(inputs, 2), tf.pow(tf.transpose(self.V), 2)), axis=1, keepdims=True)
		return first_order + second_order


class DNN(Layer):
	"""
	Deep part
	"""
	def __init__(self, hidden_units, activation='relu', dnn_dropout=0.):
		"""
		DNN part
		:param hidden_units: A list. List of hidden layer units's numbers
		:param activation: A string. Activation function
		:param dnn_dropout: A scalar. dropout number
		"""
		super(DNN, self).__init__()
		self.dnn_network = [Dense(units=unit, activation=activation) for unit in hidden_units]
		self.dropout = Dropout(dnn_dropout)

	def call(self, inputs, **kwargs):
		x = inputs
		for dnn in self.dnn_network:
			x = dnn(x)
		x = self.dropout(x)
		return x


class DeepFM(Model):
	def __init__(self, feature_columns, k=10, hidden_units=(200, 200, 200), dnn_dropout=0.,
				 activation='relu', fm_w_reg=1e-4, fm_v_reg=1e-4, embed_reg=1e-4):
		"""
		DeepFM
		:param feature_columns: A list. a list containing dense and sparse column feature information.
		:param k: A scalar. fm's latent vector number.
		:param hidden_units: A list. A list of dnn hidden units.
		:param dnn_dropout: A scalar. Dropout of dnn.
		:param activation: A string. Activation function of dnn.
		:param fm_w_reg: A scalar. The regularizer of w in fm.
		:param fm_v_reg: A scalar. The regularizer of v in fm.
		:param embed_reg: A scalar. The regularizer of embedding.
		"""
		super(DeepFM, self).__init__()
		self.dense_feature_columns, self.sparse_feature_columns = feature_columns
		self.embed_layers = {
			'embed_' + str(i): Embedding(input_dim=feat['feat_num'],
										 input_length=1,
										 output_dim=feat['embed_dim'],
										 embeddings_initializer='random_uniform',
										 embeddings_regularizer=l2(embed_reg))
			for i, feat in enumerate(self.sparse_feature_columns)
		}
		self.fm = FM(k, fm_w_reg, fm_v_reg)
		self.dnn = DNN(hidden_units, activation, dnn_dropout)
		self.dense = Dense(1, activation=None)

	def call(self, inputs, **kwargs):
		dense_inputs, sparse_inputs = inputs
		sparse_embed = tf.concat([self.embed_layers['embed_{}'.format(i)](sparse_inputs[:, i])
                                  for i in range(sparse_inputs.shape[1])], axis=-1)
		stack = tf.concat([dense_inputs, sparse_embed], axis=-1)
		# wide
		wide_outputs = self.fm(stack)
		# deep
		deep_outputs = self.dnn(stack)
		deep_outputs = self.dense(deep_outputs)

		outputs = tf.nn.sigmoid(tf.add(wide_outputs, deep_outputs))
		return outputs

	def summary(self):
		dense_inputs = Input(shape=(len(self.dense_feature_columns),), dtype=tf.float32)
		sparse_inputs = Input(shape=(len(self.sparse_feature_columns),), dtype=tf.int32)
		Model(inputs=[dense_inputs, sparse_inputs], outputs=self.call([dense_inputs, sparse_inputs])).summary()
