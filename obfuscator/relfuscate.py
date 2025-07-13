#!/usr/bin/env python3
import struct
import random
import argparse
import os
from pathlib import Path
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.elf.relocation import RelocationSection
from elftools.elf.dynamic import DynamicSection

def get_symbol_name(elffile, symbol_index):
    """Get symbol name from symbol index."""
    # Look for the dynamic symbol table first, as it's most relevant for relocations
    dynsym = elffile.get_section_by_name('.dynsym')
    if dynsym and symbol_index < dynsym.num_symbols():
        return dynsym.get_symbol(symbol_index).name
    
    # Fallback to other symbol tables if not found in .dynsym
    for section in elffile.iter_sections():
        if isinstance(section, SymbolTableSection):
            if symbol_index < section.num_symbols():
                return section.get_symbol(symbol_index).name
    return f"<unknown_{symbol_index}>"

def mess_jmprel(input_filepath, output_filepath, used_functions):
    """
    Reads an ELF file, shuffles its JMPREL relocations, and writes the result to a new file.
    """
    gots = []
    jmprel_addr = None

    try:
        with open(input_filepath, 'rb') as f:
            elffile = ELFFile(f)

            print(f"ELF File: {input_filepath}")
            print(f"Architecture: {'64-bit' if elffile.elfclass == 64 else '32-bit'}")
            print("-" * 60)

            # Find the .rela.plt (or .rel.plt) section via the dynamic segment
            dynamic_section = elffile.get_section_by_name('.dynamic')
            if not dynamic_section:
                print("Error: No dynamic section found. Cannot process relocations.")
                return

            # Get the address of the JMPREL table from the dynamic tags
            for tag in dynamic_section.iter_tags():
                if tag.entry.d_tag == 'DT_JMPREL':
                    jmprel_addr = tag.entry.d_val
                    break
            
            if jmprel_addr is None:
                print("Error: DT_JMPREL tag not found in the dynamic section.")
                return

            # Find the actual relocation section corresponding to the JMPREL address
            jmprel_section = None
            for section in elffile.iter_sections():
                if isinstance(section, RelocationSection) and section.header.sh_addr == jmprel_addr:
                    jmprel_section = section
                    break
            
            if jmprel_section is None:
                print(f"Error: Could not find a relocation section at address {hex(jmprel_addr)}.")
                return

            # Populate the list of GOT entries with their symbol names and original offsets
            for relocation in jmprel_section.iter_relocations():
                symbol_name = get_symbol_name(elffile, relocation['r_info_sym'])
                gots.append((symbol_name, relocation['r_offset']))
            
            reloc_entry_size = jmprel_section.entry_size
            num_relocs = jmprel_section.num_relocations()

    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_filepath}'")
        return
    except Exception as e:
        print(f"An error occurred while reading the ELF file: {e}")
        return


    # original_gots -> gots
    original_gots = gots[:]
    random.shuffle(gots)

    used_functions = [i for i in gots if i[0] in used_functions]
    unused_functions = [i for i in gots if i[0] not in used_functions]

    random.shuffle(unused_functions)
    for used in used_functions:
        unused = unused_functions.pop(0)
        original_gots.remove(used)
        gots.remove(unused)

        gots = [unused] + gots
        original_gots = [used] + original_gots

    for i in range(len(gots)):
        print(f"  {original_gots[i][0]:<20} -> {gots[i][0]}")


    # --- Shuffling Logic ---
    # hacky shuffling because im lazy...
    # original_gots = gots[:]
    # while True:
    #     works = True
    #     for i in range(len(gots)):
    #         original_symbol = original_gots[i][0]
    #         new_symbol = gots[i][0]
    #         # Rule: a "used" function cannot be overwritten by another "used" function
    #         if original_symbol in used_functions and new_symbol in used_functions:
    #             print(f"Shuffle conflict: '{original_symbol}' would be overwritten by '{new_symbol}'. Retrying...")
    #             works = False
    #             break
    #     if works:
    #         print("\nFound a valid shuffle.")
    #         for i in range(len(gots)):
    #             print(f"  {original_gots[i][0]:<20} -> {gots[i][0]}")
    #         break
    
    # --- File Modification ---
    print("\nApplying modifications...")
    with open(input_filepath, "rb") as f:
        contents = bytearray(f.read())

    # Overwrite the r_offset field in each relocation entry
    for i in range(num_relocs):
        # Calculate the position of the r_offset field within the .rela.plt section
        offset_in_file = jmprel_addr + (i * reloc_entry_size)
        
        # In a 64-bit RELA entry, r_offset is the first 8 bytes.
        # This assumes the file is RELA, which is common but not guaranteed.
        # struct Elf64_Rela { Elf64_Addr r_offset; ... }
        contents[offset_in_file : offset_in_file+8] = struct.pack("<Q", gots[i][1])

    # Write to the new output file
    with open(output_filepath, "wb") as f:
        f.write(bytes(contents))
    
    # Copy file permissions from input to output (e.g., to keep it executable)
    st = os.stat(input_filepath)
    os.chmod(output_filepath, st.st_mode)
    print(f"\nSuccessfully created modified file: '{output_filepath}'")


if __name__ == '__main__':
    # --- Setup Argument Parser ---
    parser = argparse.ArgumentParser(
        description='Shuffle JMPREL relocations in an ELF file to obfuscate GOT entries.'
    )
    parser.add_argument(
        'input_file',
        metavar='INPUT_FILE',
        type=str,
        help='The path to the input ELF binary'
    )
    parser.add_argument(
        'output_file',
        metavar='OUTPUT_FILE',
        type=str,
        help='The path to write the modified ELF binary to'
    )
    args = parser.parse_args()
    
    try:
        user_input = input("Paste the list of library functions the binary uses: ")
        used_functions = eval(user_input)
        if not isinstance(used_functions, list):
            raise TypeError("Input must be a list.")
    except Exception as e:
        print(f"Invalid input. Please provide a valid Python list of strings. Error: {e}")
        sys.exit(1)

    print("\nFunctions considered 'used':", used_functions)
    
    # --- Run the main logic ---
    mess_jmprel(args.input_file, args.output_file, used_functions)
