import base64
import ecdsa
import config
import requests
import pickle


# User that operates on the server.
class Wallet(object):
    def __init__(self, pubKey=None, priKey=None):
        self.balance = 0
        if pubKey and priKey:
            self.publicKey = pubKey
            self.privateKey = priKey
        else:
            self.publicKey, self.privateKey = Wallet.generate_ECDSA_keys()

    def __str__(self):
        return "Wallet -" \
               "publicKey: " + str(self.publicKey) + \
               "balance: " + str(self.balance)

    def changeWallet(self, pubKey, priKey):
        self.balance = 0
        self.publicKey = pubKey
        self.privateKey = priKey

    @staticmethod
    def generate_ECDSA_keys():
        """This function takes care of creating your private and public (your address) keys.
        It's very important you don't lose any of them or those wallets will be lost
        forever. If someone else get access to your private key, you risk losing your coins.

        private_key: str
        public_ley: base64 (to make it shorter)
        """
        sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)  # this is your sign (private key)
        private_key = sk.to_string().hex()  # convert your private key to hex
        vk = sk.get_verifying_key()  # this is your verification key (public key)
        public_key = vk.to_string().hex()
        # we are going to encode the public key to make it shorter
        public_key = base64.b64encode(bytes.fromhex(public_key))

        filename = input("Please enter the file name to store your key: ") + ".txt"
        with open(filename, "w") as f:
            f.write("Private key: {0}\nWallet address / Public key: {1}".format(private_key, public_key.decode()))
        print("Your new address and private key are now in the file {0}".format(filename))
        return public_key, private_key

    def sign_ECDSA_msg(self, dataHash):
        """Sign the message to be sent
        private_key: must be hex

        return
        signature: base64 (to make it shorter)
        message: str
        """
        # Get timestamp, round it, make it into a string and encode it to bytes
        # message = str(round(time.time()))
        bmessage = dataHash.encode()
        sk = ecdsa.SigningKey.from_string(bytes.fromhex(self.privateKey), curve=ecdsa.SECP256k1)
        signature = base64.b64encode(sk.sign(bmessage))
        return signature

    def createTransaction(self, to, amount, type, blockchain, transactionPool):
        self.balance = blockchain.getBalance(self.publicKey)

        if amount > self.balance:
            print("Not enough money")
            return False
        from transaction import Transaction
        transaction = Transaction.new_transaction(self, to, amount, type)
        transactionPool.addTransaction(transaction)
        return transaction

    def getBalance(self, blockchain):
        return blockchain.getBalance(self.publicKey)

    @staticmethod
    def validate_signature(public_key, signature, message):
        """Verifies if the signature is correct. This is used to prove
        it's you (and not someone else) trying to do a transaction with your
        address. Called when a user tries to submit a new transaction.
        """
        public_key = (base64.b64decode(public_key)).hex()
        signature = base64.b64decode(signature)
        vk = ecdsa.VerifyingKey.from_string(bytes.fromhex(public_key), curve=ecdsa.SECP256k1)
        # Try changing into an if/else statement as except is too broad.
        try:
            return vk.verify(signature, message.encode())
        except:
            return False


def control_panel():
    response = None
    while response not in ["1", "2", "3"]:
        response = input("""What do you want to do? Please enter the number:
            1. Login 
            2. Register\n""")

    if response == "2":
        print("""=========================================\n
           IMPORTANT: save this credentials or you won't be able to recover your wallet\n
           =========================================\n""")
        Wallet.generate_ECDSA_keys()
    wallet = Wallet("1", "1")
    while True:
        print("===============================\n LOGIN PROCESS \n===============================\n")

        publicKey = input("From: introduce your wallet address (public key)\n")
        privateKey = input("Introduce your private key\n")

        if not send_login_request(publicKey, privateKey):
            continue
        else:
            wallet.changeWallet(publicKey, privateKey)
            break

    while True:
        response = input(f"""User: {wallet.publicKey}
                    What do you want to do?
                    1. Become validator and add stake 
                    2. Send coins to another wallet (TRANSACTION_FEE = {config.TRANSACTION_FEE})
                    3. Check all pending transactions
                    4. Check account balance
                    5. Check my transactions that has been executed
                    6. Check all transactions that has been executed (admin)
                    7. Check all balance (admin)
                    8. Check connected peers 
                    9. Check Validators and Stake
                    0. Exit \n""")
        if response == "1":
            url = config.HOSTPORT + "/isValidator"
            res = requests.get(url)
            if res.text == "False":
                response = input("""You need to register to become a validator. The registration fee is 10 coins. 
                                Do you want to continue?  y/n\n""")
                if response.lower() == "y":
                    response = create_transaction("0", 10, "validator")
                    if response == 200:
                        add_stake()
            else:
                add_stake()
        elif response == "2":
            addr_to = input("To: introduce destination wallet address\n")
            amount = input("Amount: number stating how much do you want to send\n")
            try:
                amount = int(amount)
            except ValueError:
                print("Invalid Input! Must be Integer. Please try again.")
                continue
            print("Is everything correct?\n")
            print("From: {0}\nPrivate Key: {1}\nTo: {2}\nAmount: {3}\n".format(wallet.publicKey, wallet.privateKey,
                                                                               addr_to, amount))
            response = input("y/n\n")
            if response.lower() == "y":
                create_transaction(addr_to, amount, "transaction")
        elif response == "3":
            check_transactions()
        elif response == "4":
            check_account_balance()
        elif response == "5":
            check_user_block_transactions(wallet.publicKey)
        elif response == "6":
            check_block_transactions()
        elif response == "7":
            check_all_balance()
        elif response == "8":
            check_peers()
        elif response == "9":
            check_validator_and_peers()
        elif response == "0":
            break
        else:
            continue


def check_validator_and_peers():
    url = config.HOSTPORT + "/validatorsAndStake"
    res = requests.get(url)
    print("======================= Validator and Stake ======================\n")
    print(res.text)
    print("==================================================================\n")


def check_peers():
    url = config.HOSTPORT + "/peer/list"
    res = requests.get(url)
    print("======================= Peers List ======================\n")
    print(res.text)
    print("==========================================================\n")


def check_all_balance():
    url = config.HOSTPORT + "/balance"
    res = requests.get(url)
    print("=================== All Account Balance ======================\n")
    print(res.text)
    print("==========================================================\n")


def check_user_block_transactions(publicKey):
    url = config.HOSTPORT + "/user/transaction"
    res = requests.get(url)
    transactions = pickle.loads(res.content)
    print("=================== All Executed User Transactions ======================\n")
    print("User: " + publicKey + "\n")
    if len(transactions) == 0:
        print("No records. \n")
    for t in transactions:
        print(t)
    print("===================================================================\n")


def check_block_transactions():
    url = config.HOSTPORT + "/chain"
    res = requests.get(url)
    chain = pickle.loads(res.content)
    print("=================== All Executed Transactions ======================\n")
    print("block length:")
    print(len(chain))
    for block in chain:
        print("validator: " + str(block.validator))
        print("transaction length:")
        print(len(block.transactions))
        for t in block.transactions:
            print(t)
    print("====================================================================\n")


def create_transaction(to, amount, type):
    url = config.HOSTPORT + "/new_transaction"
    payload = {
        "to": to,
        "amount": amount,
        "type": type
    }
    headers = {"Content-Type": "application/json"}
    res = requests.post(url, json=payload, headers=headers)
    if res.status_code == 200:
        print("Transaction Created!\n")
    else:
        print(res.text)
    return res.status_code


def add_stake():
    url = config.HOSTPORT + "/user/stake"
    res = requests.get(url)
    print("Your current stake is: \n" + res.text)
    response = input("Do you want to add more? \n y/n\n")
    if response.lower() == "y":
        print("Your account balance is: ")
        check_account_balance()
        response = input("Please enter the number of stake to added:\n")
        try:
            amount = int(response)
            create_transaction("0", amount, "stake")
        except ValueError:
            print("Invalid Input! Please try again.")


def check_account_balance():
    url = config.HOSTPORT + "/user/balance"
    res = requests.get(url)
    print("=================== Account Balance ======================\n")
    print(res.text)
    print("==========================================================\n")


def check_transactions():
    """Retrieve the entire blockchain. With this you can check your
    wallets balance. If the blockchain is to long, it may take some time to load.
    """
    url = config.HOSTPORT + "/transactions"
    res = requests.get(url)
    transactions = pickle.loads(res.content)
    print("=================== All Pending Transactions ======================\n")
    if len(transactions) == 0:
        print("No records.")
    else:
        for transaction in transactions:
            print(transaction)
    print("==================================================================\n")


def send_login_request(publicKey, privateKey):
    if len(privateKey) == 64:
        wallet = Wallet(publicKey, privateKey)
        signature = wallet.sign_ECDSA_msg("")
        isValid = wallet.validate_signature(publicKey, signature, "")
        if isValid:
            url = config.HOSTPORT + "/login"
            payload = {"publicKey": publicKey,
                       "privateKey": privateKey}
            headers = {"Content-Type": "application/json"}
            res = requests.post(url, json=payload, headers=headers)
            print(res.text)
            return True
    print("Wrong address or key length! Verify and try again.")
    return False


if __name__ == '__main__':
    print("""       =========================================\n
        POS v1.0.0 - BLOCKCHAIN SYSTEM\n
       =========================================\n\n\n""")
    control_panel()
    input("Press ENTER to exit...")
