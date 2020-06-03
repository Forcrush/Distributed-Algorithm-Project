from config import TRANSACTION_TYPE
from account import Account
from block import Block
from stake import Stake, Validators


class Blockchain(object):
    """
    It records blocks and interacts with stake, account and validator
    """
    def __init__(self):
        # The maintained blockchain
        self.chain = [Block.genesis()]
        self.stakes = Stake()
        self.accounts = Account()
        self.validators = Validators()


    """
    It's called by node adding the new block.
    """
    def add_block(self, block):
        # block = Block.createBlock(self.chain[-1], transactions, Wallet())
        self.chain.append(block)
        print("New Block added")
        return block

    def create_block(self, transactions, wallet):
        block = Block.createBlock(self.chain[-1], transactions, wallet)
        # self.chain.append(block)
        print("New Block created")
        return block

    def valid_chain(self, chain):
        if self.chain[0] != Block.genesis():
            return False
        for i in range(1, len(chain)):
            block = chain[i]
            lastBlock = chain[i-1]
            if block.previous_hash != lastBlock.hash or \
                    block.hash != Block.blockHash(block):
                return False
        return True

    def resolve_conflicts(self, newChain):
        if len(newChain) <= len(self.chain):
            print("Not replace the chain")
            return

        if not self.valid_chain(newChain):
            print("Invalid chain")
            return

        print("Replace the current chain with the new chain")
        self.resetState()
        self.executeChain(newChain)
        self.chain = newChain

    def getBalance(self, publicKey):
        return self.accounts.getBalance(publicKey)

    def getLeader(self):
        return self.stakes.getMax(self.validators.list)

    def initialize(self, address):
        self.accounts.initialize(address)
        self.stakes.initialize(address)

    def valid_block(self, block):
        lastBlock = self.chain[-1]
        if block.previous_hash == lastBlock.hash and \
                block.hash == Block.blockHash(block) and \
                Block.verifyBlock(block) and \
                Block.verifyLeader(block, self.getLeader()):
            print("valid block")
            self.add_block(block)
            self.executeTransaction(block)
            return True
        return False
    """
    When the number of pending transactions reach the theshold, it generate the block and execute the transaction.
    """
    def executeTransaction(self, block):
        for transaction in block.transactions:
            # type == "stake"
            if transaction.type == TRANSACTION_TYPE[0]:
                self.stakes.update(transaction)
                self.accounts.decrement(
                    transaction.input["from"],
                    transaction.output["amount"]
                )
                self.accounts.transferFee(block, transaction)
            # type == "validator"
            elif transaction.type == TRANSACTION_TYPE[1]:
                if self.validators.update(transaction):
                    self.accounts.decrement(
                        transaction.input["from"],
                        transaction.output["amount"]
                    )
                    self.accounts.transferFee(block, transaction)
                else:
                    print("Error occur when trying to be a validator")
            # type == "transaction"
            elif transaction.type == TRANSACTION_TYPE[2]:
                self.accounts.update(transaction)
                self.accounts.transferFee(block, transaction)
            else:
                print("invalid transaction type: " + transaction.type)

    def executeChain(self, chain):
        for block in chain:
            self.executeTransaction(block)

    def resetState(self):
        self.chain = [Block.genesis()]
        self.stakes = Stake()
        self.accounts = Account()
        self.validators = Validators()

    def isExistTransaction(self, transaction):
        for block in self.chain:
            if block.isTransactionExist(transaction):
                return True
        return False


