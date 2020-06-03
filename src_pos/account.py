"""
Record and maintain the balance of each user
"""
class Account(object):
    def __init__(self):
        # self.addresses = []
        # self.balance = {}
        self.addresses =["kHdwGTsh3TiS6CDUjnw8E9mtOpGQkKoD+ODj+XaWnpg/pYriRUkP4bXUZdvkt7cHYOzlaJLFRrGIakrfTuT2kA=="]
        self.balance = {"kHdwGTsh3TiS6CDUjnw8E9mtOpGQkKoD+ODj+XaWnpg/pYriRUkP4bXUZdvkt7cHYOzlaJLFRrGIakrfTuT2kA==": 100}

    def initialize(self, address):
        if address not in self.balance:
            self.balance[address] = 100
            self.addresses.append(address)

    def transfer(self, _from, to, amount):
        self.increment(to, amount)
        self.decrement(_from, amount)

    def increment(self, to, amount):
        self.initialize(to)
        self.balance[to] += amount

    def decrement(self, _from, amount):
        self.initialize(_from)
        self.balance[_from] -= amount

    def getBalance(self, address):
        self.initialize(address)
        return self.balance[address]

    def update(self, transaction):
        amount = transaction.output["amount"]
        _from = transaction.input["from"]
        to = transaction.output["to"]
        self.transfer(_from, to, amount)

    def transferFee(self, block, transaction):
        amount = transaction.output["fee"]
        _from = transaction.input["from"]
        to = block.validator
        self.transfer(_from, to, amount)
