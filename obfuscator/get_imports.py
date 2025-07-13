import argparse
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
from elftools.elf.sections import SymbolTableSection
from elftools.elf.dynamic import DynamicSection

def parse_elf_imports(file_path):
    """
    Parses an ELF file to extract imported libraries and functions that are resolved
    via the Procedure Linkage Table (PLT).

    This specifically inspects the relocations pointed to by the DT_JMPREL dynamic
    tag, which correspond to function calls made through the PLT.

    Args:
        file_path (str): The path to the ELF file.

    Returns:
        dict: A dictionary with two keys:
              'libraries': A list of strings, where each string is a needed library.
              'functions': A list of strings for imported functions resolved via JMPREL.
              Returns None if the file cannot be parsed or required sections are missing.
    """
    imported_libraries = []
    jmprel_functions = []

    try:
        with open(file_path, 'rb') as f:
            elf_file = ELFFile(f)

            # --- Step 1: Find needed libraries and the JMPREL address ---
            dynamic_section = elf_file.get_section_by_name('.dynamic')
            if not isinstance(dynamic_section, DynamicSection):
                return None  # Not a dynamically linked executable

            jmprel_addr = None
            for tag in dynamic_section.iter_tags():
                if tag.entry.d_tag == 'DT_NEEDED':
                    imported_libraries.append(tag.needed)
                elif tag.entry.d_tag == 'DT_JMPREL':
                    jmprel_addr = tag.entry.d_val
            
            if jmprel_addr is None:
                # No JMPREL table, so no PLT functions to report.
                return {
                    'libraries': sorted(list(set(imported_libraries))),
                    'functions': []
                }

            # --- Step 2: Find the JMPREL relocation section ---
            jmprel_section = None
            for section in elf_file.iter_sections():
                if isinstance(section, RelocationSection) and section.header.sh_addr == jmprel_addr:
                    jmprel_section = section
                    break
            
            if jmprel_section is None:
                print(f"Error: Could not find JMPREL relocation section at address {hex(jmprel_addr)}")
                return None

            # --- Step 3: Get symbols from the relocations in that section ---
            dynsym_section = elf_file.get_section_by_name('.dynsym')
            if not isinstance(dynsym_section, SymbolTableSection):
                print("Error: '.dynsym' section not found, cannot resolve symbol names.")
                return None
            
            for reloc in jmprel_section.iter_relocations():
                symbol_index = reloc['r_info_sym']
                # Symbol index 0 is reserved (STN_UNDEF)
                if symbol_index != 0:
                    symbol = dynsym_section.get_symbol(symbol_index)
                    # Double-check it's an actual function before adding
                    if symbol['st_info']['type'] == 'STT_FUNC' and symbol.name:
                        jmprel_functions.append(symbol.name)

    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    return {
        'libraries': sorted(list(set(imported_libraries))),
        'functions': sorted(list(set(jmprel_functions)))
    }

if __name__ == '__main__':
    # --- Setup argument parser ---
    parser = argparse.ArgumentParser(
        description='Parse an ELF file to show its imported libraries and functions.'
    )
    parser.add_argument(
        'binary',
        metavar='ELF_FILE',
        type=str,
        help='The path to the ELF binary to inspect'
    )
    args = parser.parse_args()
    
    # Use the file path from the command-line arguments
    elf_file_path = args.binary
    imports = parse_elf_imports(elf_file_path)

    if imports:
        print(f"Parsing ELF file: {elf_file_path}")
        
        print("\nImported Libraries (DT_NEEDED):")
        if imports['libraries']:
            for lib in imports['libraries']:
                print(f"- {lib}")
        else:
            print("No imported libraries found.")

        print("\nImported Functions:")
        if imports['functions']:
            print(imports['functions'])
        else:
            print("No imported functions found.")
    else:
        # The function `parse_elf_imports` now handles the FileNotFoundError case,
        # but we add a general failure message here.
        print(f"\nCould not parse imports from '{elf_file_path}'. It might not be a "
              "dynamically linked executable or lacks dynamic symbols.")
