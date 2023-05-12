# CCATpHive

See /docs for more information about this project.

## File Descriptions:
- **alcove_commands/**: Modules containing the functions to perform board tasks.
    - **board_io.py**: Extends base_io.py on the boards.
    - **board_utilities.py**: Basic board utility tools.
    - **init.py**: Initialization script. Must be run to initialize the board.
    - **multi_chan.py**: Gateware functions (four channel).
    - **single_chan.py**: Deprecated. Gateware functions (single channel).
    - **test_functions.py**: Testing functions.
- **docs/**: Documentation and guides.
- **drones/**: The board runs four drones which each have a subdirectory (droneX, X={1,2,3,4}).
    - **droneX/**: Configuration and data files specific to drone X.
        - **cal_tones/**: Directory to hold calibration tone files.
        - **targ/**: Directory to hold target sweep files.
        - **vna/**: Directory to hold VNA sweep files.
        - **_cfg_droneX.py**: Drone X specific configuration options.
- **gui_assets/**: Assets that queen_gui.py uses.
- **logs/**: Directory that contains log files.
- **queen_commands/**: Commands which run on the control server instead of the boards.
    - **control_io.py**: Extends base_io.py on the control computer.
    - **test_functions**: Testing functions.
- **RFnetworks/**: Contains a subdirectory for each RF network this board has used. Each subdirectory contains configuration and data files specific to that RF network.
- **tmp/**: Temporary files are dumped here. On the control computer this is primarily board returns.
- **_cfg_board.py**: RFSoC board configuration options. Note that this needs to be manually created on each board from _cfg_board.bak.py.
- **_cfg_queen.py**: Control server configuration options. Note that this needs to be manually created from _cfg_queen.bak.py.
- **alcove_tui.py**: A terminal interface to alcove.py. This is used only to directly interact with alcove.py when locally on the board.
- **alcove.py**: Provides an API to the board functionality functions (commands).
- **drone.py**: Runs on each of the boards (4 instances) and listens for commands from the control server (via Redis). Upon receiving a command it asks alcove.py to execute it and publishes returns. Must be running to receive commands.
- **init_multi**: Board initialization script for four channels. Must be run after bootup.
- **init**: Deprecated. Board initialization script for single channel.
- **queen_gui.ipynb**: Graphical interface to queen.py.
- **queen_tui.py**: Terminal interface to queen.py.
- **queen.py**: Runs on the command server to publish commands (via Redis) to remote boards, and to listen for messages from the boards. Should be running at all times in listen mode to pick up board messages.
- **quickDataViewer.ipynb**: A simple Jupyter notebook to inspect data in tmp/ (which are payloads from the board functions).

## Redis Channels:
- **all_boards**: Channel to send commands to all boards at once.
- **board_[bid]**: Drones will listen to all channels that begin with this.
- **board_[bid].[drid]_[cid]**: Each board has it's own command channels. A new channel is created every time a command is issued with a random cid generated string suffix. [bid] and [drid] are the board and drone identifiers respectively (contained in _cfg_board.py) and [cid] is the command identifier which is a unique id generated when the command is sent.
- **rets_***: Boards send returns on the channel they received the command on modified with the prefix 'rets_'.

**[bid]**: Board identifier (contained in _cfg_board.py).  
**[drid]**: Drone identifier (1-4) (contained in _cfg_drone.py).  
**[cid]**: Command identifier which is a unique id generated when the command is sent.  