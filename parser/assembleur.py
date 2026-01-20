import sys

#################################################################################
# la définition des constantes (Tableau de synthèse)
REGISTRES = {
    'r0': 0, 'r1': 1, 'r2': 2, 'r3': 3,
    'r4': 4, 'r5': 5, 'r6': 6, 'r7': 7,
    'sp': 13, 'lr': 14, 'pc': 15
}
#################################################################################







#################################################################################
# codes de conditions pr les branchements 
CONDITIONS = {
    'eq': 0b0000, 'ne': 0b0001, 'cs': 0b0010, 'cc': 0b0011,
    'mi': 0b0100, 'pl': 0b0101, 'vs': 0b0110, 'vc': 0b0111,
    'hi': 0b1000, 'ls': 0b1001, 'ge': 0b1010, 'lt': 0b1011,
    'gt': 0b1100, 'le': 0b1101, 'al': 0b1110 # Always
}
#################################################################################

# Ajout pour la gestion des sauts (donc le Double Passage)
LABELS = {} 







###################################################################################
def parse_val(arg, current_line=0):
    arg = arg.strip().lower()
    
    if arg in REGISTRES:
        return REGISTRES[arg]
    elif arg.startswith('#'):
        return int(arg.replace('#', ''), 0)
    elif arg in LABELS:
        # CALCUL DU SAUT (Offset)
        target_line = LABELS[arg]
        offset = target_line - current_line - 3 
        return offset
    else:
        try:
            return int(arg, 0)
        except ValueError:
            return 0
 ###################################################################################    

     
     
     
     
     
     
        
        
#######################################################################################
def assembler_instruction(mnemonic, args, current_line):
    instr_bin = 0

    # -------------------------------------------------------------------------
    # GROUPE SP (Gestion Spéciale)
    # -------------------------------------------------------------------------
    if mnemonic == 'add' and args[0] == 'sp':
        imm = parse_val(args[1])
        imm_scaled = imm // 4 
        instr_bin = (0b101100000 << 7) | imm_scaled

    elif mnemonic == 'sub' and args[0] == 'sp':
        imm = parse_val(args[1])
        imm_scaled = imm // 4 
        instr_bin = (0b101100001 << 7) | imm_scaled

    # -------------------------------------------------------------------------
    # GROUPE 1 : Décalages immédiats (LSLS, LSRS, ASRS)
    # -------------------------------------------------------------------------
    elif mnemonic in ['lsls', 'lsrs', 'asrs'] and len(args) == 3 and args[2].startswith('#'):
        if mnemonic == 'lsls': base = 0b00000
        elif mnemonic == 'lsrs': base = 0b00001
        elif mnemonic == 'asrs': base = 0b00010
        rd = parse_val(args[0])
        rn = parse_val(args[1])
        imm5 = parse_val(args[2])
        instr_bin = (base << 11) | (imm5 << 6) | (rn << 3) | rd

    # -------------------------------------------------------------------------
    # GROUPE 2 : ADD/SUB (Gère 3 args ET 2 args) 
    # -------------------------------------------------------------------------
    elif mnemonic in ['adds', 'subs']:
        rd = parse_val(args[0])
        
        # CAS 1 : 3 Arguments (ex: adds r0, r1, #4)
        if len(args) == 3:
            rn = parse_val(args[1])
            last_arg = args[2]
            if last_arg.startswith('r'): # Version Registre
                op = 0b0001100 if mnemonic == 'adds' else 0b0001101
                rm = parse_val(last_arg)
                instr_bin = (op << 9) | (rm << 6) | (rn << 3) | rd
            else: # Version Immédiat 3 bits
                op = 0b0001110 if mnemonic == 'adds' else 0b0001111
                imm3 = parse_val(last_arg)
                instr_bin = (op << 9) | (imm3 << 6) | (rn << 3) | rd
        
        # CAS 2 : 2 Arguments (ex: subs r0, #48)
        # Voir le Tableau "Add/Sub 8-bit immediate"
        elif len(args) == 2 and args[1].startswith('#'):
            imm8 = parse_val(args[1])
            # ADDS 8-bit: 00110, SUBS 8-bit: 00111
            op = 0b00110 if mnemonic == 'adds' else 0b00111
            # Format: Opcode(5) | Rdn(3) | imm8(8)
            instr_bin = (op << 11) | (rd << 8) | imm8

    # -------------------------------------------------------------------------
    # GROUPE 3: MOVS et CMP
    # -------------------------------------------------------------------------
    elif mnemonic == 'movs':
        rd = parse_val(args[0])
        if args[1].startswith('#'): # MOVS Rd, #imm8
            imm8 = parse_val(args[1])
            instr_bin = (0b00100 << 11) | (rd << 8) | imm8
        else: 
            # MOVS Rd, Rm (Registre à Registre)
            # c'est pas dans le tableau, mais c'est souvent encodé comme ADDS Rd, Rm, #0
            # ou, LSLS Rd, Rm, #0. On utilise LSLS (00000) pour copier.
            rm = parse_val(args[1])
            # LSLS Rd, Rm, #0 -> 00000 | 00000 | Rm | Rd
            instr_bin = (0b00000 << 11) | (0 << 6) | (rm << 3) | rd

    # CMP avec Immédiat (ex: cmp r0, #0)
    elif mnemonic == 'cmp' and args[1].startswith('#'):
        # Voir le Tableau "Compare / CMP <imm8> <Rd>" -> 00101
        rd = parse_val(args[0])
        imm8 = parse_val(args[1])
        instr_bin = (0b00101 << 11) | (rd << 8) | imm8

    # -------------------------------------------------------------------------
    # GROUPE 4 : DATA PROCESSING (ALU 2 Registres)
    # -------------------------------------------------------------------------
    elif mnemonic in ['ands', 'eors', 'lsls', 'lsrs', 'asrs', 'adcs', 'sbcs', 'rors', 
                      'tst', 'rsbs', 'cmp', 'cmn', 'orrs', 'muls', 'bics', 'mvns']:
        alu_codes = {
            'ands': 0b0000, 'eors': 0b0001, 'lsls': 0b0010, 'lsrs': 0b0011,
            'asrs': 0b0100, 'adcs': 0b0101, 'sbcs': 0b0110, 'rors': 0b0111,
            'tst':  0b1000, 'rsbs': 0b1001, 'cmp':  0b1010, 'cmn':  0b1011,
            'orrs': 0b1100, 'muls': 0b1101, 'bics': 0b1110, 'mvns': 0b1111
        }
        op_alu = alu_codes[mnemonic]
        rdn = parse_val(args[0])
        rm = parse_val(args[1])
        instr_bin = (0b010000 << 10) | (op_alu << 6) | (rm << 3) | rdn

    # -------------------------------------------------------------------------
    # GROUPE 5 : LOAD / STORE (CORRIGÉ)
    # -------------------------------------------------------------------------
    elif mnemonic == 'str': 
        rt = parse_val(args[0])
        
        # Est-ce qu'on a un décalage explicite (ex: [sp, #4]) ?
        if args[-1].startswith('#'):
            imm_str = args[-1].replace(']', '') 
            imm = parse_val(imm_str)
        else:
            # Pas de #, donc c'est [sp] tout court -> décalage 0
            imm = 0
            
        # Division par 4 si c'est relatif à SP
        if 'sp' in args[1]: 
            imm = imm // 4 
            
        instr_bin = (0b10010 << 11) | (rt << 8) | imm

    elif mnemonic == 'ldr': 
        rt = parse_val(args[0])
        
        # Est-ce qu'on a un décalage explicite ?
        if args[-1].startswith('#'):
            imm_str = args[-1].replace(']', '')
            imm = parse_val(imm_str)
        else:
            # Pas de # -> décalage 0
            imm = 0
            
        # Division par 4 si c'est relatif à SP
        if 'sp' in args[1]: 
            imm = imm // 4
            
        instr_bin = (0b10011 << 11) | (rt << 8) | imm

    # -------------------------------------------------------------------------
    # GROUPE 6 & 7 : BRANCHEMENTS
    # -------------------------------------------------------------------------
    elif mnemonic.startswith('b') and mnemonic != 'b':
        cond_str = mnemonic[1:] 
        if cond_str in CONDITIONS:
            cond_bits = CONDITIONS[cond_str]
            offset = parse_val(args[0], current_line) 
            instr_bin = (0b1101 << 12) | (cond_bits << 8) | (offset & 0xFF)

    elif mnemonic == 'b':
        offset = parse_val(args[0], current_line)
        instr_bin = (0b11100 << 11) | (offset & 0x7FF)

    return instr_bin








#----------------------------------------------------------------------------------------------
def main(input_file, output_file):
    lines_to_process = []
    
    # --- PASSE 1 : REPÉRAGE DES LABELS ---
    try:
        with open(input_file, 'r') as f_in:
            instruction_count = 0
            for line in f_in:
                clean_line = line.split('@')[0].strip()
                
                # On ignore lignes vides
                if not clean_line:
                    continue

                # LA GESTION DES LABELS (avec ou sans point, ex: "run:" ou ".LBB0_1:")
                if clean_line.endswith(':'):
                    label_name = clean_line[:-1].lower() # stocke en minuscule 
                    LABELS[label_name] = instruction_count
                    continue
                
                # LA GESTION DES DIRECTIVES (tout ce qui commence par . et n'est pas un label)
                if clean_line.startswith('.'):
                    continue
                
                # --- petits FILTRES C ---
                parts = clean_line.replace(',', ' ').split()
                mnemonic = parts[0].lower()
                
                if mnemonic in ['push', 'pop', 'bx', 'blx', 'bl']:
                    continue
                
                if mnemonic == 'add' and 'r7' in parts and 'sp' in parts:
                    continue
                
                # Si on arrive ici, c'est bien une vraie instruction yay
                lines_to_process.append(clean_line)
                instruction_count += 1

        # --- PASSE 2 : GÉNÉRATION DU CODE ---
        with open(output_file, 'w') as f_out:
            f_out.write("v2.0 raw\n")
            
            for idx, line in enumerate(lines_to_process):
                parts = line.replace(',', ' ').replace('[', ' ').replace(']', ' ').split()
                if not parts: continue
                
                mnemonic = parts[0].lower()
                
                # Clang met 'mov' au lieu de 'movs'
                if mnemonic == 'mov': mnemonic = 'movs'
                
                args = parts[1:]
                
                try:
                    code = assembler_instruction(mnemonic, args, idx)
                    f_out.write(f"{code:04x} ")
                except Exception as e:
                    print(f"Erreur instruction {idx} ({line}): {e}")
                    f_out.write("0000 ")
                    
        print(f"Succès ! Fichier généré : {output_file}")
        
    except FileNotFoundError:
        print(f"Erreur : Fichier {input_file} introuvable.")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        main(sys.argv[1], sys.argv[2])
        #python3 assembleur.py code_c/calckeyb.s code_c/mon_test.bin
    else:
        # Valeur par défaut pour les tests
        main("calckeyb.s", "mon_test_calckeyb.bin")