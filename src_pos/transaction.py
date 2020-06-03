from time import time
from uuid import uuid4
import json
import hashlib
from config import TRANSACTION_FEE
from wallet import Wallet
from config import TRANSACTION_THRESHOLD

"""
Structure of transaction: 
{
  id: <here goes some identifier>
  type: <transactions type: stake,validator,transaction>
  input: {
          timestamp: <time of creation>,
          from: <senders address>,
          signature: <signature of the transaction>
         }
  output: {
           to: <recievers address>
           amount: <amount transfered>
           fee: <transactions fee>
          }
}
"""


class Transaction(object):
    def __init__(self):
        self.id = str(uuid4())
        self.type = ""
        self.input = ""
        self.output = ""

    def __str__(self):
        id = "id: " + self.id
        type = "type: " + self.type

        input = "input: {timestamp:" + str(self.input["timestamp"]) + ", from: " + str(self.input["from"]) + \
                ", signature: " + str(self.input["signature"]) + "}"
        output = "output: {to:" + self.output["to"] + ", amount: " + str(self.output["amount"]) + \
                ", fee: " + str(self.output["fee"]) + "}"
        return "{\n"+id+"\n"+type+"\n" + input + "\n" + output + "\n}"

    def __eq__(self, other):
        return self.id == other.id

    @staticmethod
    def new_transaction(senderWallet, to, amount, type):
        # Adds a new transaction to the list of transactions
        """
        Creates a new transaction to go into the next mined Block
        :param sender: <Account> detail of the sender account
        :param to: <str> Address of the Recipient (public key)
        :param amount: <int> Amount
        :param type: <transactions type: stake, validator, transaction>
        :return: <int> The index of the Block that will hold this transaction
        """
        if amount + TRANSACTION_FEE > senderWallet.balance:
            print('Not enough balance')
            return False
        return Transaction.generateTransaction(senderWallet, to, amount, type)

    @staticmethod
    def generateTransaction(senderWallet, to, amount, type):
        transaction = Transaction()
        transaction.type = type
        transaction.output = {
            "to": to,
            "amount": amount - TRANSACTION_FEE,
            "fee": TRANSACTION_FEE
        }
        Transaction.signTransaction(senderWallet, transaction)
        print(transaction)
        return transaction

    @staticmethod
    def hash(data):
        block_string = json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @staticmethod
    def signTransaction(senderAccount, transaction):
        transaction.input = {
            "timestamp": time(),
            "from": senderAccount.publicKey,
            "signature": senderAccount.sign_ECDSA_msg(Transaction.hash(transaction.output)).decode()
        }

    @staticmethod
    def verifyTransaction(transaction):
        return Wallet.validate_signature(transaction.input["from"],
                                          transaction.input["signature"],
                                          Transaction.hash(transaction.output))


class TransactionPool(object):
    def __init__(self):
        self.transactions = []

    # def __str__(self):
    #     return str(self.transactions)

    # return true when we hit the threshold
    def addTransaction(self, transaction):
        self.transactions.append(transaction)
        if len(self.transactions) >= TRANSACTION_THRESHOLD:
            return True
        return False

    def validTransactions(self):
        for transaction in self.transactions:
            if not Transaction.verifyTransaction():
                print("Invalid signature from transaction:" + str(transaction.id))
                return False
        return True

    def transactionExists(self, transaction):
        for t in self.transactions:
            if transaction.id == t.id:
                return True
        return False

    def clear(self):
        self.transactions = []
