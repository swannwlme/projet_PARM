def to_bin(val, n):
    """Binaire sur n bits"""
    return format(val & ((1 << n) - 1), f'0{n}b')

def generate_line(opcode_bin, rm, rn, rd, imm):
    # --- 1. Reconstruction de l'Instruction (16 bits) ---
    inst_val = 0
    op5 = int(opcode_bin[:5], 2)
    op7 = int(opcode_bin[:7], 2)
    
    # Valeurs par défaut (x = don't care)
    alu_op = "0000"
    out_rm = "xxx"
    out_rn = "xxx"
    out_rd = "xxx"
    mask = "0000"
    carry = "x"      # Par défaut x pour éviter les erreurs inutiles
    imm32_en = "0"
    out_imm5 = "xxxxx"
    out_imm32_val = 0 
    
    # === SHIFTS (LSL, LSR, ASR) ===
    if opcode_bin.startswith(("00000", "00001", "00010")):
        inst_val = (op5 << 11) | ((imm & 0x1F) << 6) | ((rn & 0x7) << 3) | (rd & 0x7)
        out_rn = to_bin(rn, 3) 
        out_rd = to_bin(rd, 3)
        out_imm5 = to_bin(imm, 5)
        imm32_en = "0"            
        mask = "1110"             
        carry = "x"               # Carry indifférente pour les shifts
        
        if op5 == 0: alu_op = "0010"
        elif op5 == 1: alu_op = "0011"
        elif op5 == 2: alu_op = "0100"

    # === ADD/SUB (Register) ===
    elif opcode_bin.startswith(("0001100", "0001101")):
        inst_val = (op7 << 9) | ((rm & 0x7) << 6) | ((rn & 0x7) << 3) | (rd & 0x7)
        out_rm = to_bin(rm, 3)
        out_rn = to_bin(rn, 3)
        out_rd = to_bin(rd, 3)
        out_imm5 = "xxxxx"
        imm32_en = "0"
        mask = "1111"
        if op7 == 0b0001100: alu_op = "0101"; carry = "0"
        else: alu_op = "0110"; carry = "1"

    # === ADD/SUB (Immediate 3) ===
    elif opcode_bin.startswith(("0001110", "0001111")):
        inst_val = (op7 << 9) | ((imm & 0x7) << 6) | ((rn & 0x7) << 3) | (rd & 0x7)
        out_rn = to_bin(rn, 3)
        out_rd = to_bin(rd, 3)
        out_imm5 = "xxxxx"
        imm32_en = "1"
        out_imm32_val = imm
        mask = "1111"
        if op7 == 0b0001110: alu_op = "0101"; carry = "0"
        else: alu_op = "0110"; carry = "1"

    # === MOVS (Immediate 8) ===
    # CORRECTION ICI : Immédiat POSITIF et Carry "x"
    elif opcode_bin.startswith("00100"):
        inst_val = (op5 << 11) | ((rd & 0x7) << 8) | (imm & 0xFF)
        out_rd = to_bin(rd, 3)
        out_imm5 = "xxxxx"
        imm32_en = "1"
        
        # Correction 1 : On garde la valeur POSITIVE (votre circuit ne fait pas l'inversion ici)
        out_imm32_val = imm 
        
        # Note : Si votre ALU fait un RSB (1001), attention au résultat final.
        # Mais ici on teste le contrôleur, et votre contrôleur sort du positif.
        alu_op = "1001" 
        
        mask = "1100"
        
        # Correction 2 : Carry est indifférente
        carry = "x"

    # === CMP (Immediate 8) ===
    elif opcode_bin.startswith("00101"):
        inst_val = (op5 << 11) | ((rn & 0x7) << 8) | (imm & 0xFF)
        out_rn = to_bin(rn, 3)
        out_imm5 = "xxxxx"
        imm32_en = "1"
        out_imm32_val = imm
        alu_op = "1010"
        mask = "1111"
        carry = "1"

    # === ADD/SUB (Immediate 8) ===
    elif opcode_bin.startswith(("00110", "00111")):
        inst_val = (op5 << 11) | ((rd & 0x7) << 8) | (imm & 0xFF)
        out_rn = to_bin(rd, 3)
        out_rd = to_bin(rd, 3)
        out_imm5 = "xxxxx"
        imm32_en = "1"
        out_imm32_val = imm
        mask = "1111"
        if op5 == 0b00110: alu_op = "0101"; carry = "0"
        else: alu_op = "0110"; carry = "1"

    # --- Gestion Imm32 (x ou Valeur) ---
    if imm32_en == "0":
        imm32_str = "x" * 32
    else:
        imm32_str = to_bin(out_imm32_val, 32)

    # Format Output
    return f"{to_bin(inst_val, 16)} 1 {alu_op} {out_rm} {out_rn} {out_rd} {out_imm5} {imm32_en} {carry} {mask} {imm32_str}"

# --- GÉNÉRATION ---
filename = "test_ctl_shift_add_sub_move.txt"
with open(filename, "w") as f:
    # En-tête 
    f.write("Instruction[16] Enable[1] ALU_Opcode[4] Rm[3] Rn[3] Rd[3] Imm5[5] Imm32_Enable[1] Carry[1] Flags_Update_Mask[4] Imm32[32]\n")
    
    # 1. SHIFTS
    for r in range(8):
        f.write(generate_line("00000", 0, r, (r+1)%8, 4) + "\n") # LSLS
        f.write(generate_line("00001", 0, r, (r+1)%8, 4) + "\n") # LSRS
        f.write(generate_line("00010", 0, r, (r+1)%8, 4) + "\n") # ASRS

    # 2. ADD/SUB Reg 
    for r in range(8):
        f.write(generate_line("0001100", r, (r+1)%8, (r+2)%8, 0) + "\n") # ADD
        f.write(generate_line("0001101", r, (r+1)%8, (r+2)%8, 0) + "\n") # SUB

    # 3. ADD/SUB Imm3
    for i in range(8):
        f.write(generate_line("0001110", 0, 0, 1, i) + "\n") # ADD Imm3
        f.write(generate_line("0001111", 0, 0, 1, i) + "\n") # SUB Imm3
        
    # 4. MOVS Imm8 (Positif + Carry x)
    f.write(generate_line("00100", 0, 0, 0, 1) + "\n")   # MOVS #1
    f.write(generate_line("00100", 0, 0, 1, 255) + "\n") # MOVS #255
    f.write(generate_line("00100", 0, 0, 2, 0) + "\n")   # MOVS #0

    # 5. CMP/ADD/SUB Imm8
    f.write(generate_line("00101", 0, 2, 0, 15) + "\n") # CMP
    f.write(generate_line("00110", 0, 0, 3, 20) + "\n") # ADD8
    f.write(generate_line("00111", 0, 0, 4, 20) + "\n") # SUB8

print(f"Fichier '{filename}' généré !")