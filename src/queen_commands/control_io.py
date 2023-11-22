## control_io.py
## Control computer IO module.

#####################
# Global attributes #
#####################

from base_io import *

try:
    from config import queen as cfg
except Exception as e: 
    print(f"control_io.py global attribute issue.")



#######################
# Internal attributes #
#######################

# class file:
# # parameters:
#     # required:
#         # fname           (str) Base filename (sans extension).
#         # file_type       (str) Dictates extension and saving method.
#         # dname           (str) Absolute directory containing fname.
#     # optional:
#         # use_timestamp   (bool) Append timestamp to filename.

#     class _tmp:
#         def __get__(self, obj, cls):
#             return {
#                 'fname'         :'tmp',
#                 'file_type'     :'npy', 
#                 'dname'         :cfg.drone_dir+'/vna',
#                 'use_timestamp' :True}
#     freqs_vna = _freqs_vna()
