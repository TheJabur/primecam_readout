# CCATpHive

See /docs for more information about this project.

## File Descriptions:
- **_cfg_board.py**: Board configuration options.
- **queen.py**: Runs on the command server to publish commands to remote boards, and to listen for messages from the boards. Should be running at all times in listen mode to pick up board messages.
- **queen_tui.py**: A terminal interface to queen.py.
- **drone.py**: Runs on each of the boards (4 instances) and listens for commands. Upon receiving a command it asks alcove.py to execute it and publishes any necessary messages, e.g. the return statement. Should be running at all times to hear commands.
- **alcove.py**: Mediator to the board functionality functions (commands).
- **alcove_tui.py**: A terminal interface to alcove.py.
- **/alcove_commands**: Modules containing the functions to perform board tasks.
    - **board_utilities.py**: Basic board utility tools.
    - **single_chan.py**: Gateware functions.
    - **test_functions.py**: Testing functions.
- **/queen_commands**: Modules containing the functions to perform server tasks.
    - **test_functions**: Testing functions.

## Redis Channels:
- There is a command channel to send to all boards at once (all_boards).
- Each board has it's own command channel (board_[bid]) and return channel (board_rets_[bid]).