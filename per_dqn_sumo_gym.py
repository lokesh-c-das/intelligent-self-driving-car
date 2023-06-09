
import gym
import gym_sumo

import math
import random
import numpy as np 
from collections import namedtuple,deque
from itertools import count

#import memory class
from prioritized_experience_replay_memory import PER

import torch
from torch.utils.tensorboard import SummaryWriter
torch.manual_seed(45)
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F


import matplotlib
import matplotlib.pyplot as plt
# set up matplotlib
is_ipython = 'inline' in matplotlib.get_backend()
if is_ipython:
    from IPython import display

plt.ion()
#import traci
# implementation link:
#https://pytorch.org/tutorials/intermediate/reinforcement_q_learning.html

# if GPU
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
#device = torch.device("cpu")
import platform
if platform.system() == "Windows":
	device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


step_done = 0
random.seed(45)
np.random.seed(45)



class DQN(nn.Module):

    def __init__(self, n_observations, n_actions):
        super(DQN, self).__init__()
        self.layer1 = nn.Linear(n_observations,16)
        self.layer2 = nn.Linear(16, 16)
        # self.layer3 = nn.Linear(32, 64)
        # self.layer4 = nn.Linear(64, 128)
        # self.layer5 = nn.Linear(128, 64)
        # self.layer6 = nn.Linear(64, 32)
        #self.layer7 = nn.Linear(32,16)
        self.layer8 = nn.Linear(16,n_actions) 

    # Called with either one element to determine next action, or a batch
    # during optimization. Returns tensor([[left0exp,right0exp]...]).
    def forward(self, x):
        x = F.relu(self.layer1(x))
        x = F.relu(self.layer2(x))
        # x = F.relu(self.layer3(x))
        # x = F.relu(self.layer4(x))
        # x = F.relu(self.layer5(x))
        # x = F.relu(self.layer6(x))
        # x = F.relu(self.layer7(x))
        return self.layer8(x)


class Agent(object):
	"""docstring for Agent"""
	def __init__(self, arg, hp=""):
		super(Agent, self).__init__()
		self.arg = arg
		self.batch_size = 64
		self.gamma = 0.99
		self.eps_start = 1.0
		self.eps_end = 0.1
		self.eps_decay = 100000
		self.tau = 10#0.5 # update after 30 episodes
		self.lr = 0.001
		self.n_actions = 5
		self.n_observations = 21
		self.writter = SummaryWriter(comment=str(hp))
		self.episodic_loss = 0
		self.episode_durations = []

		# create network
		self.policy_net = DQN(self.n_observations, self.n_actions).to(device)
		self.target_net = DQN(self.n_observations,self.n_actions).to(device)
		self.policy_net.eval()
		self.target_net.load_state_dict(self.policy_net.state_dict())
		self.target_net.eval()

		#self.optimizer = optim.SGD(self.policy_net.parameters(), lr=0.01, momentum=0.9)
		self.optimizer = optim.AdamW(self.policy_net.parameters(), lr=self.lr, amsgrad=True)
		self.memory = PER(30000)

	def load_model(self, PATH):
		self.policy_net = DQN(self.n_observations, self.n_actions).to(device)
		self.policy_net.load_state_dict(torch.load(PATH))
		self.policy_net.eval()

	def select_action(self,state, evaluation=False):
		global step_done
		sample = random.random()
		#print(f'Step: {step_done}')
		eps_threshold = self.eps_end + (self.eps_start-self.eps_end)*math.exp(-1.*step_done/self.eps_decay)
		step_done += 1

		if evaluation:
			with torch.no_grad():
				return self.policy_net(state).max(1)[1].view(1,1)


		if sample > eps_threshold:
			with torch.no_grad():
				return self.policy_net(state).max(1)[1].view(1,1)
		else:
			return torch.tensor([[np.random.choice(self.n_actions)]], device= device,dtype=torch.long)


	def learn_model(self):
		if len(self.memory) < self.batch_size:
			return

		transitions = self.memory.sample(self.batch_size)
		batch = Transition(*zip(*transitions))

		non_final_mask = torch.tensor(tuple(map(lambda s: s is not None,
                                          batch.next_state)), device=device, dtype=torch.bool)
		non_final_next_states = torch.cat([s for s in batch.next_state
                                                if s is not None])
		state_batch = torch.cat(batch.state)
		action_batch = torch.cat(batch.action)
		reward_batch = torch.cat(batch.reward)
		state_action_values = self.policy_net(state_batch).gather(1, action_batch)
		next_state_values = torch.zeros(self.batch_size, device=device)
		with torch.no_grad():
			next_state_values[non_final_mask] = self.target_net(non_final_next_states).max(1)[0]
		expected_state_action_values = (next_state_values * self.gamma) + reward_batch
		criterion = nn.SmoothL1Loss()
		loss = criterion(state_action_values, expected_state_action_values.unsqueeze(1))
		self.episodic_loss += loss
		self.optimizer.zero_grad()
		loss.backward()
		#torch.nn.utils.clip_grad_value_(self.policy_net.parameters(), 100)
		self.optimizer.step()

	def updateTargetNetwork(self):
		# soft update of the target network's weights
		# θ′ ← τ θ + (1 −τ )θ′
		target_net_state_dict = self.target_net.state_dict()
		policy_net_state_dict = self.policy_net.state_dict()

		for key in policy_net_state_dict:
			target_net_state_dict[key] = policy_net_state_dict[key]#*self.tau + target_net_state_dict[key]*(1-self.tau)
		self.target_net.load_state_dict(target_net_state_dict)

	def train_RL(self, env):
		max_reward = 0.0
		for e in range(1000):
			state, info = env.reset()
			r_r = 0
			time_loss_e = 0
			state = torch.tensor(state, dtype=torch.float32, device=device).unsqueeze(0)
			for t in count():
				#env.render()
				action = self.select_action(state)
				observation, reward, terminated, time_loss, _ = env.step(action.item())
				r_r += reward
				time_loss_e += time_loss
				if reward == -10:
					print(f'Collision: {reward}')
				reward = torch.tensor([reward], device=device)
				done = terminated
				if terminated:
					next_state = None
				else:
					next_state = torch.tensor(observation,dtype=torch.float32, device=device).unsqueeze(0)

				self.memory.push(state, action, next_state, reward)
				state = next_state

				self.learn_model()
				if(e+1)%self.tau == 0:
					self.updateTargetNetwork()
				if done:
					env.closeEnvConnection()
					print(f'Episodes:{e+1}, Reward: {r_r}')
					break
				env.move_gui()
			if r_r >= max_reward:
				torch.save(self.policy_net.state_dict(), "models/model_test.pth")
				max_reward = r_r
			self.writter.add_scalar("Loss/train", self.episodic_loss, (e+1))
			self.writter.add_scalar("Reward/Train", r_r, (e+1))
			self.writter.add_scalar("TimeLoss/Train", time_loss_e, (e+1))
			self.writter.flush()
			self.episodic_loss = 0.0
		#env.closeEnvConnection()
		self.writter.close()


	def test_RL(self, env):
		self.load_model("models/model_test.pth")
		for e in range(10):
			r_r = 0
			state, info = env.reset()
			state = torch.tensor(state, dtype=torch.float32, device=device).unsqueeze(0)
			for t in count():
				#env.render()
				action = self.select_action(state)
				observation, reward, terminated, _ = env.step(action.item())
				r_r += reward
				print(f'reward: {reward}')
				reward = torch.tensor([reward], device=device)
				done = terminated
				
				if terminated:
					next_state = None
				else:
					next_state = torch.tensor(observation,dtype=torch.float32, device=device).unsqueeze(0)

				if done:
					env.closeEnvConnection()
					print(f'Episodes:{e+1}, Reward: {r_r}')
					break
				state = next_state
				env.move_gui()
		env.closeEnvConnection()
		self.writter.close()






		
