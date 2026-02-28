# map_config.py
# Rezoluție: 1500x800
# Logica: 4 noduri per intersecție (Colțurile: NW, NE, SE, SW) cu viraje perpendiculare.

nodes = {
    # --- MARGINI (Punctele de Spawn / Ieșire nu se schimbă) ---
    "W_START": (0, 675),
    "W_END": (0, 635),
    "E_START": (1500, 635),
    "E_END": (1500, 675),
    "S1_START": (420, 800),
    "S1_END": (380, 800),
    "S2_START": (1120, 800),
    "S2_END": (1080, 800),
    "NW_START": (0, 100),
    "NW_END": (0, 70),
    "NE_ONEWAY_START": (1000, 0),
    # --- INTERSECȚIA 1 (4 noduri centrale) ---
    "I1_NW": (380, 635),
    "I1_NE": (420, 635),
    "I1_SE": (420, 675),
    "I1_SW": (380, 675),
    # --- INTERSECȚIA 2 (4 noduri centrale) ---
    "I2_NW": (1080, 635),
    "I2_NE": (1120, 635),
    "I2_SE": (1120, 675),
    "I2_SW": (1080, 675),
    # --- INTERSECȚIA 3 (4 noduri centrale) ---
    "I3_NW": (380, 290),
    "I3_NE": (420, 280),
    "I3_SE": (420, 310),
    "I3_SW": (380, 320),
    # --- INTERSECȚIA 4 (Merge Points - rămâne la fel de simplu) ---
    "MERGE_UP": (770, 455),  # Mijlocul matematic perfect între I2_NE și I3_NE
    "MERGE_DOWN": (760, 475),
}

edges = [
    # --- 1. INTRARE / IEȘIRE SPRE MARGINI ---
    # Vest
    ("W_START", "I1_SW", 1),
    ("I1_NW", "W_END", 1),
    # Est
    ("E_START", "I2_NE", 1),
    ("I2_SE", "E_END", 1),
    # Sud 1
    ("S1_START", "I1_SE", 1),
    ("I1_SW", "S1_END", 1),
    # Sud 2
    ("S2_START", "I2_SE", 1),
    ("I2_SW", "S2_END", 1),
    # Nord-Vest
    ("NW_START", "I3_NW", 1),
    ("I3_NE", "NW_END", 1),
    # --- 2. DRUMURI DE LEGĂTURĂ ÎNTRE INTERSECȚII ---
    # I1 <-> I2 (Orizontală Jos)
    ("I1_SE", "I2_SW", 1),  # Spre Est
    ("I2_NW", "I1_NE", 1),  # Spre Vest
    # I1 <-> I3 (Verticală Stânga)
    ("I1_NE", "I3_SE", 1),  # Spre Nord
    ("I3_SW", "I1_NW", 1),  # Spre Sud
    # I2 <-> I3 (Diagonala Principală) - Trece prin Merge Points
    ("I3_SE", "MERGE_DOWN", 1),  # Din I3 coboară spre I2
    ("MERGE_DOWN", "I2_NW", 1),
    ("I2_NE", "MERGE_UP", 1),  # Din I2 urcă spre I3
    ("MERGE_UP", "I3_NE", 1),
    # --- 3. SENS UNIC I4 ---
    ("NE_ONEWAY_START", "MERGE_UP", 1),
    ("NE_ONEWAY_START", "MERGE_DOWN", 1),  # Se varsă spre I2
    # --- 4. LEGAREA INTERNĂ A INTERSECȚIILOR (Pătratul Perpendicular) ---
    # Mașinile circulă Counter-Clockwise în interior (regula de prioritate dreapta)
    # I1
    ("I1_NW", "I1_SW", 1),
    ("I1_SW", "I1_SE", 1),
    ("I1_SE", "I1_NE", 1),
    ("I1_NE", "I1_NW", 1),
    # I2
    ("I2_NW", "I2_SW", 1),
    ("I2_SW", "I2_SE", 1),
    ("I2_SE", "I2_NE", 1),
    ("I2_NE", "I2_NW", 1),
    # I3
    ("I3_NW", "I3_SW", 1),
    ("I3_SW", "I3_SE", 1),
    ("I3_SE", "I3_NE", 1),
    ("I3_NE", "I3_NW", 1),
]
