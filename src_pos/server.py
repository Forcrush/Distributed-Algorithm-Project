import config
import requests
import pickle


class Node(object):

    def __init__(self, host, port, blockchain):
        self.blockchain = blockchain
        self.peers = set(config.INIT_PEERS)
        self.wallet = None
        self.socket = host+':'+str(port)

    def get_socket(self):
       return self.socket

    def init_clone_from_peer(self, peerToBeCloned):
        try:
            json_content = {"peer": self.get_socket()}
            response = requests.post(url=f'http://{peerToBeCloned}/node/init', json=json_content,
                                     timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
            if response.status_code == 200:
                node = pickle.loads(response.content)
                self.blockchain = node.blockchain
                for p in node.peers:
                    if p not in self.peers:
                        self.register_peer(p)
                return node.blockchain
        except Exception as e:
            print(e)
        return False

    def get_peers(self):
       return list(self.peers)

    def register_peer(self, peer):
        if peer != self.socket:
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
        if peer != self.socket:
            self.peers.add(peer)

    def broadcast_peer(self, peer):
        json = {'peer': peer}
        for node in self.peers:
            try:
                response = requests.post(url=f'http://{node}/peer/add', json=json,
                                         timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
            except Exception as e:
                print(e)

    def broadcast_chain(self, chain):
        for peer in self.peers:
            _url = f"http://{peer}/replace_chain"
            payload = pickle.dumps(chain)
            try:
                requests.post(url=_url, data=payload, timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
            except Exception as e:
                print(e)

    def broadcast_transaction(self, transaction):
        for peer in self.peers:
            _url = f"http://{peer}/add_transaction"
            payload = pickle.dumps(transaction)
            try:
                requests.post(url = _url, data = payload, timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
            except Exception as e:
                print(e)

    def broadcast_block(self, block):
        for peer in self.peers:
            _url = f"http://{peer}/add_block"
            payload = pickle.dumps(block)
            try:
                requests.post(url = _url, data = payload, timeout=config.CONNECTION_TIMEOUT_IN_SECONDS)
            except Exception as e:
                print(e)

