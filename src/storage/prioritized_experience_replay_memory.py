# Source: https://github.com/rlcode/per/blob/master/cartpole_per.py

import random
import numpy as np
from src.storage.sum_tree import SumTree


class PER(object):
	"""docstring for PER"""
	e = 0.01
	a = 0.9
	beta = 0.4
	beta_increment_per_sampling=0.001

	def __init__(self, capacity):
		super(PER, self).__init__()
		self.capacity = capacity
		self.tree = SumTree(capacity)

	def get_mem_size(self):
		return self.tree.n_entries
	def _get_priority(self,error):
		return (np.abs(error)+self.e)**self.a


	def add(self, error, sample):
		p = self._get_priority(error)
		self.tree.add(p, sample)

	def sample_experience(self, n):
		batch = []
		idxs = []
		segment = self.tree.total()/n
		priorities = []

		self.beta = np.min([1.,self.beta+self.beta_increment_per_sampling])

		for i in range(n):
			a = segment*i
			b = segment*(i+1)
			s = random.uniform(a, b)
			(idx, priority, data) = self.tree.get(s)
			priorities.append(priority)
			batch.append(data)
			idxs.append(idx)

		sampling_probabilities = priorities/self.tree.total()
		is_weight = np.power(self.tree.n_entries*sampling_probabilities, -self.beta)
		is_weight /= is_weight.max()

		return batch, idxs, is_weight

	def update(self, idx, error):
		priority = self._get_priority(error)
		self.tree.update(idx, priority)
	

