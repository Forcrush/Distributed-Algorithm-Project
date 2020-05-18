# -*- coding: utf-8 -*-


from raft.node import Node
from multiprocessing import Process

node_num = 3

def node_run(conf):
	node = Node(conf)
	node.run()

if __name__ == '__main__':

	node_pool = {}
	for i in range(1, node_num+1):
		node_pool['node_{}'.format(i)] = ('localhost', 10000 + i)

	conf_pool = []
	for i in range(1, node_num+1):
		peers = node_pool.copy()
		peers.pop('node_{}'.format(i))
		conf = {'id': 'node_{}'.format(i),
				'addr': node_pool['node_{}'.format(i)],
				'peers': peers
				}
		conf_pool.append(conf)

	pro_pool = []
	for conf in conf_pool:
		pi = Process(target=node_run(conf), name='node_run', daemon=True)
		pro_pool.append(pi)
		
	for p in pro_pool:
		p.start()
	for p in pro_pool:
		p.join()
