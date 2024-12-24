wifi_channels = [
    # 2.4 GHz channels (1 to 13)
    {'channel': 'wifi_ism_channel1', 'range': (2.402e9, 2.422e9), 'centre_frequency': 2.412e9, 'dfs': False},
    {'channel': 'wifi_ism_channel2', 'range': (2.422e9, 2.442e9), 'centre_frequency': 2.432e9, 'dfs': False},
    {'channel': 'wifi_ism_channel3', 'range': (2.442e9, 2.462e9), 'centre_frequency': 2.452e9, 'dfs': False},
    {'channel': 'wifi_ism_channel4', 'range': (2.462e9, 2.482e9), 'centre_frequency': 2.472e9, 'dfs': False},
    {'channel': 'wifi_ism_channel5', 'range': (2.482e9, 2.502e9), 'centre_frequency': 2.492e9, 'dfs': False},
    {'channel': 'wifi_ism_channel6', 'range': (2.502e9, 2.522e9), 'centre_frequency': 2.512e9, 'dfs': False},
    {'channel': 'wifi_ism_channel7', 'range': (2.522e9, 2.542e9), 'centre_frequency': 2.532e9, 'dfs': False},
    {'channel': 'wifi_ism_channel8', 'range': (2.542e9, 2.562e9), 'centre_frequency': 2.552e9, 'dfs': False},
    {'channel': 'wifi_ism_channel9', 'range': (2.562e9, 2.582e9), 'centre_frequency': 2.572e9, 'dfs': False},
    {'channel': 'wifi_ism_channel10', 'range': (2.582e9, 2.602e9), 'centre_frequency': 2.592e9, 'dfs': False},
    {'channel': 'wifi_ism_channel11', 'range': (2.602e9, 2.622e9), 'centre_frequency': 2.612e9, 'dfs': False},
    {'channel': 'wifi_ism_channel12', 'range': (2.622e9, 2.642e9), 'centre_frequency': 2.632e9, 'dfs': False},
    {'channel': 'wifi_ism_channel13', 'range': (2.642e9, 2.662e9), 'centre_frequency': 2.652e9, 'dfs': False}, 
    
    # 5 GHz channels (UNI1, UNI2, UNI2e, UNI3, etc.)
    # UNI1: Channels 36-48
    {'channel': 'wifi_uni1_channel36', 'range': (5.180e9, 5.200e9), 'centre_frequency': 5.190e9, 'dfs': False},
    {'channel': 'wifi_uni1_channel40', 'range': (5.200e9, 5.220e9), 'centre_frequency': 5.210e9, 'dfs': False},
    {'channel': 'wifi_uni1_channel44', 'range': (5.220e9, 5.240e9), 'centre_frequency': 5.230e9, 'dfs': False},
    {'channel': 'wifi_uni1_channel48', 'range': (5.240e9, 5.260e9), 'centre_frequency': 5.250e9, 'dfs': False},
    
    # UNI2: Channels 52-64
    {'channel': 'wifi_uni2_channel52', 'range': (5.260e9, 5.280e9), 'centre_frequency': 5.270e9, 'dfs': False},
    {'channel': 'wifi_uni2_channel56', 'range': (5.280e9, 5.300e9), 'centre_frequency': 5.290e9, 'dfs': False},
    {'channel': 'wifi_uni2_channel60', 'range': (5.300e9, 5.320e9), 'centre_frequency': 5.310e9, 'dfs': False},
    {'channel': 'wifi_uni2_channel64', 'range': (5.320e9, 5.340e9), 'centre_frequency': 5.330e9, 'dfs': False},
    
    # UNI2e: Channels 100-144 (for DFS)
    {'channel': 'wifi_uni2e_channel100', 'range': (5.500e9, 5.520e9), 'centre_frequency': 5.510e9, 'dfs': True},
    {'channel': 'wifi_uni2e_channel104', 'range': (5.520e9, 5.540e9), 'centre_frequency': 5.530e9, 'dfs': True},
    {'channel': 'wifi_uni2e_channel108', 'range': (5.540e9, 5.560e9), 'centre_frequency': 5.550e9, 'dfs': True},
    {'channel': 'wifi_uni2e_channel112', 'range': (5.560e9, 5.580e9), 'centre_frequency': 5.570e9, 'dfs': True},
    {'channel': 'wifi_uni2e_channel116', 'range': (5.580e9, 5.600e9), 'centre_frequency': 5.590e9, 'dfs': True},
    {'channel': 'wifi_uni2e_channel120', 'range': (5.600e9, 5.620e9), 'centre_frequency': 5.610e9, 'dfs': True},
    {'channel': 'wifi_uni2e_channel124', 'range': (5.620e9, 5.640e9), 'centre_frequency': 5.630e9, 'dfs': True},
    {'channel': 'wifi_uni2e_channel128', 'range': (5.640e9, 5.660e9), 'centre_frequency': 5.650e9, 'dfs': True},
    {'channel': 'wifi_uni2e_channel132', 'range': (5.660e9, 5.680e9), 'centre_frequency': 5.670e9, 'dfs': True},
    {'channel': 'wifi_uni2e_channel136', 'range': (5.680e9, 5.700e9), 'centre_frequency': 5.690e9, 'dfs': True},
    {'channel': 'wifi_uni2e_channel140', 'range': (5.700e9, 5.720e9), 'centre_frequency': 5.710e9, 'dfs': True},
    {'channel': 'wifi_uni2e_channel144', 'range': (5.720e9, 5.740e9), 'centre_frequency': 5.730e9, 'dfs': True},
    
    # UNI3: Channels 149-165
    {'channel': 'wifi_uni3_channel149', 'range': (5.745e9, 5.765e9), 'centre_frequency': 5.755e9, 'dfs': True},
    {'channel': 'wifi_uni3_channel153', 'range': (5.765e9, 5.785e9), 'centre_frequency': 5.775e9, 'dfs': True},
    {'channel': 'wifi_uni3_channel157', 'range': (5.785e9, 5.805e9), 'centre_frequency': 5.795e9, 'dfs': True},
    {'channel': 'wifi_uni3_channel161', 'range': (5.805e9, 5.825e9), 'centre_frequency': 5.815e9, 'dfs': True},
    {'channel': 'wifi_uni3_channel165', 'range': (5.825e9, 5.845e9), 'centre_frequency': 5.835e9, 'dfs': True},
    
    # 6 GHz channels (Wi-Fi 6E) - UNI6
    # Channels 1 to 233 
    {'channel': 'wifi_uni6_channel1', 'range': (5.925e9, 5.945e9), 'centre_frequency': 5.935e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel2', 'range': (5.945e9, 5.965e9), 'centre_frequency': 5.955e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel3', 'range': (5.965e9, 5.985e9), 'centre_frequency': 5.975e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel4', 'range': (5.985e9, 6.005e9), 'centre_frequency': 5.995e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel5', 'range': (6.005e9, 6.025e9), 'centre_frequency': 6.015e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel6', 'range': (6.025e9, 6.045e9), 'centre_frequency': 6.035e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel7', 'range': (6.045e9, 6.065e9), 'centre_frequency': 6.055e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel8', 'range': (6.065e9, 6.085e9), 'centre_frequency': 6.075e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel9', 'range': (6.085e9, 6.105e9), 'centre_frequency': 6.095e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel10', 'range': (6.105e9, 6.125e9), 'centre_frequency': 6.115e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel11', 'range': (6.125e9, 6.145e9), 'centre_frequency': 6.135e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel12', 'range': (6.145e9, 6.165e9), 'centre_frequency': 6.155e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel13', 'range': (6.165e9, 6.185e9), 'centre_frequency': 6.175e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel14', 'range': (6.185e9, 6.205e9), 'centre_frequency': 6.195e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel15', 'range': (6.205e9, 6.225e9), 'centre_frequency': 6.215e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel16', 'range': (6.225e9, 6.245e9), 'centre_frequency': 6.235e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel17', 'range': (6.245e9, 6.265e9), 'centre_frequency': 6.255e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel18', 'range': (6.265e9, 6.285e9), 'centre_frequency': 6.275e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel19', 'range': (6.285e9, 6.305e9), 'centre_frequency': 6.295e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel20', 'range': (6.305e9, 6.325e9), 'centre_frequency': 6.315e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel21', 'range': (6.325e9, 6.345e9), 'centre_frequency': 6.335e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel22', 'range': (6.345e9, 6.365e9), 'centre_frequency': 6.355e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel23', 'range': (6.365e9, 6.385e9), 'centre_frequency': 6.375e9, 'dfs': False},
    {'channel': 'wifi_uni6_channel24', 'range': (6.385e9, 6.405e9), 'centre_frequency': 6.395e9, 'dfs': False},
    # Continue for all channels up to 233...
]

# Example: Print all channels in the 5GHz and 6GHz band
#for channel in wifi_channels:
#    if 'wifi_uni' in channel['channel']:
#        print(f"Channel: {channel['channel']}, Range: {channel['range']}")


# Example: Print all DFS channels
for channel in wifi_channels:
    if channel['dfs'] == True:  # Check if the 'dfs' value is True
        print(f"Channel: {channel['channel']}, Range: {channel['range']}")

