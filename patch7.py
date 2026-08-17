import re

with open('poses_locas.py', 'r') as f:
    content = f.read()

# 1. Add static checks for Y and O
new_checks = """def check_left_bicep(lm): return abs(lm[L_WRIST].x - lm[L_SHOULDER].x) < 0.10 and abs(lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.15 and lm[L_ELBOW].x < lm[L_SHOULDER].x - 0.05
def check_right_bicep(lm): return abs(lm[R_WRIST].x - lm[R_SHOULDER].x) < 0.10 and abs(lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.15 and lm[R_ELBOW].x > lm[R_SHOULDER].x + 0.05
def check_right_salute(lm): return abs(lm[R_WRIST].x - lm[R_EAR].x) < 0.10 and abs(lm[R_WRIST].y - lm[R_EAR].y) < 0.10

def check_left_arm_y(lm): return lm[L_WRIST].y < lm[NOSE].y and lm[L_WRIST].x < lm[L_SHOULDER].x - 0.15
def check_right_arm_y(lm): return lm[R_WRIST].y < lm[NOSE].y and lm[R_WRIST].x > lm[R_SHOULDER].x + 0.15
def check_left_arm_o(lm): return lm[L_WRIST].y < lm[NOSE].y - 0.05 and abs(lm[L_WRIST].x - lm[NOSE].x) < 0.1
def check_right_arm_o(lm): return lm[R_WRIST].y < lm[NOSE].y - 0.05 and abs(lm[R_WRIST].x - lm[NOSE].x) < 0.1
"""
content = content.replace("""def check_left_bicep(lm): return abs(lm[L_WRIST].x - lm[L_SHOULDER].x) < 0.10 and abs(lm[L_WRIST].y - lm[L_SHOULDER].y) < 0.15 and lm[L_ELBOW].x < lm[L_SHOULDER].x - 0.05
def check_right_bicep(lm): return abs(lm[R_WRIST].x - lm[R_SHOULDER].x) < 0.10 and abs(lm[R_WRIST].y - lm[R_SHOULDER].y) < 0.15 and lm[R_ELBOW].x > lm[R_SHOULDER].x + 0.05
def check_right_salute(lm): return abs(lm[R_WRIST].x - lm[R_EAR].x) < 0.10 and abs(lm[R_WRIST].y - lm[R_EAR].y) < 0.10""", new_checks)

# 2. Add poses to POSES
old_poses = """        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.32, 0.45), R_ELBOW: (0.75, 0.30), L_WRIST: (0.35, 0.58), R_WRIST: (0.58, 0.12), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
]"""
new_poses = """        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.32, 0.45), R_ELBOW: (0.75, 0.30), L_WRIST: (0.35, 0.58), R_WRIST: (0.58, 0.12), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'Letra Y!', 'color': (255, 100, 255),
        'checks': {'left_arm': check_left_arm_y, 'right_arm': check_right_arm_y},
        'icon': load_icon('pose_letra_y'),
        'ref': { NOSE: (0.5, 0.12), L_SHOULDER: (0.38, 0.30), R_SHOULDER: (0.62, 0.30), L_ELBOW: (0.28, 0.18), R_ELBOW: (0.72, 0.18), L_WRIST: (0.15, 0.05), R_WRIST: (0.85, 0.05), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
    {
        'name': 'Letra O!', 'color': (100, 255, 255),
        'checks': {'left_arm': check_left_arm_o, 'right_arm': check_right_arm_o},
        'icon': load_icon('pose_letra_o'),
        'ref': { NOSE: (0.5, 0.25), L_SHOULDER: (0.38, 0.40), R_SHOULDER: (0.62, 0.40), L_ELBOW: (0.32, 0.15), R_ELBOW: (0.68, 0.15), L_WRIST: (0.45, 0.05), R_WRIST: (0.55, 0.05), L_HIP: (0.42, 0.65), R_HIP: (0.58, 0.65) },
    },
]"""
content = content.replace(old_poses, new_poses)

with open('poses_locas.py', 'w') as f:
    f.write(content)
print("Patch 7 applied")
