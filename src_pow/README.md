### Components

- `app.py` : flask controller
- `blockchain.py` : functions about the wrapping transaction and linking blocks
- `node.py` : control the transactions and communicate with peer nodes
- `utility.py` : fundamental useful functions
- `config.py` : basic configuration


### Execution
Each time when you want to open a new node:
1. confirm the parameters in config.py 
2. run `app.py` (-p argument to assign port)
3. you can use Postman to interact with the enpoints
4. remember to initialize node from endpoints if necessary
 (e.g. synchronization with an existing node)
 
