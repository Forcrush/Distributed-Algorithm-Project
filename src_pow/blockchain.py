import config
import hashlib
import json
from time import time
from uuid import uuid4


# Bitcoin-liked blockchain implementation 
# using the Proof-of-Work consensus algorithm
class Blockchain(object):
    def __init__(self, node):
        self.node = node
        self.chain = []
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
        user_balences = self.node.user_balence_pool.copy()
        previous_block_hash = self.hash(self.get_last_block()) if len(self.chain)>0 else None

        block = {
            'index': len(self.chain),
            'previous_block_hash': previous_block_hash,
            'timestamp': int(time()),
            'transactions': transactions,
            'user_balences': user_balences,
            'nonce': 0,
            'target_bits': config.TARGET_BITS
        }
        return block


    # Proof of work algorithm: A block is mined until SHA256 hash 
    # of this block matching target bits
    def mine(self, miner):
        self.node.user_balence_pool[miner] += config.MINING_REWARD
        candidate_block = self.create_new_block(miner)

        # Proof of work: Mining a block by adjusting the nonce parameter
        while self.is_valid_nonce(candidate_block, config.TARGET_BITS) is False:
            candidate_block['nonce'] += 1

        # Update pools after mining a new block and committing transactions
        self.node.reset_transaction_pool()
        self.chain.append(candidate_block)
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


    def is_valid_nonce(self, block, target_bits):
        return self.hash(block)[ : target_bits] == ''.zfill(target_bits)

    # A block is valid if hash of this block matching thr target bits
    # and the previous_block_hash field equals to the hash of the previous block
    def verify_block(self, block):
        if block.get('previous_block_hash') != self.hash(self.chain[-1]):
            return False
        if self.is_valid_nonce(block, config.TARGET_BITS) is False:
            return False
        return True;

    def verify_chain(self, chain):
        for i in range(1, len(chain)):
           if chain[i].get('previous_block_hash') != self.hash(chain[i-1]):
              return False
           if self.is_valid_nonce(chain[i], config.TARGET_BITS) is False:
              return False
        return True;

    # Proof of work: Reaching consensus on longest valid chain
    def add_cahin(self,chain):
        if len(chain) <= len(self.chain):
            return False
        last_block = chain[-1]
        if self.add_block(last_block):
            return True
        elif self.verify_chain(chain):
            self.chain = chain
            self.node.reset_transaction_pool()
            self.node.user_balence_pool = self.get_committed_user_balences()
            return True
        return False

    # Add the block to tail of chain if its valid
    def add_block(self, block):
        if block.get('index') == len(self.chain) and self.verify_block(block):
            self.chain.append(block)
            self.node.reset_transaction_pool()
            self.node.user_balence_pool = self.get_committed_user_balences()
            return True
        return False
