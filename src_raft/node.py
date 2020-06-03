from blockchain import Blockchain
import config
import json
import requests
from time import time
from uuid import uuid4


class Node(object):
    def __init__(self, host, port):
        self.socket = host+':'+str(port)
        self.peers = set()
        self.users = dict()
        self.transaction_pool = dict()
        self.user_balence_pool = dict()
        self.blockchain = Blockchain(self)
        # Raft
        self.raft = None
        self.uncommitted_user = None
        self.uncommitted_transaction = None
        # broadcast_ methods: for broadcast user requests by sending message to raft module
        # add_* methods: for verifying changes validity and storing changes
        # commit_* methods: for committing all changes and updating all relating status


    ###############
    # Node setting
    ###############

    def set_raft(self, raft):
        self.raft = raft

    def get_socket(self):
       return self.socket

    # Initialization node by replicating from ann existing peer node
    def clone_from_peer(self, peer):
        try:
            response = requests.get(url=f'http://{peer}/node/clone', timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
            if response.status_code == 200:
                replica = response.json()  
                for p in replica.get('peers'):
                    self.add_peer(p)
                self.users = replica.get('users')
                self.transaction_pool = replica.get('transaction_pool')
                self.user_balence_pool = replica.get('user_balence_pool')
                self.blockchain.set_chain(replica.get('blockchain'))
                return True
        except Exception as e:
            print(e)
        return False


    ####################
    # P2P Network Peers
    ####################

    def get_peers(self):
       return list(self.peers)

    def register_peer(self, peer):
        if peer!=self.socket:
            try:
                response = requests.get(url=f'http://{peer}/', timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
                if response.status_code == 200:
                    self.broadcast_peer(peer)
                    self.peers.add(peer)
                    return True
            except Exception as e:
                print(e)
        return False

    def add_peer(self, peer):
        if peer!=self.socket:
            self.peers.add(peer)
            return True
        return False

    def broadcast_peer(self, peer):
        json = { 'peer': peer }
        for node in self.peers:
            try:
                response = requests.post(url=f'http://{node}/peer/add', json=json , timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
            except Exception as e:
                print(e)


    ###############
    # Users
    ###############

    def get_users(self):
        return self.users

    def register_user(self, user, password):
        if user in self.users:
            return False
        self.broadcast_user(user, password)
        return True

    def add_user(self, user, password):
        if user not in self.users:
            self.uncommitted_user = (user, password)
            return True
        return False

    def commit_user(self):
        if self.uncommitted_user is not None:
            user = self.uncommitted_user[0]
            password = self.uncommitted_user[1]
            self.users[user] = password
            self.user_balence_pool[user] = config.NEW_USER_REWARD
            self.uncommitted_user = None
            return True
        return False

    def broadcast_user(self, user, password):
        json = { 'username': user, 'password': password, 'type': 'broadcast_user' }
        self.raft.handle_message(json)

    def authenticate_user(self, user, password):
        return self.users.get(user) == password


    #############################
    # Transactions and Balences
    ##############################

    def get_transaction_pool(self):
        return self.transaction_pool

    def get_transaction_pool_as_list(self):
        return list(self.transaction_pool.values())

    def reset_transaction_pool(self):
        self.transaction_pool = dict()


    def start_transaction(self, sender, recipient, amount):
        if self.verify_transaction(sender, recipient, amount):
            transaction = self.create_transaction(sender, amount, recipient)
            self.broadcast_transaction(transaction)
            return transaction
        else:
            return None

    def add_transaction(self, transaction):
        transaction_id = transaction.get('transaction_id')
        sender = transaction.get('sender')
        recipient = transaction.get('recipient')
        amount = transaction.get('amount')
        if self.verify_transaction(sender, recipient, amount):
            self.uncommitted_transaction = transaction
            return True
        return False

    def commit_transaction(self):
        if self.uncommitted_transaction is not None:
            transaction_id = self.uncommitted_transaction.get('transaction_id')
            sender = self.uncommitted_transaction.get('sender')
            recipient = self.uncommitted_transaction.get('recipient')
            amount = self.uncommitted_transaction.get('amount')
            self.transaction_pool[transaction_id] = self.uncommitted_transaction
            self.update_user_balence_pool(sender, recipient, amount)
            self.uncommitted_transaction = None
            return True
        return False

    def broadcast_transaction(self, transaction):
        json = { 'transaction': transaction, 'type': 'broadcast_transaction' }
        self.raft.handle_message(json)


    def verify_transaction(self, sender, recipient, amount):
       if self.user_balence_pool.get(sender) is None or self.user_balence_pool.get(recipient) is None:
          return False
       return self.user_balence_pool.get(sender) >= amount

    @staticmethod
    def create_transaction(sender, amount, recipient):
        return {
            'transaction_id': str(uuid4()),
            'sender': sender, 
            'recipient': recipient, 
            'amount': amount,
            'timestamp': int(time())
        }


    def get_user_balence_pool(self):
        return self.user_balence_pool

    def update_user_balence_pool(self, sender, recipient, amount):
        self.user_balence_pool[sender] = self.user_balence_pool.get(sender) - amount
        self.user_balence_pool[recipient] = self.user_balence_pool.get(recipient) + amount


    ###############
    # Blockchain
    ###############

    def get_full_chain(self):
        return self.blockchain.get_chain()

    def get_last_block(self):
        return self.blockchain.get_last_block()

    def get_committed_user_balences(self):
        return self.blockchain.get_committed_user_balences()

    def mine(self, miner):
        new_block = self.blockchain.mine(miner)
        if new_block is not None:
            new_blockchain = self.blockchain.get_chain().copy()
            new_blockchain.append(new_block)
            self.broadcast_chain(new_blockchain)
        return new_block


    def add_chain(self, chain):
        return self.blockchain.add_cahin(chain)

    def commit_chain(self):
        return self.blockchain.commit_chain()

    def broadcast_chain(self, chain):
        json = { 'blockchain': chain, 'type': 'broadcast_chain' }
        self.raft.handle_message(json)

    '''
    def add_block(self, block):
        return self.blockchain.add_block(block)

    def broadcast_block(self, block):
        pass
    '''
