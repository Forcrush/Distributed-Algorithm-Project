import config
from blockchain_pos import Blockchain
from transaction import TransactionPool
from flask import Flask, jsonify, request, redirect
from wallet import Wallet
from server import Node
import pickle

transactionPool = TransactionPool()
blockchain = Blockchain()

wallet = Wallet("1", "1")
# During initialization, query the node state from peers. If no response, initialize your own state.
node = Node(config.HOST, config.PORT, blockchain)
for p in node.peers:
    outcome = node.init_clone_from_peer(p)
    if outcome:
        blockchain = outcome
        break

app = Flask(__name__)


@app.route('/', methods=['GET'])
def get_node_availability():
    """
    It receives and process messages from user and other nodes
    """
    host_port = node.get_socket()
    response = {
        'message': f'Node on http://{host_port} is available!'
    }
    return jsonify(response), 200


@app.route('/node/init', methods=['POST'])
def process_init_node_from_peer():
    """
    Process register node request from other peers：
    1. if it's a valid node, return whole node info to it.
    2. add peer to the node peer list
    """
    body = request.get_json()
    if body is None or body.get('peer') is None:
        response = {
            'error': 'Invalid request body'
        }
        return jsonify(response), 400
    peer = body.get('peer')
    if peer == node.get_socket():
        response = {
            'error': 'Invalid peer node'
        }
        return jsonify(response), 400

    try:
        response = pickle.dumps(node)
        if peer not in node.peers:
            node.broadcast_peer(peer)
            node.add_peer(peer)
        return response, 200
    except Exception as e:
        print(e)
        response = {
            'error': f'Failed to initialize and clone from http://{peer}'
        }
        return jsonify(response), 400


@app.route('/peer/add', methods=['POST'])
def post_peer_registration():
    """
    Exchange connected peer information
    """
    body = request.get_json()
    print(body)
    if body is None or body.get('peer') is None:
        response = {
            'error': 'Invalid request body'
        }
        return jsonify(response), 400

    p = body.get('peer')
    if p not in node.peers:
        node.add_peer(peer=p)
        response = {
            'message': 'Your peer registration is successful!'
        }
        return jsonify(response), 201
    else:
        response = {
            "message": "Already have this node!"
        }
        return jsonify(response), 200


@app.route('/peer/list', methods=['GET'])
def get_node_peers():
    peers = node.get_peers()
    response = {
        'peers': peers
    }
    return jsonify(response), 200



@app.route('/login', methods=['POST'])
def generate_Wallet():
    """
    You must enter the right key, otherwise error will occur when you try to create a new transaction
    """
    values = request.get_json()
    required = ["publicKey", "privateKey"]
    if not all(k in values for k in required):
        return 'Missing values', 400
    wallet.changeWallet(values["publicKey"], values["privateKey"])
    return "Login successfully", 200


@app.route('/chain', methods=['GET'])
def show_chain():
    """
    Query the whole chain of the system.
    """
    return pickle.dumps(blockchain.chain), 200


@app.route('/transactions', methods=['GET'])
def show_all_transactions():
    """
    Query the pending transaction that have not been executed.
    """
    o = pickle.dumps(transactionPool.transactions)
    return o, 200


@app.route('/new_transaction', methods=['POST'])
def new_transactions():
    """
    Create new transaction call from wallet.
    """
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['to', 'amount', 'type']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    transaction = wallet.createTransaction(
        values["to"],
        values["amount"],
        values["type"],
        blockchain,
        transactionPool
    )
    if not transaction:
        return "Insufficient balance!", 403
    node.broadcast_transaction(transaction)
    if len(transactionPool.transactions) >= config.TRANSACTION_THRESHOLD and blockchain.getLeader() == wallet.publicKey:
        block = blockchain.create_block(transactionPool.transactions, wallet)
        blockchain.add_block(block)
        blockchain.executeTransaction(block)
        transactionPool.clear()
        node.broadcast_block(block)
    return redirect('/transactions')


@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    """
    Add transaction call from other node
    """
    transaction = pickle.loads(request.data)
    if not transactionPool.transactionExists(transaction) and not blockchain.isExistTransaction(transaction):
        threshholdReached = transactionPool.addTransaction(transaction)
        node.broadcast_transaction(transaction)
        if threshholdReached:
            if blockchain.getLeader() == wallet.publicKey:
                print("Create block")
                block = blockchain.create_block(transactionPool.transactions, wallet)
                blockchain.add_block(block)
                blockchain.executeTransaction(block)
                transactionPool.clear()
                node.broadcast_block(block)
                return "New block created", 200
    return "Transaction exists", 200


@app.route('/add_block', methods=['POST'])
def add_block():
    """
    Add block request call from other node
    """
    block = pickle.loads(request.data)
    if blockchain.valid_block(block):
        node.broadcast_block(block)
        transactionPool.clear()
        return "Block added", 201
    return "Invalid Block", 200


@app.route('/replace_chain', methods=['POST'])
def replace_chain():
    """
    Receive chain from other node
    """
    chain = pickle.loads(request.data)
    blockchain.resolve_conflicts(chain)
    return "Chain received", 200


@app.route('/isValidator', methods=['GET'])
def is_Validator():
    """
    Check it the user is a validator
    """
    response = "False"
    if wallet.publicKey in blockchain.validators.list:
        response = "True"
    return response, 200


@app.route('/validatorsAndStake', methods=['GET'])
def check_validators_and_stake():
    """
    Check the current stake.
    """
    response = {}
    for v in blockchain.validators.list:
        response[v] = blockchain.stakes.balance[v]
    return jsonify(response), 200


@app.route('/user', methods=['GET'])
def show_public_key():
    """
    Show the current login user
    """
    response = {
        'user': wallet.publicKey
    }
    return jsonify(response), 200


@app.route('/user/transaction', methods=['GET'])
def show_user_transaction():
    """
    Check user transaction that has been executed.
    """
    temp_transaction = []
    for block in blockchain.chain:
        for t in block.transactions:
            if t.input["from"] == wallet.publicKey or t.output["to"] == wallet.publicKey:
                temp_transaction.append(t)
    o = pickle.dumps(temp_transaction)
    return o, 200


@app.route('/user/balance', methods=['GET'])
def show_user_balance():
    """
    Check user's balance
    """
    response = {
        "balance": blockchain.getBalance(wallet.publicKey)
    }
    return jsonify(response), 200


@app.route('/balance', methods=['GET'])
def show_all_balance():
    response = blockchain.accounts.balance
    return jsonify(response), 200


@app.route('/user/stake', methods=['GET'])
def show_user_stake():
    response = {
        "stake": blockchain.stakes.getBalance(wallet.publicKey)
    }
    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host="127.0.0.1", port=config.PORT)
