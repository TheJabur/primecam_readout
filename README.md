# CCATpHive

See /docs for more information about this project.

## File Descriptions:
- **alcove_commands/**: Modules containing the functions to perform board tasks.
    - **board_utilities.py**: Basic board utility tools.
    - **init.py**: Initialization script. Must be run to initialize the board.
    - **single_chan.py**: Gateware functions (single channel).
    - **test_functions.py**: Testing functions.
- **docs/**: Documentation and guides.
- **drones/**: The board runs four drones which each have a subdirectory in here.
    - **drone1/**: Configuration and data files specific to drone 1.
        - **_cfg_drone1.py**: Drone 1 specific configuration options.
- **queen_commands/**: Commands which run on the control server instead of the boards.
    - **test_functions**: Testing functions.
- **RFnetworks/**: Contains a subdirectory for each RF network this board has used. Each subdirectory contains configuration and data files specific to that RF network.
- **_cfg_board.py**: RFSoC board configuration options.
- **_cfg_queen.py**: Control server configuration options.
- **alcove_tui.py**: A terminal interface to alcove.py. This is used only to directly interact with alcove.py when locally on the board.
- **alcove.py**: Provides an API to the board functionality functions (commands).
- **drone.py**: Runs on each of the boards (4 instances) and listens for commands from the control server (via Redis). Upon receiving a command it asks alcove.py to execute it and publishes any necessary messages, e.g. the return statement. Should be running at all times to hear commands.
- **queen_gui.ipynb**: Proof of concept graphical interface to queen.py running in a Jupyter notebook.
- **queen_tui.py**: A terminal interface to queen.py.
- **queen.py**: Runs on the command server to publish commands (via Redis) to remote boards, and to listen for messages from the boards. Should be running at all times in listen mode to pick up board messages.
- **quickDataViewer.ipynb**: A simple Jupyter notebook to inspect data in tmp/ (which are payloads from the board functions).

## Redis Channels:
- **all_boards**: Channel to send commands to all boards at once.
- **board_[bid]_[uuid]**: Each board has it's own command channels. A new channel is created every time a command is issued with a random uuid generated string suffix. [bid] is the board identifier (contained in _cfg_board.py) and [cid] is the command identifier which is a unique id generated when the command is sent.
- **rets_board_[bid]_[uuid]**: Each board has it's own return channels, similar to the command channels.
- **board_[bid].[drid]_[uuid]**: Each drone has it's own command channels. A new channel is created every time a command is issued with a random uuid generated string suffix.
- **rets_board_[bid].[drid]_[uuid]**: Each drone has it's own return channels, similar to the command channels.

**[bid]**: Board identifier (contained in _cfg_board.py).  
**[drid]**: Drone identifier (1-4) (contained in _cfg_drone.py).  
**[cid]**: Command identifier which is a unique id generated when the command is sent.  