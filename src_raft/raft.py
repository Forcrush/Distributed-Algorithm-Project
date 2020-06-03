import config 
from queue import Queue
import random
import requests
import time
import traceback


class Raft(object):
    def __init__(self, node):
        self.node = node
        self.message_queue = Queue()

        self.id = self.node.get_socket()
        self.role = 'follower'
        self.leader_id = None

        # Persistent state on all servers:
        self.current_term = 0
        self.voted_for = None

        # Volatile state on all servers:
        self.commit_index = 0

        # timeout and leader election settings
        self.election_timeout_interval = ( config.RAFT_ELECTION_TIMEOUT_LOWER_IN_MS,
                                           config.RAFT_ELECTION_TIMEOUT_UPPER_IN_MS )

        self.next_election_time = self.get_next_election_start()
        self.leader_next_heartbeat_time = 0
        self.voter_ids = set()

        self.client_message_types = { 'broadcast_user', 'broadcast_transaction', 'broadcast_chain' }
        self.leader_message_types = { 'heartbeat', 'add_log', 'commit_log' }


    def get_status(self):
        return {
            'role': self.role,
            'leader': self.leader_id,
            'current_term': self.current_term,
            'commit_index': self.commit_index,
            'peers': self.node.get_peers()
        }


    def get_next_election_start(self):
        return time.time() + random.randint(*self.election_timeout_interval)/1000

    # messaging to raft module from outside
    def handle_message(self, message):
        self.message_queue.put(message)


    def switch_from_follower_to_candidate(self):
        self.next_election_time = self.get_next_election_start()
        self.role = 'candidate'
        self.current_term += 1
        self.voted_for = self.id
        self.voter_ids = set()

    def switch_from_candidate_to_follower(self):
        self.next_election_time = self.get_next_election_start()
        self.role = 'follower'
        self.voted_for = None
        self.voter_ids = set()


    # for raft follower to handle leader election vote request
    def handle_vote_request(self, message):
        json = {
            'type': 'vote_response',
            'src_id': self.id,
            'dst_id': message['src_id'],
            'term': self.current_term,
            'vote_granted': False,
            'last_log_index': self.commit_index
        }
        candidate_id = message['candidate_id']
        last_log_index = message['last_log_index']
        last_log_term = message['term']

        if self.voted_for is None or self.voted_for == candidate_id:
            # reject if this candidate is not in the known newest log updating status
            if self.current_term <= last_log_term and self.commit_index <= last_log_index:
                self.voted_for = message['src_id']
                self.current_term = last_log_term
                json['term'] = last_log_term
                json['vote_granted'] = True
            else:
                self.voted_for = None
        try:
            response = requests.post(url=f'http://{candidate_id}/raft/message', json=json , timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
        except Exception as e:
            print(e)


    def start_an_iteration(self, message):
        if message is None:
            return
        if message['type'] in self.client_message_types:
            return

        # updating the newest known election term from message
        if message['term'] > self.current_term:
            print('[START] message term > current term. Switch to a follower')
            self.role = 'follower'
            self.current_term = message['term']
            self.voted_for = None



    def act_as_a_follower(self, message):
        t = time.time()
        if message is not None:
            if message['type'] == 'vote_request':
                self.handle_vote_request(message)
            elif message['type'] in self.leader_message_types:
                if message['term'] == self.current_term:
                    self.leader_id = message['leader_id']
                    if self.commit_index < message['last_log_index']:
                        print('[FOLLOWER] Synchronizing with leader', self.leader_id)
                        if self.node.clone_from_peer(self.leader_id):
                            self.commit_index = message['last_log_index']
                    if message['type'] == 'commit_log':
                        print('[FOLLOWER] Committing', message)
                        self.commit_index += 1
                    self.next_election_time = self.get_next_election_start()
            elif message['type'] in self.client_message_types:
                if self.leader_id is None:
                    self.handle_message(message)
                    message = None
                else:
                    try:
                        json = message
                        response = requests.post(url=f'http://{self.leader_id}/raft/message', json=json, timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
                    except Exception as e:
                        print(e)
                        self.handle_message(message)
                        message = None

        if t > self.next_election_time:
            print('[FOLLOWER] leader heartbeat timeouted. Switch to a candidate')
            self.switch_from_follower_to_candidate()
        return


    def act_as_a_candidate(self, message):
        t = time.time()
        peers = self.node.get_peers()
        for peer in peers:
            if peer not in self.voter_ids:
               json = {
                    'type': 'vote_request',
                    'src_id': self.id,
                    'dst_id': peer,
                    'term': self.current_term,
                    'candidate_id': self.id,
                    'last_log_index': self.commit_index
               }
            try:
                response = requests.post(url=f'http://{peer}/raft/message', json=json , timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
            except Exception as e:
                print(e)

        if message is not None:
            if message['type'] == 'vote_response':
                if self.current_term < message['term'] or self.commit_index < message['last_log_index']:
                    self.switch_from_candidate_to_follower()
                elif message['vote_granted']:
                    self.voter_ids.add(message['src_id'])
                    # Receiving majority votes: reaching consensus on leader election 
                    if 1+len(self.voter_ids) > (len(peers)+1)//2:
                        print('[CANDIDATE] Win the leader election. Switch to a leader')
                        self.role = 'leader'
                        self.voted_for = None
                        self.next_heartbeat_time = 0
                        return
            elif message['type'] in self.leader_message_types:
                print('[CANDIDATE] Detect a leader. Switch to a follower')
                self.leader_id = message['src_id']
                self.current_term = message['term']
                self.switch_from_candidate_to_follower()
            elif message['type'] in self.client_message_types:
                self.handle_message(message)
                message = None

        if t > self.next_election_time:
            print('[CANDIDATE] leader election timeouted. Switch to a follower')
            self.switch_from_candidate_to_follower()
        return


    def act_as_a_leader(self, message):
        t = time.time()
        # Upon election heartbeat to each server; repeat during idle periods to prevent election timeouts
        if t > self.next_heartbeat_time or (message is not None and message['type'] == 'vote_request'):
            self.next_heartbeat_time = t + config.RAFT_LEADER_HEARTBEAT_INTERVAL_IN_MS/1000
            for peer in self.node.get_peers():
                json = {
                    'type': 'heartbeat',
                    'src_id': self.id,
                    'dst_id': peer,
                    'term': self.current_term,
                    'leader_id': self.id,
                    'last_log_index': self.commit_index
                }
                try:
                    response = requests.post(url=f'http://{peer}/raft/message', json=json , timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
                except Exception as e:
                    print(e)

        if message is not None:
            if message['type'] == 'commit_log':
                print('[LEADER] Committing', message)
                self.commit_index += 1
            elif message['type'] in self.client_message_types:
                json = message.copy()
                json['type'] = 'add_log'
                json['src_id'] = self.id
                json['term'] = self.current_term
                json['leader_id'] = self.id
                json['last_log_index'] = self.commit_index
               
                agree_count = 0
                peers = self.node.get_peers()
                peers.append(self.id)
                endpoint = None
                if message['type'] == 'broadcast_user':
                    endpoint = '/user/add'
                elif message['type'] == 'broadcast_transaction':
                    endpoint = '/transaction/add' 
                elif message['type'] == 'broadcast_chain':
                    endpoint = '/blockchain/add'

                # broadcast user requests on changes
                for peer in peers:
                    json['dst_id'] = peer
                    try:
                        response = requests.post(url=f'http://{peer}'+endpoint, json=json , timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
                        if response.status_code == 201:
                            agree_count += 1
                    except Exception as e:
                        print(e)

                # reaching consensus on changes frmm majority agreement among peers, then committing the changes
                if agree_count > len(peers)//2:
                    json['type'] = 'commit_log'
                    for peer in peers:
                        json['dst_id'] = peer
                        try:
                            response = requests.post(url=f'http://{peer}'+endpoint, json=json , timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
                        except Exception as e:
                            print(e)
        return


    def run(self):
        while True:
            try:
                # reads an incomming message from buffer
                try:
                    message =  None if self.message_queue.empty() else self.message_queue.get()
                except Exception as e:
                    print(e)

                # updating status and playing raft roles
                self.start_an_iteration(message)
                if self.role == 'follower':
                    self.act_as_a_follower(message)
                if self.role == 'candidate':
                    self.act_as_a_candidate(message)
                if self.role == 'leader':
                    self.act_as_a_leader(message)
                time.sleep(.300)
            except Exception as e:
                print(e)
                traceback.print_tb(e.__traceback__)
