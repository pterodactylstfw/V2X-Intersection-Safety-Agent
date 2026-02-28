# map_config.py
# Rezoluție: 1500x800
# Logica: I4 se varsă direct în fluxul diagonal (Merge Points)

nodes = {
    # --- MARGINI ---
    "W_START": (0, 670),
    "W_END": (0, 630),
    "E_START": (1500, 630),
    "E_END": (1500, 670),
    "S1_START": (420, 800),
    "S1_END": (380, 800),
    "S2_START": (1120, 800),
    "S2_END": (1080, 800),
    "NW_START": (0, 100),
    "NW_END": (0, 50),
    "NE_ONEWAY_START": (1000, 0),
    # --- INTERSECȚIA 1 (Jos-Stânga) ---
    "I1_W_STOP": (340, 670),
    "I1_W_EXIT": (340, 630),
    "I1_S_STOP": (420, 710),
    "I1_S_EXIT": (380, 710),
    "I1_E_STOP": (460, 630),
    "I1_E_EXIT": (460, 670),
    "I1_N_STOP": (380, 590),
    "I1_N_EXIT": (420, 590),
    # --- INTERSECȚIA 2 (Jos-Dreapta) ---
    "I2_W_STOP": (1040, 670),
    "I2_W_EXIT": (1040, 630),
    "I2_S_STOP": (1120, 710),
    "I2_S_EXIT": (1080, 710),
    "I2_E_STOP": (1160, 630),
    "I2_E_EXIT": (1160, 670),
    # Capetele diagonalei la I2
    "I2_DIAG_STOP": (1060, 580),  # Unde ajunge coborârea
    "I2_DIAG_EXIT": (1080, 560),  # De unde pleacă urcarea
    # --- INTERSECȚIA 3 (Sus-Stânga) ---
    "I3_NW_STOP": (350, 280),
    "I3_NW_EXIT": (400, 240),
    "I3_S_STOP": (420, 360),
    "I3_S_EXIT": (380, 360),
    # Capetele diagonalei la I3
    "I3_DIAG_EXIT": (460, 320),  # De unde pleacă coborârea
    "I3_DIAG_STOP": (500, 300),  # Unde ajunge urcarea
    # --- INTERSECȚIA 4 (PUNCT DE FUZIUNE PE DIAGONALĂ) ---
    # Acesta este nodul de intrare dinspre NE
    "I4_IN_STOP": (820, 390),
    # PUNCTELE DE MERGE (Exact pe liniile dintre I2 și I3)
    # Aici traficul din I4 intră pe banda care merge spre I3 (Urcare)
    "MERGE_POINT_UP": (800, 435),
    # Aici traficul din I4 intră pe banda care merge spre I2 (Coborâre)
    "MERGE_POINT_DOWN": (780, 465),
}

edges = [
    # 1. Magistrala Orizontală Jos
    ("W_START", "I1_W_STOP", 1),
    ("I1_W_EXIT", "W_END", 1),
    ("I1_E_EXIT", "I2_W_STOP", 1),
    ("I2_W_EXIT", "I1_E_STOP", 1),
    ("I2_E_EXIT", "E_END", 1),
    ("E_START", "I2_E_STOP", 1),
    # 2. Verticala Stânga
    ("S1_START", "I1_S_STOP", 1),
    ("I1_S_EXIT", "S1_END", 1),
    ("I1_N_EXIT", "I3_S_STOP", 1),
    ("I3_S_EXIT", "I1_N_STOP", 1),
    # 3. Verticala Dreapta
    ("S2_START", "I2_S_STOP", 1),
    ("I2_S_EXIT", "S2_END", 1),
    # 4. Diagonala Nord-Vest
    ("NW_START", "I3_NW_STOP", 1),
    ("I3_NW_EXIT", "NW_END", 1),
    # 5. DIAGONALA URCARE (I2 -> I4 Merge -> I3)
    # Drumul se rupe în două segmente la I4
    ("I2_DIAG_EXIT", "MERGE_POINT_UP", 1),  # Segment 1: I2 până la I4
    ("MERGE_POINT_UP", "I3_DIAG_STOP", 1),  # Segment 2: I4 până la I3
    # 6. DIAGONALA COBORÂRE (I3 -> I4 Merge -> I2)
    # Drumul se rupe în două segmente la I4
    ("I3_DIAG_EXIT", "MERGE_POINT_DOWN", 1),  # Segment 1: I3 până la I4
    ("MERGE_POINT_DOWN", "I2_DIAG_STOP", 1),  # Segment 2: I4 până la I2
    # 7. SENS UNIC I4 (Intrare NE -> Merge Points)
    ("NE_ONEWAY_START", "I4_IN_STOP", 1),
    # De la I4, poți intra pe oricare din sensuri
    ("I4_IN_STOP", "MERGE_POINT_UP", 1),  # Vrei să mergi spre I3
    ("I4_IN_STOP", "MERGE_POINT_DOWN", 1),  # Vrei să mergi spre I2
    # --- 8. LEGAREA INTERNĂ A INTERSECȚIEI 1 ---
    ("I1_W_STOP", "I1_E_EXIT", 1),
    ("I1_W_STOP", "I1_N_EXIT", 1),
    ("I1_W_STOP", "I1_S_EXIT", 1),
    ("I1_E_STOP", "I1_W_EXIT", 1),
    ("I1_E_STOP", "I1_N_EXIT", 1),
    ("I1_E_STOP", "I1_S_EXIT", 1),
    ("I1_S_STOP", "I1_N_EXIT", 1),
    ("I1_S_STOP", "I1_E_EXIT", 1),
    ("I1_S_STOP", "I1_W_EXIT", 1),
    ("I1_N_STOP", "I1_S_EXIT", 1),
    ("I1_N_STOP", "I1_E_EXIT", 1),
    ("I1_N_STOP", "I1_W_EXIT", 1),
    # --- 9. LEGAREA INTERNĂ A INTERSECȚIEI 2 ---
    ("I2_W_STOP", "I2_E_EXIT", 1),
    ("I2_W_STOP", "I2_S_EXIT", 1),
    ("I2_W_STOP", "I2_DIAG_EXIT", 1),
    ("I2_E_STOP", "I2_W_EXIT", 1),
    ("I2_E_STOP", "I2_S_EXIT", 1),
    ("I2_E_STOP", "I2_DIAG_EXIT", 1),
    ("I2_S_STOP", "I2_W_EXIT", 1),
    ("I2_S_STOP", "I2_E_EXIT", 1),
    ("I2_S_STOP", "I2_DIAG_EXIT", 1),
    ("I2_DIAG_STOP", "I2_W_EXIT", 1),
    ("I2_DIAG_STOP", "I2_E_EXIT", 1),
    ("I2_DIAG_STOP", "I2_S_EXIT", 1),
    # --- 10. LEGAREA INTERNĂ A INTERSECȚIEI 3 ---
    ("I3_NW_STOP", "I3_S_EXIT", 1),
    ("I3_NW_STOP", "I3_DIAG_EXIT", 1),
    ("I3_S_STOP", "I3_NW_EXIT", 1),
    ("I3_S_STOP", "I3_DIAG_EXIT", 1),
    ("I3_DIAG_STOP", "I3_NW_EXIT", 1),
    ("I3_DIAG_STOP", "I3_S_EXIT", 1),
]
