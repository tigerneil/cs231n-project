import tensorflow as tf
import numpy as np
import hyperparameters as hp
from action import Action

def weight_variable(shape, name):
  initial = tf.truncated_normal(shape, stddev=0.1)
  return tf.Variable(initial, name=name)

def bias_variable(shape, name):
  initial = tf.constant(0.1, shape=shape)
  return tf.Variable(initial, name=name)

def conv2d(x, W, s):
  return tf.nn.conv2d(x, W, strides=[1, s, s, 1], padding="VALID")

def output_size(in_size, filter_size, stride):
	return (in_size - filter_size)/stride + 1

conv1_out_size = output_size(hp.INPUT_SIZE, hp.CONV_1_SIZE, hp.CONV_1_STRIDE)
conv2_out_size = output_size(conv1_out_size, hp.CONV_2_SIZE, hp.CONV_2_STRIDE)
conv3_out_size = output_size(conv2_out_size, hp.CONV_3_SIZE, hp.CONV_3_STRIDE)
conv3_out_len = hp.CONV_3_DEPTH * (conv3_out_size ** 2)

with tf.name_scope("input"):
	s = tf.placeholder(tf.float32, shape=[
		hp.MINIBATCH_SIZE, # TODO None
		hp.INPUT_SIZE,
		hp.INPUT_SIZE,
		hp.AGENT_HISTORY_LENGTH
	], name="s")

	sp = tf.placeholder(tf.float32, shape=[
		hp.MINIBATCH_SIZE, # TODO None
		hp.INPUT_SIZE,
		hp.INPUT_SIZE,
		hp.AGENT_HISTORY_LENGTH
	], name="sp")

with tf.name_scope("regular_net"):
	r_W_conv1 = weight_variable([
		hp.CONV_1_SIZE,
		hp.CONV_1_SIZE,
		hp.AGENT_HISTORY_LENGTH,
		hp.CONV_1_DEPTH
	], name="r_W_conv1")
	r_b_conv1 = bias_variable([hp.CONV_1_DEPTH], name="r_b_conv1")

	r_W_conv2 = weight_variable([
		hp.CONV_2_SIZE,
		hp.CONV_2_SIZE,
		hp.CONV_1_DEPTH,
		hp.CONV_2_DEPTH
	], name="r_W_conv2")
	r_b_conv2 = bias_variable([hp.CONV_2_DEPTH], name="r_b_conv2")

	r_W_conv3 = weight_variable([
		hp.CONV_3_SIZE,
		hp.CONV_3_SIZE,
		hp.CONV_2_DEPTH,
		hp.CONV_3_DEPTH
	], name="r_W_conv3")
	r_b_conv3 = bias_variable([hp.CONV_3_DEPTH], name="r_b_conv3")

	r_W_fc1 = weight_variable([conv3_out_len, hp.FC_SIZE], name="r_W_fc1")
	r_b_fc1 = bias_variable([hp.FC_SIZE], name="r_b_fc1")

	r_W_out = weight_variable([hp.FC_SIZE, Action.num_actions], name="r_W_out")
	r_b_out = bias_variable([Action.num_actions], name="b_out")

	r_h_conv1 = tf.nn.relu(conv2d(s, r_W_conv1, hp.CONV_1_STRIDE) + r_b_conv1)
	r_h_conv2 = tf.nn.relu(conv2d(r_h_conv1, r_W_conv2, hp.CONV_2_STRIDE) + r_b_conv2)
	r_h_conv3 = tf.nn.relu(conv2d(r_h_conv2, r_W_conv3, hp.CONV_3_STRIDE) + r_b_conv3)
	r_resized = tf.reshape(r_h_conv3, [-1, conv3_out_len], name="r_resized")
	r_h_fc1 = tf.nn.relu(tf.matmul(r_resized, r_W_fc1) + r_b_fc1)
	r_actions = tf.matmul(r_h_fc1, r_W_out) + r_b_out


with tf.name_scope("target_params"):
	t_W_conv1 = tf.Variable(r_W_conv1.initialized_value(), trainable=False)
	t_W_conv2 = tf.Variable(r_W_conv2.initialized_value(), trainable=False)
	t_W_conv3 = tf.Variable(r_W_conv3.initialized_value(), trainable=False)
	t_W_fc1 = tf.Variable(r_W_fc1.initialized_value(), trainable=False)
	t_W_out = tf.Variable(r_W_out.initialized_value(), trainable=False)
	t_b_conv1 = tf.Variable(r_b_conv1.initialized_value(), trainable=False)
	t_b_conv2 = tf.Variable(r_b_conv2.initialized_value(), trainable=False)
	t_b_conv3 = tf.Variable(r_b_conv3.initialized_value(), trainable=False)
	t_b_fc1 = tf.Variable(r_b_fc1.initialized_value(), trainable=False)
	t_b_out = tf.Variable(r_b_out.initialized_value(), trainable=False)

	t_h_conv1 = tf.nn.relu(conv2d(sp, t_W_conv1, hp.CONV_1_STRIDE) + t_b_conv1)
	t_h_conv2 = tf.nn.relu(conv2d(t_h_conv1, t_W_conv2, hp.CONV_2_STRIDE) + t_b_conv2)
	t_h_conv3 = tf.nn.relu(conv2d(t_h_conv2, t_W_conv3, hp.CONV_3_STRIDE) + t_b_conv3)
	t_resized = tf.reshape(t_h_conv3, [-1, conv3_out_len], name="t_resized")
	t_h_fc1 = tf.nn.relu(tf.matmul(t_resized, t_W_fc1) + t_b_fc1)
	t_actions = tf.matmul(t_h_fc1, t_W_out) + t_b_out

with tf.name_scope("updaters"):
	regular = [
		r_W_conv1,
		r_W_conv2,
		r_W_conv3,
		r_W_fc1,
		r_W_out,
		r_b_conv1,
		r_b_conv2,
		r_b_conv3,
		r_b_fc1,
		r_b_out,
	]

	target = [
		t_W_conv1,
		t_W_conv2,
		t_W_conv3,
		t_W_fc1,
		t_W_out,
		t_b_conv1,
		t_b_conv2,
		t_b_conv3,
		t_b_fc1,
		t_b_out,
	]


	target_update = []

	for i in range(len(regular)):
		t, r = target[i], regular[i]
		target_update.append(tf.assign(t, r))

	update_target = tf.group(*target_update)

with tf.name_scope("loss"):
	actions = tf.placeholder(tf.int32, hp.MINIBATCH_SIZE)
	rewards = tf.placeholder(tf.float32, hp.MINIBATCH_SIZE)
	terminals = tf.placeholder(tf.int32, hp.MINIBATCH_SIZE)
	gamma = tf.constant(hp.DISCOUNT_FACTOR, dtype=tf.float32)

	ys = rewards + tf.to_float(1 - terminals) * gamma * tf.reduce_max(t_actions, reduction_indices=1)
	r_actions_flat = tf.reshape(r_actions, [-1])
	gathered = tf.gather(r_actions_flat, hp.MINIBATCH_SIZE * actions)
	loss = tf.reduce_mean(tf.square(ys - gathered))
	optimizer = tf.train.RMSPropOptimizer(hp.LEARNING_RATE, hp.GRADIENT_MOMENTUM, momentum=hp.SQUARED_GRADIENT_MOMENTUM, epsilon=hp.MIN_SQUARED_GRADIENT)
	minimize_loss = optimizer.minimize(loss, var_list=regular)

