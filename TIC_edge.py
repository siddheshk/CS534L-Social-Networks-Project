import os
import sys
import heapq
import numpy as np
import Queue
import networkx as nx
from classDefinitions import *
from scipy.misc import logsumexp
import math
from cStringIO import StringIO

np.seterr(all='raise')

def generateGraph(nodes, topics, density=0.5):
	G = nx.DiGraph()
	G.add_nodes_from(range(nodes))
	edgeProbs = np.random.rand(nodes,nodes)
	edgeOccurence = edgeProbs < density
	edgeIndices = np.transpose(edgeOccurence.nonzero())
	for id,edge in enumerate(edgeIndices):
		node1 = edge[0]
		node2 = edge[1]
		probabilities = np.random.rand(topics)
		G.add_edges_from([(node1, node2, {'probabilities': probabilities, 'estimates': np.random.rand(topics), 'average': np.zeros(topics)})])
	return G

class TIC(object):
	def __init__(self, graph, numTopics, items):
		self.graph = graph
		self.numTopics = numTopics
		self.numItems = len(items)
		self.items = items

	def generatePossibleWorld(self):
		coinFlips = np.random.rand(self.graph.number_of_nodes(), self.graph.number_of_nodes())
		return coinFlips

	def initAllItems(self, items):
		self.Fplus = {i : {} for i in range(items)}
		self.Fminus = {i : {} for i in range(items)}
		self.Splus = {}
		self.Sminus = {}
		self.nodeset = {i :{} for i in range(items)}


	def diffusion(self, seeds, item, isEnvironment):
		nx.set_node_attributes(self.graph, {n: False for n in self.graph.nodes}, 'isInfluenced')
		nx.set_node_attributes(self.graph, {n: None for n in self.graph.nodes}, 'influenceTimestep')
		possibleWorld = self.generatePossibleWorld()
		activeNodes = Queue.Queue()
		for seed in seeds:
			activeNodes.put([seed, 0])
			self.graph.node[seed]['isInfluenced'] = True
			self.graph.node[seed]['influenceTimestep'] = 0

		while not activeNodes.empty():
			currentNode, timestep = activeNodes.get()
			for node in self.graph.successors(currentNode):
				if not self.graph.node[node]['isInfluenced']:
					if isEnvironment:
						dot = np.dot(self.graph.edges[currentNode, node]['probabilities'], item.topicDistribution)
					else:
						dot = np.dot(self.graph.edges[currentNode, node]['estimates'], item.topicEstimates)	
					if dot > possibleWorld[currentNode][node]:
						activeNodes.put([node, timestep+1])
						self.graph.node[node]['isInfluenced'] = True
						self.graph.node[node]['influenceTimestep'] = timestep + 1
						if node not in self.Fplus[item.id]:
							self.Fplus[item.id][node] = {}
							self.nodeset[item.id][node] = 1
						self.Fplus[item.id][node][currentNode] = 1
						
						if (currentNode, node) not in self.Splus:
							self.Splus[(currentNode, node)] = {}
						self.Splus[(currentNode, node)][item.id] = 1
					else:
						if node not in self.Fminus[item.id]:
							self.Fminus[item.id][node] = {}
							self.nodeset[item.id][node] = 1
						self.Fminus[item.id][node][currentNode] = 1
						if (currentNode, node) not in self.Sminus:
							self.Sminus[(currentNode, node)] = {}
						self.Sminus[(currentNode, node)][item.id] = 1
				else:
					if timestep < self.graph.node[node]['influenceTimestep']:
						if node not in self.Fminus[item.id]:
							self.Fminus[item.id][node] = {}
							self.nodeset[item.id][node] = 1
						self.Fminus[item.id][node][currentNode] = 1
						if (currentNode, node) not in self.Sminus:
							self.Sminus[(currentNode, node)] = {}
						self.Sminus[(currentNode, node)][item.id] = 1

		influencedNodes = [n for n in self.graph.nodes if self.graph.node[n]['isInfluenced']]
		# print len(influencedNodes)
		return len(influencedNodes)

	def diffusionCelf(self, seeds, u, cur_best, item, isEnvironment):
		possibleWorld = self.generatePossibleWorld()
		activeNodes = Queue.Queue()
		nx.set_node_attributes(self.graph, False, 'isInfluencedSeed')
		nx.set_node_attributes(self.graph, False, 'isInfluencedu')
		nx.set_node_attributes(self.graph, False, 'isInfluencedcur')
		for seed in seeds:
			activeNodes.put([seed, 0])
			self.graph.node[seed]['isInfluencedSeed'] = True

		while not activeNodes.empty():
			currentNode, timestep = activeNodes.get()
			for node in self.graph.successors(currentNode):
				if not self.graph.node[node]['isInfluencedSeed']:
					if isEnvironment:
						dot = np.dot(self.graph.edges[currentNode, node]['probabilities'], item.topicDistribution)
					else:
						dot = np.dot(self.graph.edges[currentNode, node]['estimates'], item.topicEstimates)	
					if dot > possibleWorld[currentNode][node]:
						activeNodes.put([node, timestep+1])
						self.graph.node[node]['isInfluencedSeed'] = True
	
		if not self.graph.node[u]['isInfluencedSeed']:
			activeNodes.put([u, 0])
			self.graph.node[u]['isInfluencedu'] = True
			while not activeNodes.empty():
				currentNode, timestep = activeNodes.get()
				for node in self.graph.successors(currentNode):
					if not self.graph.node[node]['isInfluencedSeed'] and not self.graph.node[node]['isInfluencedu']:
						if isEnvironment:
							dot = np.dot(self.graph.edges[currentNode, node]['probabilities'], item.topicDistribution)
						else:
							dot = np.dot(self.graph.edges[currentNode, node]['estimates'], item.topicEstimates)	
						if dot > possibleWorld[currentNode][node]:
							activeNodes.put([node, timestep+1])
							self.graph.node[node]['isInfluencedu'] = True
		
		if not self.graph.node[cur_best]['isInfluencedSeed']:
			activeNodes.put([cur_best, 0])
			self.graph.node[u]['isInfluencedcur'] = True
			while not activeNodes.empty():
				currentNode, timestep = activeNodes.get()
				for node in self.graph.successors(currentNode):
					if not self.graph.node[node]['isInfluencedSeed'] and not self.graph.node[node]['isInfluencedcur']:
						if isEnvironment:
							dot = np.dot(self.graph.edges[currentNode, node]['probabilities'], item.topicDistribution)
						else:
							dot = np.dot(self.graph.edges[currentNode, node]['estimates'], item.topicEstimates)	
						if dot > possibleWorld[currentNode][node]:
							activeNodes.put([node, timestep+1])
							self.graph.node[node]['isInfluencedcur'] = True

		influencedNodes = []
		influencedNodesCur = []
		influencedNodesu = []
		influencedNodesuCur = []
		for n in self.graph.nodes:
			if self.graph.node[n]['isInfluencedSeed']:
				influencedNodes.append(n)
			if self.graph.node[n]['isInfluencedSeed'] or self.graph.node[n]['isInfluencedu']:
				influencedNodesu.append(n)
			if self.graph.node[n]['isInfluencedSeed'] or self.graph.node[n]['isInfluencedcur']:
				influencedNodesCur.append(n)
			if self.graph.node[n]['isInfluencedSeed'] or self.graph.node[n]['isInfluencedcur'] or self.graph.node[n]['isInfluencedu']:
				influencedNodesuCur.append(n)
		return len(influencedNodes), len(influencedNodesu), len(influencedNodesCur), len(influencedNodesuCur)

	def expectedSpread(self, seeds, item, numberOfSimulations, isEnvironment):
		expSpread = 0.0
		for simulation in range(numberOfSimulations):
			expSpread += self.diffusion(seeds, item, isEnvironment)
		expSpread = expSpread/numberOfSimulations
		return expSpread

	def expectedSpreadCelf(self, seeds, u, cur_best, item, numberOfSimulations, isEnvironment):
		expSpread = 0.0
		expSpreadu = 0.0
		expSpreadCur = 0.0
		expSpreaduCur = 0.0
		for simulation in range(numberOfSimulations):
			spreads = self.diffusionCelf(seeds, u, cur_best, item, isEnvironment)
			expSpread += spreads[0]
			expSpreadu += spreads[1]
			expSpreadCur += spreads[2]
			expSpreaduCur += spreads[3]
		expSpread /= numberOfSimulations
		expSpreadu /= numberOfSimulations
		expSpreadCur /= numberOfSimulations
		expSpreaduCur /= numberOfSimulations
		return expSpread, expSpreadu, expSpreadCur, expSpreaduCur

	def findBestSeeds(self, item, budget, isEnvironment=True, numberOfSimulations=100):
		seeds = []
		seedMap = {}
		while len(seeds) < budget:
			maximumSpread = 0
			newSeed = -1
			for candidate in range(self.graph.number_of_nodes()):
				try:
					isSeed = seedMap[candidate]
				except:
					expSpread = self.expectedSpread(seeds+[candidate], item, numberOfSimulations, isEnvironment)
					if expSpread > maximumSpread:
						maximumSpread = expSpread
						newSeed = candidate
			if newSeed != -1:
				seeds.append(newSeed)
				seedMap[newSeed] = 1
			else:
				break
		return seeds, maximumSpread

	def celf(self, item, budget, isEnvironment=True, numberOfSimulations=100):
		seeds = []
		q = []
		seedMap = {}
		cur_best = None
		cur_best_spread = -1
		last_seed = None
		for node in self.graph.nodes:
			u = {}
			if cur_best is None:
				u['mg1'] = self.expectedSpread([node], item, numberOfSimulations, isEnvironment)
				u['mg2'] = u['mg1']
			else:
				spreads = self.expectedSpreadCelf([], node, cur_best, item, numberOfSimulations, isEnvironment)
				u['mg1'] = spreads[1] - spreads[0]
				u['mg2'] = spreads[3] - spreads[0]
			u['prev_best'] = cur_best
			u['flag'] = 0
			u['node'] = node
			heapq.heappush(q, (-u['mg1'], u))
			q.append((-u['mg1'], u))
			if cur_best_spread < u['mg1']:
				cur_best_spread = u['mg1']
				cur_best = node
		while len(seeds) < budget:
			u = heapq.heappop(q)[1]
			if u['flag'] == len(seeds):
				seeds.append(u['node'])
				last_seed = u['node']
				continue
			elif u['prev_best'] == last_seed:
				u['mg1'] = u['mg2']
			else:
				spreads = self.expectedSpreadCelf(seeds, u['node'], cur_best, item, numberOfSimulations, isEnvironment)
				u['mg1'] = spreads[1] - spreads[0]
				u['mg2'] = spreads[3] - spreads[2]
				u['prev_best'] = cur_best
			u['flag'] = len(seeds)
			if cur_best_spread < u['mg1']:
				cur_best_spread = u['mg1']
				cur_best = u['node']
			heapq.heappush(q, (-u['mg1'], u))
		return seeds


class MAB(object):
	def __init__(self, tic, budget):
		self.budget = budget
		self.tic = tic

	def explore(self, item):
		seeds = np.random.choice(self.tic.graph.number_of_nodes(), self.budget, replace=False)
		return seeds.tolist()

	def exploit(self, item):
		seeds = self.tic.celf(item, self.budget, isEnvironment=False)
		return seeds

	def epsilonGreedy(self, epsilon, item):
		if epsilon > np.random.rand(1):
			seeds = self.explore(item)
		else:
			seeds = self.exploit(item)
		spread = self.tic.diffusion(seeds=seeds, item=item, isEnvironment=True)
		return seeds

	def L2Error(self):
		l2 = 0.
		for edge in self.tic.graph.edges:
			l2 += (self.tic.graph.edges[edge]['estimates'] - self.tic.graph.edges[edge]['probabilities'])**2
		return np.sum(l2)

	def learner(self, iterations, epsilon):
		pi = np.random.rand(self.tic.numTopics)
		pi = np.log(pi/sum(pi))
		nodeset = {}
		R = {}
		negative_sum = {}
		positive_sum = {}
		pi_average = np.zeros(self.tic.numTopics)
		for iteration in range(iterations):
			self.tic.initAllItems(self.tic.numItems)
			seeds = [self.epsilonGreedy(epsilon, self.tic.items[i]) for i in range(self.tic.numItems)]
			itemSum = np.zeros(self.tic.numTopics)
			for item in range(self.tic.numItems):
				cascadeLogProbPositive = np.zeros(self.tic.numTopics)
				cascadeLogProbNegative = np.zeros(self.tic.numTopics)
				for node in self.tic.nodeset[item]:
					influenced = 0
					if node in self.tic.Fplus[item]:
						influenced = 1
						for positivenode in self.tic.Fplus[item][node].keys():
							positive = np.copy(self.tic.graph.edges[positivenode, node]['estimates'])
							try:
								cascadeLogProbPositive += np.log(positive)
							except:
								positive[positive <= 0.] = 1.
								cascadeLogProbPositive += np.log(positive)								

					if node in self.tic.Fminus[item]:
						for negativeNode in self.tic.Fminus[item][node].keys():
							negative = np.copy(1. - self.tic.graph.edges[negativeNode, node]['estimates'])
							try:
								cascadeLogProbNegative += np.log(negative)
							except:
								negative[negative <= 0.] = 1.
								cascadeLogProbNegative += np.log(negative)
						
				self.tic.items[item].topicEstimates =  pi + cascadeLogProbPositive + cascadeLogProbNegative
				try:
					norm = logsumexp(self.tic.items[item].topicEstimates)
				except:
					self.tic.items[item].topicEstimates[self.tic.items[item].topicEstimates < -500] = -500
					norm = logsumexp(self.tic.items[item].topicEstimates)
				self.tic.items[item].topicEstimates = np.exp(self.tic.items[item].topicEstimates - norm)
				itemSum += np.copy(self.tic.items[item].topicEstimates)
			pi_average += np.copy(itemSum)
			# pi = np.log(pi_average/(self.tic.numItems*(iteration+1)))
			pi = np.log(itemSum/(self.tic.numItems))
			for node1, node2 in self.tic.Splus.keys():
				numerator = np.zeros(self.tic.numTopics)
				denominator = np.zeros(self.tic.numTopics)
				update = 0
				for item in self.tic.Splus[(node1, node2)].keys():
					if item in self.tic.Fplus:
						if (node1, node2) not in positive_sum:
							positive_sum[(node1, node2)] = np.zeros(self.tic.numTopics)
						if (node1, node2) not in negative_sum:
							negative_sum[(node1, node2)] = np.zeros(self.tic.numTopics)
						denominator = np.copy(negative_sum[(node1, node2)])
						numerator = np.copy(positive_sum[(node1, node2)])
						try:
							numerator += self.tic.items[item].topicEstimates
							denominator += self.tic.items[item].topicEstimates
							if numerator > denominator:
								print "Error New"
								print numerator, denominator,  R[item][(node1, node2)]
								sys.exit()
						except:						
							dist = np.copy(self.tic.items[item].topicEstimates)
							dist[dist < 10**-50] = 10**-50.
							numerator += dist
							denominator += dist
						update = 1

				if update == 1:
					
					if (node1, node2) in self.tic.Sminus:
						for item in self.tic.Sminus[(node1, node2)].keys():
							if item in self.tic.Fminus:
								denominator += self.tic.items[item].topicEstimates
								key = (node1, node2)

					try:
						self.tic.graph.edges[node1, node2]['estimates'] = numerator/denominator
					except:
						numerator[numerator < 10**-50] = 10**-50.
						try:
							self.tic.graph.edges[node1, node2]['estimates'] = numerator/denominator
						except:
							denominator[denominator < 10**-50] = 10**-50.
							self.tic.graph.edges[node1, node2]['estimates'] = numerator/denominator	
					positive_sum[(node1, node2)] = np.copy(numerator)
					negative_sum[(node1, node2)] = np.copy(denominator)
					#probMask = (self.tic.graph.edges[node1, node2]['estimates'] > 1.)
					#self.tic.graph.edges[node1, node2]['estimates'][probMask] = 1.
					if sum(self.tic.graph.edges[node1, node2]['estimates']> 1.) > 0:
						print "Error: ", numerator, denominator, self.tic.graph.edges[node1, node2]['estimates']
						sys.exit()

			print self.tic.graph.edges[key]['probabilities'], self.tic.graph.edges[key]['estimates'], self.tic.items[0].topicEstimates, self.tic.items[0].topicDistribution, np.dot(self.tic.graph.edges[key]['probabilities'], self.tic.items[0].topicDistribution), np.dot(self.tic.graph.edges[key]['estimates'], self.tic.items[0].topicEstimates)

itemList = []
numItems = 10
numTopics = 2
budget = 5
for i in range(numItems):
	itemDist = np.random.rand(numTopics)
	itemList.append(Item(i, itemDist/sum(itemDist)))
tic = TIC(generateGraph(1000, numTopics, density=0.002), numTopics, itemList)
mab = MAB(tic, budget)
print mab.learner(100000,1)