'''
Run the exe modifications.
'''
from Plugins import *

Settings(
    X4_exe_name = 'X4_nonsteam.exe',
    #X4_exe_name = 'X4.vanilla.exe',
    )

if 1:
    Remove_Sig_Errors()
    Remove_Modified()
    # Addition edit to mess with systemtime for high precision profiling.
    # Not for general play.
    if 0:
        High_Precision_Systemtime()

    
Write_Modified_Binaries()

# TODO: rename the modded exe to x4.exe for steam.