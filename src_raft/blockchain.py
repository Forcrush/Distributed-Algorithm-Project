import config
import hashlib
import json
from time import time
from uuid import uuid4


# Blockchain implementation for raft consensus algorithm
class Blockchain(object):
    def __init__(self, node):
        self.node = node
        self.chain = []
        # Raft: for uncommited changes
        self.uncommitted_user_balence_pool = dict()
        self.uncommitted_chain = None
        genesis_block = self.create_new_block()
        self.chain.append(genesis_block)


    def get_chain(self):
        return self.chain

    def get_last_block(self):
        return self.chain[-1];

    def get_committed_user_balences(self):
        return self.chain[-1].get('user_balences').copy()

    def set_chain(self, chain):
        self.chain = chain


    @staticmethod
    def hash(block):        
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


    def create_new_block(self, miner=None):
        transactions = list()
        if miner is not None:
            transactions.append(self.create_mining_reward(miner))
            transactions += self.node.get_transaction_pool_as_list()
        user_balences = self.uncommitted_user_balence_pool
        previous_block_hash = self.hash(self.get_last_block()) if len(self.chain)>0 else None

        block = {
            'index': len(self.chain),
            'previous_block_hash': previous_block_hash,
            'timestamp': int(time()),
            'transactions': transactions,
            'user_balences': user_balences
        }
        return block


    # Mining a new block and committing all transactions
    def mine(self, miner):
        # Stores uncomitted changes
        self.uncommitted_user_balence_pool = self.node.user_balence_pool.copy()
        self.uncommitted_user_balence_pool[miner] += config.MINING_REWARD
        candidate_block = self.create_new_block(miner)
        return candidate_block

    @staticmethod
    def create_mining_reward(miner):
        return {
            'transaction_id': str(uuid4()),
            'sender': 'SYSTEM',
            'recipient': miner, 
            'amount': config.MINING_REWARD,
            'timestamp': int(time())
        }


    # A block is valid if the previous_block_hash field equals to the hash of the previous block
    def verify_block(self, block):
        if block.get('index') == len(self.chain) and block.get('previous_block_hash') == self.hash(self.chain[-1]):
            return True
        return False

    def verify_chain(self, chain):
        for i in range(1, len(chain)):
           if chain[i].get('previous_block_hash') != self.hash(chain[i-1]):
              return False
        return True;

    # Verifird the whole chain. If its valid, stores the changes
    def add_cahin(self,chain):
        if len(chain) <= len(self.chain):
            return False
        last_block = chain[-1]
        # Stores uncomitted changes
        if self.verify_block(last_block):
            self.uncommitted_chain = chain
            return True
        elif self.verify_chain(chain):
            self.uncommitted_chain = chain
            return True
        return False

    # Committing all changes on blockchain and updatig all status
    def commit_chain(self):
        if self.uncommitted_user_balence_pool is not None and self.uncommitted_chain is not None:
            self.chain = self.uncommitted_chain
            self.node.reset_transaction_pool()
            self.node.user_balence_pool = self.get_committed_user_balences()
            self.uncommitted_user_balence_pool = dict()
            self.uncommitted_chain = None
            return True
        return False
