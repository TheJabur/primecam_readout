
import os

# =========================================================================== #
# gatewareInfoFromBoardCfg
def gatewareInfoFromBoardCfg(cfg_b):
    # MUST use *_v[version]p* as gateware filename
    gateware_file = os.path.join(cfg_b.dir_root, cfg_b.gateware_file)
    gateware_fname = os.path.splitext(os.path.basename(gateware_file))[0]
    gateware_fname_parts = re.search(r'_v(\d+)p(\d+)', gateware_fname)
    gateware_version = int(gateware_fname_parts.group(1)) 
    gateware_version_minor = int(gateware_fname_parts.group(2))
    return gateware_file, gateware_version, gateware_version_minor

try:
    gateware_file, gateware_version, gateware_version_minor = \
        gatewareInfoFromBoardCfg(cfg_b)
except:
    gateware_version = 15 # default, mostly for control computer

if gateware_version >= 15:
    from alcove_commands.alcove_base_gen2 import *
else:
    from alcove_commands.alcove_base_gen1 import *