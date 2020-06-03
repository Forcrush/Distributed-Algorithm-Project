import hashlib
import json
from time import time

from wallet import Wallet


class Block(object):
    def __init__(self, timestamp, previous_hash, hash, transactions, validator, signature):
        """Returns a new Block object. Each block is "chained" to its previous
        by calling its unique hash.

        Attributes:
            timestamp (int): Block creation timestamp.
            transactions [dict{}]: Transactions to be sent.
            previous_hash(str): String representing previous block unique hash.
            hash (str): hash of the current block
            validator(str): the address of the guy/gal whose made this block
            signature(str): the encrypted hash of the block, signed by the validator


        """

        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.hash = hash
        self.validator = validator
        self.signature = signature
        self.transactions = transactions

    def __str__(self):
        return 'Block - ' \
               'Timestamp: ' + str(self.timestamp) + \
               'Previous_hash: ' + str(self.previous_hash) + \
               'Hash: ' + str(self.hash) +\
               'Transactions: ' + str(self.transactionsToStringList()) + \
               'Validator: ' + str(self.validator) + \
               'Signature: ' + str(self.signature)

    def transactionsToStringList(self):
        temp = []
        for transaction in self.transactions:
            temp.append(str(transaction))
        return temp

    def __eq__(self, other):
        return self.hash == other.hash and self.previous_hash == other.previous_hash and self.validator == other.validator

    def isTransactionExist(self, transaction):
        if transaction in self.transactions:
            return True
        return False

    @staticmethod
    def createBlock(lastBlock, transactions, wallet):
        timestamp = time()
        previous_hash = lastBlock.hash
        hash = Block.hash(timestamp, previous_hash, transactions)
        validator = wallet.publicKey
        signature = Block.signBlockHash(hash, wallet)
        return Block(timestamp, previous_hash, hash, transactions, validator, signature)

    @staticmethod
    def signBlockHash(hash, wallet):
        return wallet.sign_ECDSA_msg(hash)

    @staticmethod
    def genesis():
        return Block(time(), "----", "", [], "", "")

    @staticmethod
    def hash(timestamp, previous_hash, transactions):
        dict_transactions = []
        for t in transactions:
            dict_transactions.append(t.__dict__)

        temp_dict = {
            "timestamp": timestamp,
            "previous_hash": previous_hash,
            "transactions": dict_transactions
        }
        block_string = json.dumps(temp_dict, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @staticmethod
    def blockHash(block):
        return Block.hash(block.timestamp, block.previous_hash, block.transactions)

    @staticmethod
    def verifyBlock(block):
        return Wallet.validate_signature(block.validator, block.signature, Block.blockHash(block))

    @staticmethod
    def verifyLeader(block, leader):
        return block.validator == leader


