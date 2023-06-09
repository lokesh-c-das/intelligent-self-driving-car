import os
import gym
from gym import spaces
import pygame
import numpy as np 
import sys
import math
from gym_sumo.envs import env_config as c
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'],'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")
import traci
import sumolib
## add each lane density and mean_speed ##
state_space_high_for_norm = np.array([c.RL_MAX_SPEED_LIMIT,c.RL_ACC_RANGE,c.HEADING_ANGLE,c.RL_SENSING_RADIUS,c.RL_MAX_SPEED_LIMIT,c.RL_ACC_RANGE,c.RL_SENSING_RADIUS,c.RL_MAX_SPEED_LIMIT,c.RL_ACC_RANGE,c.RL_SENSING_RADIUS,c.RL_MAX_SPEED_LIMIT,c.RL_ACC_RANGE
		,c.RL_MAX_SPEED_LIMIT,c.MAX_LANE_DENSITY,c.RL_MAX_SPEED_LIMIT,c.MAX_LANE_DENSITY,c.RL_MAX_SPEED_LIMIT,c.MAX_LANE_DENSITY,c.RL_MAX_SPEED_LIMIT,c.MAX_LANE_DENSITY,c.RL_MAX_SPEED_LIMIT,c.MAX_LANE_DENSITY])
def creat_observation():
	state_space_list = ['ego_speed','ego_acc','ego_dis_to_leader','leader_speed','leader_acc','dis_to_left_leader','left_leader_speed','left_leader_acc',
	'dis_to_right_leader','right_leader_speed','right_leader_acc']
	for i in range(c.NUM_OF_LANES):
		state_space_list.append("lane_"+str(i)+"_mean_speed")
		state_space_list.append("lane_"+str(i)+"_density")
	#print(state_space_list)

	state_space_low = np.array([c.RL_MIN_SPEED_LIMIT,-c.RL_DCE_RANGE,-c.HEADING_ANGLE,-c.RL_SENSING_RADIUS,c.RL_MIN_SPEED_LIMIT,-c.RL_DCE_RANGE,-c.RL_SENSING_RADIUS,c.RL_MIN_SPEED_LIMIT,-c.RL_DCE_RANGE,-c.RL_SENSING_RADIUS,c.RL_MIN_SPEED_LIMIT,-c.RL_DCE_RANGE
		,c.RL_MIN_SPEED_LIMIT,c.MIN_LANE_DENSITY,c.RL_MIN_SPEED_LIMIT,c.MIN_LANE_DENSITY,c.RL_MIN_SPEED_LIMIT,c.MIN_LANE_DENSITY,c.RL_MIN_SPEED_LIMIT,c.MIN_LANE_DENSITY,c.RL_MIN_SPEED_LIMIT,c.MIN_LANE_DENSITY])
	state_space_high = np.array([c.RL_MAX_SPEED_LIMIT,c.RL_ACC_RANGE,c.HEADING_ANGLE,c.RL_SENSING_RADIUS,c.RL_MAX_SPEED_LIMIT,c.RL_ACC_RANGE,c.RL_SENSING_RADIUS,c.RL_MAX_SPEED_LIMIT,c.RL_ACC_RANGE,c.RL_SENSING_RADIUS,c.RL_MAX_SPEED_LIMIT,c.RL_ACC_RANGE
		,c.RL_MAX_SPEED_LIMIT,c.MAX_LANE_DENSITY,c.RL_MAX_SPEED_LIMIT,c.MAX_LANE_DENSITY,c.RL_MAX_SPEED_LIMIT,c.MAX_LANE_DENSITY,c.RL_MAX_SPEED_LIMIT,c.MAX_LANE_DENSITY,c.RL_MAX_SPEED_LIMIT,c.MAX_LANE_DENSITY])

	obs = spaces.Box(low=state_space_low,high=state_space_high,dtype=np.float64)
	return obs

class SumoEnv(gym.Env):
	"""docstring for SumoEnv"""
	metadata = {"render_modes": ["", "human", "rgb_array"], "render_fps": 4}
	def __init__(self,seed="123456",render_mode=None):
		super(SumoEnv, self).__init__()
		self.action_space = spaces.Discrete(5)
		self.observation_space = creat_observation()
		self.seed = seed

		## class variable
		self.ego = c.EGO_ID
		self.num_of_lanes = c.NUM_OF_LANES
		self.max_speed_limit = c.RL_MAX_SPEED_LIMIT
		self.is_collided = False
		assert render_mode is None or render_mode in self.metadata['render_modes']
		self.render_mode =render_mode
		self.min_speed_limit = c.RL_MIN_SPEED_LIMIT 
		self.w1 = c.W1 # efficiency coefficient
		self.w2 = c.W2 # collision coefficient
		self.w3 = c.W3 # lane change coefficient

	def _getInfo(self):
		return {"current_episode":0}

	def _startSumo(self, isGui=False):
		sumoBinary = "sumo"
		if self.render_mode=="human":
			sumoBinary = "sumo-gui" if isGui else "sumo"
		sumoCmd = [sumoBinary, "-c", "SUMO-RL-ENVIRONMENT/gym_sumo/gym_sumo/envs/xml_files/test.sumocfg","--lateral-resolution","3.2",
		 "--start", "true", "--quit-on-end", "true","--no-warnings","True", "--no-step-log", "True", "--step-length",str(c.STEP_LENGTH),
		 "--random","false"]
		traci.start(sumoCmd)

	def mean_normalization(self, obs):
		#print(obs)
		return obs
		#print(f'After Normalization: {obs/state_space_high_for_norm}')
		# mu=np.mean(obs)
		# std = np.std(obs)
		# X = (obs-mu)/(max(obs)-min(obs))
		return X
	def reset(self, isGui=False,seed=None, options=None):
		super().reset(seed=seed)
		self.is_collided = False
		self._startSumo(isGui=isGui)
		self._warmup()
		obs = np.array(self.observation_space.sample()/state_space_high_for_norm)
		info = self._getInfo()
		return self.mean_normalization(obs), info

	def _getCloseLeader(self, leaders):
		if len(leaders) <= 0:
			return "", -1
		min_dis = float('inf')
		current_leader = None,
		for leader in leaders:
			leader_id, dis = leader
			if dis < min_dis:
				current_leader = leader_id
				min_dis = dis
		return (current_leader, min_dis)

	def _getLaneDensity(self):
		road_id = traci.vehicle.getRoadID(self.ego)
		density = []
		mean_speed = []
		for i in range(self.num_of_lanes):
			density.append(len(traci.lane.getLastStepVehicleIDs(road_id+"_"+str(i))))
			mean_speed.append(traci.lane.getLastStepMeanSpeed(road_id+"_"+str(i)))
		return density, mean_speed

	def _get_rand_obs(self):
		return np.array(self.observation_space.sample())
	def _get_observation(self):
		if self._isEgoRunning()==False:
			return self._get_rand_obs()

		ego_speed = traci.vehicle.getSpeed(self.ego)/c.RL_MAX_SPEED_LIMIT
		ego_accleration = traci.vehicle.getAccel(self.ego)/c.RL_ACC_RANGE
		ego_leader = traci.vehicle.getLeader(self.ego)
		ego_heading_angle= (traci.vehicle.getAngle(self.ego)-90.0)/c.HEADING_ANGLE
		if ego_leader is not None:
			leader_id, distance = ego_leader
		else:
			leader_id, distance = "", -1
		l_speed = traci.vehicle.getSpeed(leader_id)/c.NON_RL_VEH_MAX_SPEED if leader_id != "" else 0.01/c.NON_RL_VEH_MAX_SPEED
		l_acc = traci.vehicle.getAccel(leader_id)/c.RL_ACC_RANGE if leader_id != "" else -2.6/c.RL_ACC_RANGE
		left_leader, left_l_dis = self._getCloseLeader(traci.vehicle.getLeftLeaders(self.ego, blockingOnly=False))
		left_l_speed = traci.vehicle.getSpeed(left_leader)/c.NON_RL_VEH_MAX_SPEED if left_leader != "" else 0.01/c.NON_RL_VEH_MAX_SPEED
		left_l_acc = traci.vehicle.getAccel(left_leader)/c.RL_ACC_RANGE if left_leader != "" else -2.6/c.RL_ACC_RANGE

		right_leader, right_l_dis = self._getCloseLeader(traci.vehicle.getRightLeaders(self.ego, blockingOnly=False))
		right_l_speed = traci.vehicle.getSpeed(right_leader)/c.NON_RL_VEH_MAX_SPEED if right_leader != "" else 0.01/c.NON_RL_VEH_MAX_SPEED
		right_l_acc = traci.vehicle.getAccel(right_leader)/c.RL_ACC_RANGE if right_leader != "" else -2.6/c.RL_ACC_RANGE

		states = [ego_speed, ego_accleration, ego_heading_angle, distance/c.RL_SENSING_RADIUS, l_speed, l_acc, left_l_dis/c.RL_SENSING_RADIUS, left_l_speed, left_l_acc,
			right_l_dis/c.RL_SENSING_RADIUS, right_l_speed, right_l_acc]
		density, mean_speed = self._getLaneDensity()
		for i in range(self.num_of_lanes):
			states.append(density[i]/c.MAX_LANE_DENSITY)
			states.append(mean_speed[i]/c.LANE_MEAN_SPEED)

		observations = np.array(states)
		return observations

	def _applyAction(self, action):
		if self._isEgoRunning() == False:
			return
		current_lane_index = traci.vehicle.getLaneIndex(self.ego)
		accel = traci.vehicle.getAcceleration(self.ego)
		#print(f'Acceleration: {accel}')
		if action == 0:
			# do nothing: stay in the current lane
			pass
		elif action == 1:
			target_lane_index = min(current_lane_index+1, self.num_of_lanes-1)
			traci.vehicle.changeLane(self.ego, target_lane_index, c.STEP_LENGTH)
		elif action == 2:
			target_lane_index = max(current_lane_index-1, 0)
			traci.vehicle.changeLane(self.ego, target_lane_index, c.STEP_LENGTH)
		elif action == 3:
			traci.vehicle.setAcceleration(self.ego,0.1, c.STEP_LENGTH)
		elif action == 4:
			traci.vehicle.setAcceleration(self.ego, -4.5, c.STEP_LENGTH)


	def _collision_reward(self):
		collide_vehicles = traci.simulation.getCollidingVehiclesIDList()
		if self.ego in collide_vehicles:
			self.is_collided = True
			return -10
		return 0.0
	def _efficiency(self):
		speed = traci.vehicle.getSpeed(self.ego)
		if speed <= self.min_speed_limit:
			return (speed-self.min_speed_limit)/(self.max_speed_limit-self.min_speed_limit)
		if speed > self.max_speed_limit:
			return (self.max_speed_limit-speed)/(self.max_speed_limit-self.min_speed_limit)
		return speed/self.max_speed_limit
	def _lane_change_reward(self,action):
		if action == 1 or action == 2:
			return -1.0
		return 0

	def time_loss_reward(self):
		if self._isEgoRunning():
			return traci.vehicle.getTimeLoss(self.ego)
		return 0.0

	def _reward(self, action):
		c_reward = self._collision_reward()
		if self.is_collided or self._isEgoRunning()==False:
			return c_reward*self.w2
		return c_reward*self.w2 + self._efficiency()*self.w1 + self._lane_change_reward(action)*self.w3



	def step(self, action):
		self._applyAction(action)
		traci.simulationStep()
		reward = self._reward(action)
		observation = self._get_observation()
		time_loss = self.time_loss_reward()
		done = self.is_collided or (self._isEgoRunning()==False)
		if traci.simulation.getTime() > 720:
			done = True
		return (self.mean_normalization(observation), reward, done, {})


	def _isEgoRunning(self):
		v_ids_e0 = traci.edge.getLastStepVehicleIDs("E0")
		v_ids_e1 = traci.edge.getLastStepVehicleIDs("E1")
		v_ids_e2 = traci.edge.getLastStepVehicleIDs("E2")
		if "av_0" in v_ids_e0 or "av_0" in v_ids_e1 or "av_0" in v_ids_e2:
			return True
		return False

	def _warmup(self):
		while True:
			v_ids_e0 = traci.edge.getLastStepVehicleIDs("E0")
			v_ids_e1 = traci.edge.getLastStepVehicleIDs("E1")
			v_ids_e2 = traci.edge.getLastStepVehicleIDs("E2")
			if "av_0" in v_ids_e0 or "av_0" in v_ids_e1 or "av_0" in v_ids_e2:
				traci.vehicle.setLaneChangeMode(self.ego,0)
				#traci.vehicle.setSpeedMode(self.ego,0)
				return True
			traci.simulationStep()


	def closeEnvConnection(self):
		traci.close()

	def move_gui(self):
		if self.render_mode == "human":
			x, y = traci.vehicle.getPosition('av_0')
			traci.gui.setOffset("View #0",x-50.0,108.49)
		
