### Components

- `app.py` : flask controller
- `raft.py` : raft node contains basic functions such as 'Election RPC' and 'Append_Entries RPC'
- `node.py` : control the transactions and communicate with peer nodes
- `utility.py` : fundamental useful functions
- `config.py` : basic configuration

### Execution
Each time when you want to open a new node:
1. confirm the parameters in config.py 
2. run `app.py` (-p argument to assign port)
3. you can use Postman to interact with the enpoints
4. remember to initialize node from endpoints if necessary
   (e.g. start the raft thread or synchronization with an existing node)
