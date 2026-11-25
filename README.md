# *primecam\_readout*

# Prime-Cam Readout Software Documentation

**James Burgoyne**  
jburgoyne@phas.ubc.ca  
Documentation updated: November 2026

# Overview {#overview}

`primecam_readout` is a Python readout and control suite for Prime-Cam and Mod-Cam on the CCAT Observatory's FYST telescope. A control computer (the "queen") sends commands to RFSoC boards over Redis; each board runs up to four independent drone processes, one per RF channel. The software provides a command-line interface (CLI) for development and a PCS agent for observatory control. Each drone handles RFSoC operations and can emit detector I/Q timestream packets over UDP to a separate data-acquisition (DAQ) computer.

For motivation, background, context, and overview of `primecam_readout` see Burgoyne et al. 2024:

SPIE: [https://doi.org/10.1117/12.3019028](https://doi.org/10.1117/12.3019028)

Arxiv: [https://doi.org/10.48550/arXiv.2406.01858](https://doi:10.48550/arXiv.2406.01858)

# Table of contents {#table-of-contents}

[**Overview	1**](#overview)

[**Table of contents	1**](#table-of-contents)

[**Document notes	2**](#document-notes)

[Editor	2](#editor)

[primecam\_readout directory	3](#primecam_readout-directory)

[**Architecture	3**](#architecture)

[**Hardware	3**](#hardware)

[Control computer hardware	3](#control-computer-hardware)

[NIC	4](#nic)

[RFSoC boards hardware	4](#rfsoc-boards-hardware)

[Networks	4](#networks)

[Control network	4](#control-network)

[Timestream network	4](#timestream-network)

[Operational environment	5](#operational-environment)

[**Software Environments	5**](#software-environments)

[Control computer software environment	5](#control-computer-software-environment)

[Docker	5](#docker)

[Software setup	5](#software-setup)

[Control computer OS	5](#control-computer-os)

[Control computer software	6](#control-computer-software)

[Git	6](#git)

[Redis	6](#redis)

[Ethernet tools and PTP	6](#ethernet-tools-and-ptp)

[Control network static IP setup	7](#control-network-static-ip-setup)

[PTP setup	7](#ptp-setup)

[RFSoC software environment	7](#rfsoc-software-environment)

[RFSoC image	7](#rfsoc-image)

[RFSoC additional setup	8](#rfsoc-additional-setup)

[redis-py	8](#redis-py)

[**primecam\_readout installation	8**](#primecam_readout-installation)

[primecam\_readout control computer installation	9](#primecam_readout-control-computer-installation)

[primecam\_readout control computer Docker installation	9](#primecam_readout-control-computer-docker-installation)

[primecam\_readout control computer git installation	9](#primecam_readout-control-computer-git-installation)

[Queen configuration file	9](#queen-configuration-file)

[Master drone control	9](#master-drone-control)

[Automated drone monitoring	10](#automated-drone-monitoring)

[primecam\_readout RFSoC board installation	10](#primecam_readout-rfsoc-board-installation)

[RFSoC primecam\_readout installation	10](#rfsoc-primecam_readout-installation)

[Board configuration file	10](#board-configuration-file)

[Startup script	11](#startup-script)

[Drone daemons	11](#drone-daemons)

[**primecam\_readout file structure	12**](#primecam_readout-file-structure)

[**Redis channels	13**](#redis-channels)

[**primecam\_readout usage	14**](#primecam_readout-usage)

[Usage overview	14](#usage-overview)

[Initialization	14](#initialization)

[Basic command flow	14](#basic-command-flow)

[Control computer / queen usage	14](#control-computer-/-queen-usage)

[Control computer commands	15](#control-computer-commands)

[Board commands	15](#board-commands)

[performFullVnaSweep arguments	17](#findvnaresonators-arguments)

[Usage examples	17](#usage-examples)

[Start a drone manually	17](#start-a-drone-manually)

[Send a command to board\[s\]	18](#send-a-command-to-board[s])

[Typical usage scenario	18](#typical-usage-scenario)

# Document notes {#document-notes}

## Editor {#editor}

Throughout this document the standard editor used in example commands is `nano`. This is because `nano` has an on-screen documented control interface. Of course you can use whatever editor works for you, for example `vi`.

## `primecam_readout` directory {#primecam_readout-directory}

Several service files and shell scripts use fixed paths: board services expect `/home/xilinx/primecam_readout`, while `scripts/queen_monitor.service` expects `/home/player1/primecam_readout`. Update those paths, users, and any environment-specific settings if your installation differs. The repository directory name is `primecam_readout` (not `primecan_readout`).

# Architecture {#architecture}

The primary components are the control computer, control network, RFSoC boards, timestream network, and DAQ computer. The control computer mediates PCS or CLI requests, sends commands to boards over Redis, receives return payloads, and can monitor drone connectivity. Each board supports four drone processes. Timestream packets contain I/Q data and metadata; the DAQ computer receives these packets and handles downstream storage and processing. The UDP packet layout is documented in [docs/rfsoc_datagram.csv](docs/rfsoc_datagram.csv). Timestream generation is implemented in FPGA gateware; the Python software configures the board and controls acquisition.

# Hardware {#hardware}

## Control computer hardware {#control-computer-hardware}

The Control Computer may utilize low-specification hardware, as its primary function is to coordinate and synchronize the RFSoC boards, which do the heavy lifting. However, it is crucial that the ethernet card installed in the Control Computer facing the control network is Precision Time Protocol (PTP) enabled. This ensures accurate time synchronization across the network, a critical requirement for precise map making. A second network interface will be needed to communicate with the control computer, e.g. from the OCS.

### NIC {#nic}

Network interface cards that support IEEE 1588 (802.1as) must be used for the PTP solution. As of 2023, it was found that Intel provides the best support for Linux drivers, therefore we should baseline Intel network interface cards for Prime-Cam. Three 1GbE network interface cards were found that support PTP and have linux drivers:Intel I350-T4, Intel I350-T2V2, and Intel I210. Ethernet network cards have an issue with counterfeiters and should be purchased from electronics suppliers such as Mouser that have anti-counterfeit product statements instead of from Amazon or Newegg. Newer ethernet cards by Intel use bradyid, which is a QR code authentication and traceability program.

## RFSoC boards hardware {#rfsoc-boards-hardware}

The RFSoC boards are Xilinx ZCU111. This is a versatile FPGA platform ideal for KID readout systems. Its high-performance RFSoC architecture enables efficient processing of the large bandwidth and high data rates characteristic of KID arrays. The ZCU111's programmable logic resources allow for flexible implementation of complex digital signal processing algorithms, such as frequency domain analysis and phase-sensitive detection. Additionally, the platform's high-speed data interfaces facilitate integration with data acquisition systems and real-time data analysis pipelines.

We have custom rack-mountable board enclosures that provide DC to AC power adapter, protect (sealed Al case) and cool (fluid-cooled heat-sink), provide ports and interfaces (DC power, USB, control ethernet, timestream ethernet, 4x DAC SMA, 4x ADC SMA), integrate the additional network requirements for Prime-Cam for the timestream network (4 port 1 GbE FMC add-on card), and have dynamic digitally controllable drive and sense amplifiers and attenuators. 

## Networks {#networks}

### Control network {#control-network}

The control network facilitates communication between the control computer and the RFSoC boards using the Redis Serialization Protocol (RESP) over TCP. It employs a publish-subscribe (pub/sub) messaging pattern, and data usage is extremely efficient. The bandwidth and other specifications for this network are largely unimportant if off-the-shelf standard networking hardware is used, with the exception than the network hardware should support hardware PTP, which includes the NICs, hubs, and routers.

### Timestream network {#timestream-network}

The timestream network carries UDP packets from the RFSoC boards to the DAQ computer. The packet payload contains 1024 I/Q pairs, followed by packet metadata, a channel count, packet count, and a PTP timestamp; see [docs/rfsoc_datagram.csv](docs/rfsoc_datagram.csv). Actual bandwidth depends on the configured sample rate and the number of active drones, so provision the network and receiver for the deployed configuration.

UDP, a connectionless protocol, prioritizes speed over reliability by eliminating handshakes and acknowledgments. This makes it ideal for real-time data transfer in high-speed detector applications, where minimal latency is crucial and occasional packet loss is acceptable.

The packet structure can be seen in the rfsoc\_datagram.csv file that is part of the repo.

## Operational environment {#operational-environment}

Prime-Cam operates on Cerro Chajnantor in an ambient-coupled controlled internal atmosphere. Ambient temperature fluctuations will drive RFSoC board temperature fluctuations, which will affect clock speeds. This in turn will have an effect on tone placement. As of the writing of this document, this has not been characterized.

# Software Environments {#software-environments}

## Control computer software environment {#control-computer-software-environment}

### Docker {#docker}

Prime-Cam control software (PCS) uses Docker to manage and contain all the various software components. The architecture of `primecam_readout` has been designed to be compatible with a Docker install. Having a Docker image simplifies some aspects of the control computer setup, but increases complexity in others. At present, there is no publicly available Docker image for primecam\_readout, and instead images are built as needed, however the machinery to do so is all included in the project repo. If you are familiar with building Docker images then this should be straightforward to use, but outlining the process is beyond the scope of this document.

### Software setup {#software-setup}

The rest of this documentation assumes the control computer software environment has been set up to meet certain pre-requisites, which are outlined here.

#### Control computer OS {#control-computer-os}

The control computer OS is Linux Ubuntu 24.04. Installation can be done from a USB drive.  
[https://ubuntu.com/tutorials/create-a-usb-stick-on-ubuntu\#1-overview](https://ubuntu.com/tutorials/create-a-usb-stick-on-ubuntu#1-overview)

#### Control computer software {#control-computer-software}

##### Git {#git}

`Git` is the version control system that `primecam_readout` uses. Install from the control computer terminal.

sudo apt update  
sudo apt install git

##### Redis {#redis}

`Redis` is the TCP messaging service used by the control computer and boards. Queen and drone processes use the Python `redis` package.

Install the `Redis` server, client, and python library.

sudo apt install redis-server  
sudo apt install redis  
pip install redis

The Redis configuration file needs to be edited.

sudo nano /etc/redis/redis.conf

Configure Redis for the control-network interface and set an access password appropriate for your deployment. Make sure the Redis host, port, database, and password in the queen and board configuration files match the Redis server. Do not copy example credentials into a deployed system.

- *bind [Redis server IP address]*
- *requirepass [Redis password]*
- *tcp-keepalive 15*

Start the Redis server.

sudo systemctl start redis-server  
sudo systemctl enable redis-server

##### Ethernet tools and PTP {#ethernet-tools-and-ptp}

To support PTP across the network the control computer needs `linuxptp`.

sudo apt install linuxptp   
sudo apt install ethtool

##### Control network static IP setup {#control-network-static-ip-setup}

To connect with the RFSoC boards, your control computer needs a specific IP address. Since the boards are initially on the 192.168.2.xxx network, we'll configure your control network adapter for this range. 

Identify the network interface you want to use with the control network, e.g., enp2s0. If setting up PTP on this NIC fails then you may have chosen the wrong device.

ip a

Edit the Netplan configuration

sudo nano /etc/netplan/01-network-manager-all.yaml

and replace or modify it to look something like the following:

*network:*  
  *version: 2*  
  *ethernets:*  
    *enp2s0:*  
      *addresses:*  
        *\- 192.168.2.80/24*

Save the file and activate the changes.

sudo netplan apply

##### PTP setup {#ptp-setup}

Check the chosen NIC has hardware PTP (hardware-transmit/receive).

ethtool \-T enp1s0

## RFSoC software environment {#rfsoc-software-environment}

The RFSoC boards software is a Petalinux installation from pre-configured image, featuring Xilinx PYNQ. PYNQ is an open-source framework from AMD that facilitates embedded system design using Xilinx Zynq devices by leveraging Python, Jupyter notebooks, and Python libraries to target the programmable logic and microprocessors within Zynq platforms. This integrated setup facilitates seamless interaction with the FPGA gateware and other hardware peripherals.

### RFSoC image {#rfsoc-image}

The boards are run off of micro SD cards. We’re using a modified version 3.0.1 for the ZCU111. To write the image to the card you'll need a card reader. Make sure the RFSoC board DIP switches are in the correct position to boot from the SD card after imaging and inserting onto board, and the board is connected to the control computer on the ethernet control network. You can SSH into a freshly imaged board from the control computer:

ip: *192.168.2.99*  
user: *xilinx*  
pass: *xilinx*

ssh xilinx@192.168.2.99

The unmodified image can be downloaded here:  
[http://www.pynq.io/board.html/](http://www.pynq.io/board.html/)

And our custom image found in this Google drive:  
[https://drive.google.com/drive/folders/1IndDPkbjy8Q4VElQ37QEsqaBxuCn7emq](https://drive.google.com/drive/folders/1IndDPkbjy8Q4VElQ37QEsqaBxuCn7emq)

Instructions for writing the image:   
[https://pynq.readthedocs.io/en/latest/appendix/sdcard.html](https://pynq.readthedocs.io/en/latest/appendix/sdcard.html) 

Make sure DIP switches are in position to boot from SD card, then insert into board and boot.

### RFSoC additional setup {#rfsoc-additional-setup}

#### `redis-py` {#redis-py}

If the RFSoC board has an internet connection, then install `redis-py` using pip directly:

pip install redis==4.1.1

If the board does not have a direct internet connection, then download the wheel file for `redis-py` 4.1.1 to the computer connected to the RFSoC board from:  
[https://pypi.org/project/redis/4.1.1/\#files](https://pypi.org/project/redis/4.1.1/#files)

and transfer the wheel file to the board:

scp redis-4.1.1-py3-none-any.whl xilinx@192.168.2.99:\~

then login to the board and install using pip:

ssh xilinx@192.168.2.99  
pip install redis-4.1.1-py3-none-any.whl

# `primecam_readout` installation {#primecam_readout-installation}

The control computer and each of the boards has to be set up, as well as the control network and timestream network and the data acquisition computer. The data acquisition computer has to do a lot of heavy lifting so it’s not advisable to be the same machine as the control computer. Once the basic software and hardware environments are in place, `primecam_readout` has to be installed on the control computer and each of the RFSoC boards. 

## `primecam_readout` control computer installation {#primecam_readout-control-computer-installation}

### `primecam_readout` control computer Docker installation {#primecam_readout-control-computer-docker-installation}

The repository includes a Dockerfile and `docker-compose.yml` for running the PCS agent. The PCS Docker environment must already be running; see the [PCS documentation](https://pcs.readthedocs.io/en/latest/). From the repository root, build and start the agent:

```sh
sudo docker build -t queen_agent .
sudo docker-compose up -d
```

The compose file mounts configuration, logs, and drone data from `/home/player1/primecam_readout`; edit these host paths for your installation before starting the container.

### `primecam_readout` control computer git installation {#primecam_readout-control-computer-git-installation}

After the software environment is set up on the control computer, install `primecam_readout` and its Python dependencies.

cd \~  
git clone https://github.com/TheJabur/primecam\_readout.git
cd \~/primecam\_readout
python3 -m pip install -r requirements.txt

#### Queen configuration file {#queen-configuration-file}

`primecam_readout` needs a local configuration file after a fresh clone. The example is `cfg/_cfg_queen.bak.py`; copy it to `cfg/_cfg_queen.py` and edit the Redis connection and SSH settings:

cd \~/primecam\_readout  
cp cfg/\_cfg\_queen.bak.py cfg/\_cfg\_queen.py  
nano cfg/\_cfg\_queen.py

- *Redis server configuration*: set `host`, `port`, `db`, and `pw` to match Redis.
- *SSH credentials*: configure the account used to start/restart board services. Prefer SSH keys over a shared password where possible.
- `monitor_interval` controls drone health-check cadence; `command_return_timeout` controls how long queen waits for command returns.

#### Master drone control {#master-drone-control}

The control computer manages up to four drones per board. The configured master drone list (default filename `master_drone_list.yaml`) specifies each board/drone ID, board IP address, and whether it should run. Copy the example file and edit it:

cd \~/primecam\_readout  
cp master\_drone\_list.example.yaml master\_drone\_list.yaml   
nano master\_drone\_list.yaml

Add every drone you want running to the file with an entry that contains the board ID, drone ID, board IP address, and whether it should be running or not (to\_run), e.g.:

*'1.1': {ip: "192.168.2.99", to\_run: true}*

##### Automated drone monitoring {#automated-drone-monitoring}

A drone control system can monitor Redis connectivity and start or restart drones over SSH. It reads the configured `master_drone_list_file` (default: `master_drone_list.yaml`) to determine which board/drone pairs should run. Queen `action` commands can temporarily override that desired state.

Add the drone monitoring service on the control computer:

cd \~/primecam\_readout/scripts  
sudo cp queen\_monitor.service /etc/systemd/system/  
sudo systemctl daemon-reload  
sudo systemctl start queen\_monitor.service  
sudo systemctl enable queen\_monitor.service

Before enabling the unit, edit its hardcoded username, repository path, and Python executable to match the control computer. Check that it is running with:

sudo systemctl status queen\_monitor.service

## `primecam_readout` RFSoC board installation {#primecam_readout-rfsoc-board-installation}

### RFSoC `primecam_readout` installation {#rfsoc-primecam_readout-installation}

Prime-Cam’s RFSoC boards are not directly connected to the internet, so the `primecam_readout` repo is cloned from the control computer. On the control computer, update the repo (in the primecam\_readout directory):

cd \~/primecam\_readout  
git pull

On an RFSoC board, clone the control-computer repository over SSH. Replace the user and address with the control computer's account and control-network IP:

cd \~  
git clone user@192.168.2.80:\~/primecam\_readout

#### Board configuration file {#board-configuration-file}

`primecam_readout` needs a local board configuration file after a fresh clone. Copy the example and configure the board ID, gateware image, Redis connection, PTP interface, timestream addresses, and any board-specific hardware settings:

cd \~/primecam\_readout  
cp cfg/\_cfg\_board.bak.py cfg/\_cfg\_board.py  
nano cfg/\_cfg\_board.py

- `bid`: unique integer board ID.
- `gateware_file`: gateware image to load; it must exist on the board and match the board setup.
- Redis connection settings: must match the control computer's Redis server.
- PTP interface and peer addresses: configure for the network actually connected to the board.
- Timestream destination and per-drone source IP addresses/MAC addresses: configure for the DAQ network.
- Sample-rate and waveform settings: `acc_factor`/`scale_factors` for Gen2 or `accum_len` for Gen1.
- Sweep settings: `sweep_chan_bw` and `sweep_steps`; attenuator serial device: `atten_device`.
- Set `asu_board` to match the installed breakout board and adjust `interval_feeds` for housekeeping updates.

The board configuration is shared by the board's drone processes; the drone ID (1-4) is supplied when each process starts.

#### Startup script {#startup-script}

Each RFSoC needs to run a startup script for `primecam_readout` to operate properly, for example for the fabric gateware file to be loaded. This startup script is run as a systemd service.

cd \~/primecam\_readout/scripts  
sudo chmod \+x startup\_board.sh
sudo cp startup\_board.service /etc/systemd/system/  
sudo systemctl daemon-reload  
sudo systemctl start startup\_board.service  
sudo systemctl enable startup\_board.service

You can check that it is running properly: 

sudo systemctl status startup\_board.service

#### Drone daemons {#drone-daemons}

Each board supports up to four drones. Drones are managed by systemd. Before setting up the drone services, the `xilinx` account needs permission to start, stop, and restart those services through the queen's SSH connection.

sudo visudo

and add the following lines to the file:

xilinx ALL=(ALL) NOPASSWD: /usr/bin/systemctl start drone@\*.service  
xilinx ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop drone@\*.service  
xilinx ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart drone@\*.service

Now add the drone services:

cd \~/primecam\_readout/scripts  
sudo chmod \+x start\_drone.sh
sudo cp drone@.service /etc/systemd/system/  
sudo systemctl daemon-reload  
sudo systemctl enable drone@1.service  
sudo systemctl enable drone@2.service  
sudo systemctl enable drone@3.service  
sudo systemctl enable drone@4.service

You can start the drones now, or let the control computer start them after drone control is enabled on it. The available control commands for systemd services are: *start*, *stop*, *restart*, *status*. For example to start drone 1:

sudo systemctl start drone@1.service

# `primecam_readout` file structure {#primecam_readout-file-structure}

- **cfg/:** Example configuration templates. Copy them to `_cfg_queen.py` on the control computer and `_cfg_board.py` on each board; the active files are intentionally not tracked.
- **docs/:** Markdown documentation, packet layout, and supporting reference material.
- **drones/:** Per-drone persisted data directories (for example VNA sweeps, target sweeps, and tone files); temporary runtime data is kept under `/tmp`.
- **init/:** Board initialization scripts, PTP configuration, and gateware images.
- **scripts/:** Board startup/drone service units and scripts, queen monitor service, and maintenance utilities.
- **src/queen.py:** Control-computer Redis command publisher and return handler.
- **src/queen_cli.py:** Command-line interface for queen and board commands.
- **src/queen_agent.py:** Selects the PCS agent implementation for the installed gateware generation.
- **src/queen_agent_gen1.py, src/queen_agent_gen2.py:** PCS readout agent implementations.
- **src/drone.py:** Board-side command listener; run one process for each drone ID (1-4).
- **src/alcove.py:** Board command registry and dispatcher.
- **src/alcove_commands/:** Gateware-specific RF control, tone, sweep, analysis, I/O, and utility modules.
- **src/queen_commands/:** Control-computer test and automation commands.
- **src/redis_channels.py:** Redis pub/sub channel construction and subscriptions.
- **src/timestream.py:** UDP timestream packet capture and parsing helpers.
- **Dockerfile, docker-compose.yml:** PCS agent container build and run configuration.
- **requirements.txt:** Python dependencies for the container/control software.

# Redis channels {#redis-channels}

Commands are published on Redis channels named `board_all_<cid>`, `board_<bid>_<cid>`, or `board_<bid>.<drid>_<cid>`, depending on whether the command targets all drones, a board, or one drone. Each command ID (`cid`) is a generated UUID. Drones subscribe to the applicable board/drone patterns, including the all-board channel. A response is published on the matching channel prefixed with `rets_` (for example, `rets_board_1.2_<cid>`). The board ID comes from `_cfg_board.py`; the drone ID is passed to `drone.py` and is in the range 1-4.

# `primecam_readout` usage {#primecam_readout-usage}

## Usage overview {#usage-overview}

### Initialization {#initialization}

The basic startup routine on the control computer is to start the `Redis` server and drone monitoring. For the RFSoC boards, the initialization script needs to be run and the drones started up. For both the control computer and boards it is advised to move all of the startup functionality into system services so they are automated, as described in the setup sections of this document.

### Basic command flow {#basic-command-flow}

1\. A command is sent to queen (e.g. via queen\_cli.py or the OCS agent).  
2\. Relevant drones receive and execute the command.  
3\. The drones may send return payloads back to queen.

## Control computer / queen usage {#control-computer-/-queen-usage}

The primary job of the control computer is to send commands to boards, receive return payloads, and monitor drone connectivity. `queen.py` is used by `queen_cli.py` and by the PCS agent selected through `queen_agent.py`. Queen commands execute on the control computer; board commands are sent to one or more drone processes. Run the CLI from the repository root with `python3 src/queen_cli.py`. Its `--help` output lists the command numbers and names available in the checked-out software.

queen.py also contains functionality not directly exposed by the current interfaces, but usable by them. This includes functionality to retrieve a list of commands and convert between command numbers and names, plus low-level functions used by exposed commands.

### Control computer commands {#control-computer-commands}

| Control Computer Commands |  |  |
| :---- | :---- | :---- |
| **Number** | **Name** | **Short description** |
| 1 | alcoveCommand | Directly send command to board\[s\]. This is primarily for API access and shouldn’t be necessary for normal usage. |
| 3 | getKeyValue | Get a key-value. Primarily used for status flags.  *3 \-q \-a ‘key=\[key\]’* |
| 4 | setKeyValue | Set a key-value.  *4 \-q \-a ‘key=\[key\] value=\[value\]’* |
| 5 | getClientList | List of every client connected to Redis. This includes all clients on the controller computer as well as the boards. This client list returns the entire parameter set from Redis CLIENT\_LIST.  *5 \-q* |
| 6 | getClientListLight | Similar to getClientList, but with fewer parameters returned.  *6 \-q* |
| 7 | action | Drone control action. Possible arguments are {start, stop, restart, status, startAllDrones, stopAllDrones, restartAllDrones}. These commands will temporarily override the master drone list status.  *7 bid\[.drid\] \-q \-a ‘action=\[action\]’* |
| 8 | monitorMode | Continuously run and monitor drones for connectivity to Redis. If a drone drops, will attempt to SSH restart.  *8 \-q* |
| 9 | pollFeeds | Poll board feeds and pass them to an optional handler. |
| 14-18 | Test commands | Loopback/timestream monitoring and array tests. |

Use `python3 src/queen_cli.py --help` to see the live command list. Some registered queen commands are development/test functions and are not intended as routine observing commands.

### Board commands {#board-commands}

| Board Commands |  |  |
| :---- | :---- | :---- |
| **Number** | **Name** | **Short description** |
| 20 | setNCLO | Set the center LO frequency in MHz. |
| 21 | setFineNCLO | Set a fine LO adjustment in MHz. |
| 25 | getSnapData | Capture a hardware snapshot using `mux_sel`; available selections depend on gateware. |
| 26 | getADCrms | Convenience function to quickly determine the ADC RMS.  26 \[bid\[.drid\]\] |
| 27 | findScaleFactors | Calculate waveform scale factors for the configured tone count. |
| 29 | checkWaveformOverflow | Check the generated waveform for overflow. |
| 30 | writeTestTone | Send a single tone (at 50 MHz).  30 \[bid\[.drid\]\] |
| 32 | writeTargCombFromVnaSweep | Write a comb with tones targeted at resonators found from findVnaResonators.  32 \[bid\[.drid\]\] |
| 33 | writeTargCombFromTargSweep | Write a comb with tones targeted at resonators found from findTargResonators.  33 \[bid\[.drid\]\] |
| 34 | writeCombFromCustomList | Write a comb loaded from custom comb file.  34 \[bid\[.drid\]\] |
| 35 | createCustomCombFilesFromCurrentComb | Save current comb out to custom comb file.  35 \[bid\[.drid\]\] |
| 36 | modifyCustomCombAmps | Modify custom comb amplitudes file values by multiplicative factor.  36 \[bid\[.drid\]\] \-a ‘\[factor\]’ |
| 37 | writeTargCombFromCustomList | Calls 34 and also writes required targeted sweep files.  37 \[bid\[.drid\]\] |
| 38 | writeTestTones | Write a test comb; accepts `N` (default 1). |
| 41 | performFullVnaSweep | Write a VNA comb, sweep, find resonators, and write a target comb. Accepts resonator-finding keyword arguments. |
| 42 | targetSweep | Perform a targeted sweep after writing a target comb.  42 \[bid\[.drid\]\] |
| 44 | customSweep | Perform a sweep after writing a custom comb.  44 \[bid\[.drid\]\] |
| 51 | findTargResonators | Analyse target sweep for resonators.  51 \[bid\[.drid\]\] |
| 55 | findCalTones | Analyse the VNA sweep to place calibration tones in large gaps. |
| 60 | sys\_info | Get combined board/drone info, including config files, software versions, log events, etc.  60 \[bid\[.drid\]\] |
| 61 | sys\_info\_v | Similar to sys\_info, but less info is returned.  61 \[bid\[.drid\]\] |
| 62 | board\_temps | Return board temperature readings. |
| 65 | cleanBoardDroneDirs | Remove board/drone data directories. Use with care. |
| 70 | timestreamOn | Turn the data timestream on or off.  70 \[bid\[.drid\]\] \-a ‘\[True/False\]’ |
| 71 | userPacketInfo | Set user data in timestream packet metadata. |
| 80 | setAtten2024 | Set attenuation using `direction` and `atten` with the 2024 hardware interface. |
| 81 | setAtten2025 | Set attenuation using `direction` and `atten` with the 2025 hardware interface. |
| 82 | getAtten | Read attenuation for the requested `direction`. |

The board registry is defined in `src/alcove.py`; the implementation of several operations is selected by the installed gateware generation. For the authoritative command list on a given checkout, use the CLI `--help` output. The VNA resonator finder is called internally by command 41 and is not a separately registered command.

#### `performFullVnaSweep` arguments {#findvnaresonators-arguments}

The command accepts the keyword arguments of the VNA resonator finder in `src/alcove_commands/analysis.py`, including `peak_prom_std`, `peak_prom_db`, `peak_dis`, `width_min`, `width_max`, `stitch`, `stitch_sw`, `remove_cont`, `continuum_wn`, `remove_noise`, `noise_wn`, and the `_hz` distance/width overrides. Defaults and additional options are defined in `_findResonatorsVna`; the full VNA sweep fixes `stitch_bw=1000`.

## Usage examples {#usage-examples}

### Start a drone manually {#start-a-drone-manually}

Each board can run up to four drone services. Start or inspect a drone using systemd on the board:

sudo systemctl start drone@1.service
sudo systemctl status drone@1.service

### Send a command to board\[s\] {#send-a-command-to-board[s]}

From the repository root on the control computer, commands target one drone with `bid.drid`, every drone on a board with `bid`, or all drones when the ID is omitted:

python3 src/queen_cli.py [com_num] [bid[.drid]] [-a 'arg=value']

For a queen command, add `-q`. For example, `python3 src/queen_cli.py 8 -q` runs drone monitoring. Use square brackets in this documentation as placeholders only; do not type them unless they are part of a list ID.

### Typical usage scenario {#typical-usage-scenario}

For the current Gen2 workflow, command 41 performs the full VNA comb/sweep/resonator search and writes a target comb. Then sweep that comb, refine resonator locations, write the updated target comb, and enable timestream output:

```sh
python3 src/queen_cli.py 41
python3 src/queen_cli.py 42
python3 src/queen_cli.py 51
python3 src/queen_cli.py 33
python3 src/queen_cli.py 70 -a True
```

These commands target all drones by default. To target a specific drone, add its ID (for example, `1.2`) after the command number. Confirm the command list and behavior for the installed gateware with `python3 src/queen_cli.py --help` before running hardware operations.

