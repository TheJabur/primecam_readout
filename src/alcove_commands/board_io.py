# ============================================================================ #
# board_io.py
# File management for the boards.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2024
# ============================================================================ #



from base_io import *

try:
    from config import board as cfg
except Exception as e: 
    print(f"board_io.py global attribute issue.")



class file:
# parameters:
    # required:
        # fname           (str) Base filename (sans extension).
        # file_type       (str) Dictates extension and saving method.
        # dname           (str) Absolute directory containing fname.
    # optional:
        # use_timestamp   (bool) Append timestamp to filename.


    class _IQ_generic:
        def __get__(self, obj, cls):
            return {
                'fname'         :'IQ_generic',
                'file_type'     :'npy', 
                'dname'         :cfg.root_dir+'/tmp',
                'use_timestamp' :True}
    IQ_generic = _IQ_generic()


# ============================================================================ #
# NCLO
# ============================================================================ #

    class _f_center_vna:
        def __get__(self, obj, cls):
            return {
                'fname'         :'f_center_vna',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/vna',
                'use_timestamp' :True}
    f_center_vna = _f_center_vna()


# ============================================================================ #
# VNA sweep
# ============================================================================ #

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

    class _f_res_vna:
        def __get__(self, obj, cls):
            return {
                'fname'         :'f_res_vna',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/vna',
                'use_timestamp' :True}
    f_res_vna = _f_res_vna()

    class _phis_vna:
        def __get__(self, obj, cls):
            return {
                'fname'         :'phis_vna',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/vna',
                'use_timestamp' :True}
    phis_vna = _phis_vna()
    
    class _amps_vna:
        def __get__(self, obj, cls):
            return {
                'fname'         :'amps_vna',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/vna',
                'use_timestamp' :True}
    amps_vna = _amps_vna()



# ============================================================================ #
# Target sweep
# ============================================================================ #

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

    class _p_res_targ:
        def __get__(self, obj, cls):
            return {
                'fname'         :'p_res_targ',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/targ',
                'use_timestamp' :True}
    p_res_targ = _p_res_targ()
    
    class _s21_targ:
        def __get__(self, obj, cls):
            return {
                'fname'         :'s21_targ',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/targ',
                'use_timestamp' :True}
    s21_targ = _s21_targ()

    class _f_cal_tones:
        def __get__(self, obj, cls):
            return {
                'fname'         :'f_cal_tones',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/cal_tones',
                'use_timestamp' :True}
    f_cal_tones = _f_cal_tones()


# ============================================================================ #
# Current comb
# ============================================================================ #

    class _f_rf_tones_comb:
        def __get__(self, obj, cls):
            return {
                'fname'         :'f_rf_tones_comb',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/comb',
                'use_timestamp' :True}
    f_rf_tones_comb = _f_rf_tones_comb()

    class _a_tones_comb:
        def __get__(self, obj, cls):
            return {
                'fname'         :'a_tones_comb',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/comb',
                'use_timestamp' :True}
    a_tones_comb = _a_tones_comb()

    class _p_tones_comb:
        def __get__(self, obj, cls):
            return {
                'fname'         :'p_tones_comb',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/comb',
                'use_timestamp' :True}
    p_tones_comb = _p_tones_comb()


# ============================================================================ #
# Custom comb files
# ============================================================================ #

    class _f_rf_tones_comb_cust:
        def __get__(self, obj, cls):
            return {
                'fname'         :'f_rf_tones_comb_cust',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/custom_comb',
                'use_timestamp' :False}
    f_rf_tones_comb_cust = _f_rf_tones_comb_cust()

    class _a_tones_comb_cust:
        def __get__(self, obj, cls):
            return {
                'fname'         :'a_tones_comb_cust',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/custom_comb',
                'use_timestamp' :False}
    a_tones_comb_cust = _a_tones_comb_cust()

    class _p_tones_comb_cust:
        def __get__(self, obj, cls):
            return {
                'fname'         :'p_tones_comb_cust',
                'file_type'     :'npy', 
                'dname'         :cfg.drone_dir+'/custom_comb',
                'use_timestamp' :False}
    p_tones_comb_cust = _p_tones_comb_cust()