## board_io.py

#####################
# Global attributes #
#####################

from base_io import *

try:
    import _cfg_board as cfg
except Exception as e: 
    print(f"board_io.py global attribute issue.")



#######################
# Internal attributes #
#######################

class file:
# parameters:
    # required:
        # fname           (str) Base filename (sans extension).
        # file_type       (str) Dictates extension and saving method.
        # dname           (str) Absolute directory containing fname.
    # optional:
        # use_timestamp   (bool) Append timestamp to filename.

    class _freqs_vna:
        def __get__(self, obj, cls):
            return {
                'fname'         :'freqs_vna',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/vna',
                'use_timestamp' :True}
    freqs_vna = _freqs_vna()

    class _s21_vna:
        def __get__(self, obj, cls):
            return {
                'fname'         :'s21_vna',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/vna',
                'use_timestamp' :True}
    s21_vna = _s21_vna()

    class _f_center_vna:
        def __get__(self, obj, cls):
            return {
                'fname'         :'f_center_vna',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/vna',
                'use_timestamp' :True}
    f_center_vna = _f_center_vna()

    class _f_res_vna:
        def __get__(self, obj, cls):
            return {
                'fname'         :'f_res_vna',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/vna',
                'use_timestamp' :True}
    f_res_vna = _f_res_vna()

    class _f_center_targ:
        def __get__(self, obj, cls):
            return {
                'fname'         :'f_center_targ',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/targ',
                'use_timestamp' :True}
    f_center_targ = _f_center_targ()

    class _f_res_targ:
        def __get__(self, obj, cls):
            return {
                'fname'         :'f_res_targ',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/targ',
                'use_timestamp' :True}
    f_res_targ = _f_res_targ()

    class _a_res_targ:
        def __get__(self, obj, cls):
            return {
                'fname'         :'a_res_targ',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/targ',
                'use_timestamp' :True}
    a_res_targ = _a_res_targ()

    class _f_cal_tones:
        def __get__(self, obj, cls):
            return {
                'fname'         :'f_cal_tones',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/cal_tones',
                'use_timestamp' :True}
    freqs_vna = _freqs_vna()