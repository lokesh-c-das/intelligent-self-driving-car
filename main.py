import gym
import gym_sumo

from src.agent.dqn_agent import DQNAgent
from src.agent.dqn_per_agent import DQNPERAgent
def mul_proc_training(process):
	agent = DQNPERAgent(process)
	#agent = DQNAgent(process)
	env = gym.make("sumo-v0", seed="12454"+str(process), render_mode="")
	agent.train_RL(env) # for training

import multiprocessing as mp
from multiprocessing import Pool, Process
def main():
	ra = [i for i in range(1)]
	proces = []
	for i in ra:
	    proc = Process(target=mul_proc_training, args=(str(i+1),))
	    proces.append(proc)
	    proc.start()

	# complete
	for proc in proces:
	    proc.join()

if __name__ == '__main__':
	main()